import json
from pathlib import Path

from auditable_evidence_binding.audit import audit_response
from auditable_evidence_binding.canonical import read_json
from auditable_evidence_binding.config import load_config
from auditable_evidence_binding.diagnosis import (
    RuleBasedDemoBackend,
    build_diagnosis_schema,
)
from auditable_evidence_binding.domain import parse_event
from auditable_evidence_binding.evidence import extract_candidate_cards
from auditable_evidence_binding.provenance import bind_evidence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _fixture():
    config = load_config(REPOSITORY_ROOT / "configs" / "demo.toml")
    event = parse_event(read_json(REPOSITORY_ROOT / "examples" / "demo-event.json"))
    cards = extract_candidate_cards(event, config.evidence)
    prepared = bind_evidence(event, cards, config)
    schema = build_diagnosis_schema(config, sorted(prepared.registry["cards"]))
    raw = RuleBasedDemoBackend(config).generate(prepared.model_context, schema)
    return config, prepared, schema, raw


def test_provenance_hash_mismatch_is_rejected() -> None:
    config, prepared, schema, raw = _fixture()
    registry = json.loads(json.dumps(prepared.registry))
    first_alias = sorted(registry["cards"])[0]
    registry["cards"][first_alias]["content_hash"] = "0" * 64

    outcome = audit_response(
        raw,
        schema,
        prepared.model_context,
        registry,
        config,
    )

    assert outcome.status == "rejected"
    assert outcome.audit_record["layers"]["provenance"]["status"] == "failed"


def test_forbidden_high_risk_language_is_rejected() -> None:
    config, prepared, schema, raw = _fixture()
    record = json.loads(raw)
    record["candidate_explanations"][0]["explanation"] += " Bypass interlock now."

    outcome = audit_response(
        json.dumps(record),
        schema,
        prepared.model_context,
        prepared.registry,
        config,
    )

    assert outcome.status == "rejected"
    assert outcome.audit_record["layers"]["safety"]["status"] == "failed"
