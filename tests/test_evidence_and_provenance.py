import copy
from pathlib import Path

import pytest

from auditable_evidence_binding.canonical import read_json
from auditable_evidence_binding.config import load_config
from auditable_evidence_binding.domain import EventValidationError, parse_event
from auditable_evidence_binding.evidence import extract_candidate_cards
from auditable_evidence_binding.provenance import bind_evidence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_candidate_cards_are_ranked_before_random_alias_binding() -> None:
    config = load_config(REPOSITORY_ROOT / "configs" / "demo.toml")
    event = parse_event(read_json(REPOSITORY_ROOT / "examples" / "demo-event.json"))

    cards = extract_candidate_cards(event, config.evidence)
    prepared = bind_evidence(event, cards, config)

    assert cards[0].variable == "pressure"
    assert cards[0].direction == "increase"
    assert len(cards) == 3
    assert set(prepared.registry["cards"]) == {"E01", "E02", "E03"}
    assert {
        card["alias"] for card in prepared.model_context["candidate_observations"]
    } == set(prepared.registry["cards"])
    assert all(
        entry["event_alias"] == prepared.event_alias
        for entry in prepared.registry["cards"].values()
    )


def test_alarm_indices_must_be_integers() -> None:
    payload = copy.deepcopy(
        read_json(REPOSITORY_ROOT / "examples" / "demo-event.json")
    )
    payload["alarm"]["start_index"] = 12.5

    with pytest.raises(EventValidationError, match="must be an integer"):
        parse_event(payload)


def test_signal_names_are_unique_without_case_ambiguity() -> None:
    payload = copy.deepcopy(
        read_json(REPOSITORY_ROOT / "examples" / "demo-event.json")
    )
    payload["signals"][1]["name"] = "Pressure"

    with pytest.raises(EventValidationError, match="duplicate signal name"):
        parse_event(payload)
