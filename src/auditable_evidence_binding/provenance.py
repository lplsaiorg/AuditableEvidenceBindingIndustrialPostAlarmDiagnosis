from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any

from .canonical import sha256_json
from .config import AppConfig
from .domain import EvidenceCard, SensorEvent


@dataclass(frozen=True)
class PreparedEvidence:
    event_alias: str
    model_context: dict[str, Any]
    registry: dict[str, Any]


def _event_alias(event_id: str, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}|event|{event_id}".encode("utf-8")).hexdigest()
    return f"EVT-{digest[:12].upper()}"


def _evidence_aliases(event_id: str, salt: str, count: int) -> list[str]:
    aliases = [f"E{index:02d}" for index in range(1, count + 1)]
    digest = hashlib.sha256(f"{salt}|evidence|{event_id}".encode("utf-8")).digest()
    random.Random(int.from_bytes(digest[:8], "big")).shuffle(aliases)
    return aliases


def bind_evidence(
    event: SensorEvent,
    cards: list[EvidenceCard],
    config: AppConfig,
) -> PreparedEvidence:
    event_alias = _event_alias(event.event_id, config.alias_salt)
    aliases = _evidence_aliases(event.event_id, config.alias_salt, len(cards))
    signal_by_name = {signal.name: signal for signal in event.signals}
    visible_cards: list[dict[str, Any]] = []
    registry_cards: dict[str, dict[str, Any]] = {}

    for alias, card in zip(aliases, cards):
        content = card.model_content()
        visible_cards.append({"alias": alias, **content})
        signal = signal_by_name[card.variable]
        source_hash = sha256_json(
            {
                "dataset": event.dataset_name,
                "dataset_version": event.dataset_version,
                "source_id": event.source_id,
                "variable": signal.name,
                "values": list(signal.values),
                "reference_values": list(signal.reference_values),
            }
        )
        registry_cards[alias] = {
            "event_alias": event_alias,
            "dataset": event.dataset_name,
            "dataset_version": event.dataset_version,
            "source_id": event.source_id,
            "source_hash": source_hash,
            "variable": card.variable,
            "coordinates": {
                "start_index": event.alarm.start_index,
                "end_index": event.alarm.end_index,
                "start_timestamp": event.timestamps[event.alarm.start_index],
                "end_timestamp": event.timestamps[event.alarm.end_index],
            },
            "detector": {
                "name": event.detector.name,
                "version": event.detector.version,
            },
            "extractor_version": config.extractor_version,
            "reference_version": config.reference_version,
            "content_hash": sha256_json(content),
        }

    visible_cards.sort(key=lambda item: item["alias"])
    model_context = {
        "schema_version": config.schema_version,
        "event_id": event_alias,
        "alarm_summary": {
            "score": event.alarm.score,
            "detector": event.detector.name,
            "detector_version": event.detector.version,
            "duration_points": event.alarm.end_index - event.alarm.start_index + 1,
        },
        "candidate_observations": visible_cards,
        "allowed_labels": list(config.allowed_labels),
        "allowed_actions": list(config.allowed_actions),
        "evidence_status": (
            "sufficient_candidates"
            if len(cards) >= config.evidence.minimum_cards
            else "insufficient_candidates"
        ),
    }
    registry = {
        "registry_version": "aeb-provenance-registry/1.0",
        "event_id": event.event_id,
        "event_alias": event_alias,
        "cards": registry_cards,
    }
    return PreparedEvidence(
        event_alias=event_alias,
        model_context=model_context,
        registry=registry,
    )
