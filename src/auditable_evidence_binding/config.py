from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class EvidenceConfig:
    top_k: int
    minimum_cards: int
    local_reference_points: int
    robust_scale_floor: float
    direction_epsilon: float
    score_global_weight: float
    score_local_weight: float
    score_peak_weight: float
    score_trend_weight: float


@dataclass(frozen=True)
class SafetyConfig:
    minimum_supported_confidence: float
    escalation_actions: tuple[str, ...]
    forbidden_terms: tuple[str, ...]


@dataclass(frozen=True)
class AppConfig:
    schema_version: str
    extractor_version: str
    reference_version: str
    alias_salt: str
    allowed_labels: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    label_rules: dict[str, str]
    evidence: EvidenceConfig
    safety: SafetyConfig


def _required(mapping: dict[str, Any], key: str, expected: type) -> Any:
    value = mapping.get(key)
    if not isinstance(value, expected):
        raise ConfigurationError(f"{key} must be {expected.__name__}")
    return value


def _string_tuple(mapping: dict[str, Any], key: str) -> tuple[str, ...]:
    value = _required(mapping, key, list)
    result = tuple(str(item) for item in value)
    if not result or any(not item for item in result):
        raise ConfigurationError(f"{key} must contain non-empty strings")
    if len(set(result)) != len(result):
        raise ConfigurationError(f"{key} must not contain duplicates")
    return result


def load_config(path: Path) -> AppConfig:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    package = _required(payload, "package", dict)
    evidence = _required(payload, "evidence", dict)
    safety = _required(payload, "safety", dict)
    label_rules = {
        str(key).casefold(): str(value)
        for key, value in _required(payload, "label_rules", dict).items()
    }

    allowed_labels = _string_tuple(package, "allowed_labels")
    allowed_actions = _string_tuple(package, "allowed_actions")
    if "INSUFFICIENT_EVIDENCE" not in allowed_labels:
        raise ConfigurationError("allowed_labels must include INSUFFICIENT_EVIDENCE")
    if "ESCALATE_TO_HUMAN" not in allowed_actions:
        raise ConfigurationError("allowed_actions must include ESCALATE_TO_HUMAN")
    if any(label not in allowed_labels for label in label_rules.values()):
        raise ConfigurationError("label_rules values must be present in allowed_labels")

    result = AppConfig(
        schema_version=_required(package, "schema_version", str),
        extractor_version=_required(package, "extractor_version", str),
        reference_version=_required(package, "reference_version", str),
        alias_salt=_required(package, "alias_salt", str),
        allowed_labels=allowed_labels,
        allowed_actions=allowed_actions,
        label_rules=label_rules,
        evidence=EvidenceConfig(
            top_k=int(_required(evidence, "top_k", int)),
            minimum_cards=int(_required(evidence, "minimum_cards", int)),
            local_reference_points=int(_required(evidence, "local_reference_points", int)),
            robust_scale_floor=float(_required(evidence, "robust_scale_floor", float)),
            direction_epsilon=float(_required(evidence, "direction_epsilon", float)),
            score_global_weight=float(_required(evidence, "score_global_weight", float)),
            score_local_weight=float(_required(evidence, "score_local_weight", float)),
            score_peak_weight=float(_required(evidence, "score_peak_weight", float)),
            score_trend_weight=float(_required(evidence, "score_trend_weight", float)),
        ),
        safety=SafetyConfig(
            minimum_supported_confidence=float(
                _required(safety, "minimum_supported_confidence", float)
            ),
            escalation_actions=_string_tuple(safety, "escalation_actions"),
            forbidden_terms=tuple(
                str(item).casefold()
                for item in _required(safety, "forbidden_terms", list)
            ),
        ),
    )
    if not 1 <= result.evidence.top_k <= 8:
        raise ConfigurationError("top_k must be between 1 and 8")
    if not 1 <= result.evidence.minimum_cards <= result.evidence.top_k:
        raise ConfigurationError("minimum_cards must be between 1 and top_k")
    if result.evidence.local_reference_points < 1:
        raise ConfigurationError("local_reference_points must be positive")
    if result.evidence.robust_scale_floor <= 0:
        raise ConfigurationError("robust_scale_floor must be positive")
    if not 0 <= result.safety.minimum_supported_confidence <= 1:
        raise ConfigurationError("minimum_supported_confidence must be in [0, 1]")
    if any(action not in result.allowed_actions for action in result.safety.escalation_actions):
        raise ConfigurationError("escalation_actions must be present in allowed_actions")
    return result
