from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from .canonical import sha256_json
from .config import AppConfig


class DuplicateKeyError(ValueError):
    pass


@dataclass(frozen=True)
class AuditOutcome:
    status: str
    parsed_record: dict[str, Any] | None
    audit_record: dict[str, Any]


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_parse_json(raw_response: str) -> dict[str, Any]:
    value = json.loads(
        raw_response,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON number: {value}")
        ),
    )
    if not isinstance(value, dict):
        raise ValueError("diagnostic response must be one JSON object")
    return value


def _schema_issues(
    record: dict[str, Any],
    schema: dict[str, Any],
) -> list[str]:
    validator = Draft202012Validator(schema)
    return [
        f"{'/'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(record), key=lambda item: list(item.path))
    ]


def _provenance_issues(
    record: dict[str, Any],
    context: dict[str, Any],
    registry: dict[str, Any],
) -> list[str]:
    issues: list[str] = []
    if record.get("event_id") != context.get("event_id"):
        issues.append("record event_id does not match the current event")
    if registry.get("event_alias") != context.get("event_id"):
        issues.append("registry event ownership does not match the current event")

    visible = {
        card["alias"]: {key: value for key, value in card.items() if key != "alias"}
        for card in context.get("candidate_observations", [])
    }
    registered = registry.get("cards", {})
    if set(visible) != set(registered):
        issues.append("visible and registered evidence alias sets differ")
    for alias, content in visible.items():
        entry = registered.get(alias)
        if not isinstance(entry, dict):
            issues.append(f"{alias} is missing from the registry")
            continue
        if entry.get("event_alias") != context.get("event_id"):
            issues.append(f"{alias} belongs to a different event")
        if entry.get("content_hash") != sha256_json(content):
            issues.append(f"{alias} content hash mismatch")

    for candidate in record.get("candidate_explanations", []):
        support = candidate.get("supporting_evidence", [])
        contradiction = candidate.get("contradicting_evidence", [])
        for alias in [*support, *contradiction]:
            if alias not in visible:
                issues.append(f"unknown event-local evidence alias: {alias}")
        overlap = set(support) & set(contradiction)
        if overlap:
            issues.append(
                "evidence cannot be both supporting and contradicting: "
                + ", ".join(sorted(overlap))
            )
    return issues


def _safety_evaluation(
    record: dict[str, Any],
    config: AppConfig,
) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    escalations: list[str] = []
    for index, candidate in enumerate(record.get("candidate_explanations", [])):
        label = candidate["label"]
        support = candidate["supporting_evidence"]
        contradiction = candidate["contradicting_evidence"]
        missing = candidate["missing_information"]
        confidence = float(candidate["confidence"])
        action = candidate["action"]
        searchable = f"{candidate['explanation']} {action}".casefold()

        for term in config.safety.forbidden_terms:
            if term and term in searchable:
                failures.append(f"candidate {index} contains forbidden high-risk term: {term}")
        if label != "INSUFFICIENT_EVIDENCE" and not support:
            failures.append(f"candidate {index} asserts a diagnosis without support")
        if label == "INSUFFICIENT_EVIDENCE":
            if action not in config.safety.escalation_actions:
                failures.append(
                    f"candidate {index} must escalate when evidence is insufficient"
                )
            escalations.append(f"candidate {index} selected insufficient evidence")
        if (contradiction or missing) and action not in config.safety.escalation_actions:
            failures.append(
                f"candidate {index} must escalate when evidence conflicts or is missing"
            )
        if (
            label != "INSUFFICIENT_EVIDENCE"
            and confidence < config.safety.minimum_supported_confidence
        ):
            escalations.append(
                f"candidate {index} confidence is below the acceptance threshold"
            )
    return failures, escalations


def audit_response(
    raw_response: str,
    schema: dict[str, Any],
    context: dict[str, Any],
    registry: dict[str, Any],
    config: AppConfig,
) -> AuditOutcome:
    layers: dict[str, Any] = {}
    try:
        record = strict_parse_json(raw_response)
    except Exception as exc:
        layers["strict_parse"] = {
            "status": "failed",
            "issues": [f"{type(exc).__name__}: {exc}"],
        }
        return AuditOutcome(
            status="rejected",
            parsed_record=None,
            audit_record={"final_status": "rejected", "layers": layers},
        )
    layers["strict_parse"] = {"status": "passed", "issues": []}

    schema_issues = _schema_issues(record, schema)
    layers["schema"] = {
        "status": "passed" if not schema_issues else "failed",
        "issues": schema_issues,
    }
    if schema_issues:
        return AuditOutcome(
            status="rejected",
            parsed_record=record,
            audit_record={"final_status": "rejected", "layers": layers},
        )

    provenance_issues = _provenance_issues(record, context, registry)
    layers["provenance"] = {
        "status": "passed" if not provenance_issues else "failed",
        "issues": provenance_issues,
    }
    if provenance_issues:
        return AuditOutcome(
            status="rejected",
            parsed_record=record,
            audit_record={"final_status": "rejected", "layers": layers},
        )

    safety_failures, escalation_reasons = _safety_evaluation(record, config)
    layers["safety"] = {
        "status": "passed" if not safety_failures else "failed",
        "issues": safety_failures,
        "escalation_reasons": escalation_reasons,
    }
    if safety_failures:
        final_status = "rejected"
    elif escalation_reasons:
        final_status = "escalated"
    else:
        final_status = "accepted"
    return AuditOutcome(
        status=final_status,
        parsed_record=record,
        audit_record={
            "final_status": final_status,
            "event_id": context["event_id"],
            "layers": layers,
        },
    )
