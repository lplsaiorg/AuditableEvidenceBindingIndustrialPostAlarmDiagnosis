from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Protocol

from .canonical import read_json
from .config import AppConfig


class DiagnosisBackend(Protocol):
    name: str
    metadata: dict[str, str]

    def generate(
        self,
        context: dict[str, Any],
        schema: dict[str, Any],
    ) -> str: ...


def build_diagnosis_schema(
    config: AppConfig,
    evidence_aliases: list[str],
) -> dict[str, Any]:
    evidence_array = {
        "type": "array",
        "items": {"type": "string", "enum": evidence_aliases},
        "maxItems": len(evidence_aliases),
        "uniqueItems": True,
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.org/schemas/aeb-diagnosis-1.0.json",
        "type": "object",
        "required": ["schema_version", "event_id", "candidate_explanations"],
        "properties": {
            "schema_version": {"const": config.schema_version},
            "event_id": {"type": "string", "pattern": "^EVT-[0-9A-F]{12}$"},
            "candidate_explanations": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "required": [
                        "label",
                        "explanation",
                        "variables",
                        "supporting_evidence",
                        "contradicting_evidence",
                        "missing_information",
                        "confidence",
                        "action",
                    ],
                    "properties": {
                        "label": {
                            "type": "string",
                            "enum": list(config.allowed_labels),
                        },
                        "explanation": {"type": "string", "minLength": 1},
                        "variables": {
                            "type": "array",
                            "items": {"type": "string", "minLength": 1},
                            "uniqueItems": True,
                        },
                        "supporting_evidence": evidence_array,
                        "contradicting_evidence": evidence_array,
                        "missing_information": {
                            "type": "array",
                            "items": {"type": "string", "minLength": 1},
                            "uniqueItems": True,
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                        },
                        "action": {
                            "type": "string",
                            "enum": list(config.allowed_actions),
                        },
                    },
                    "additionalProperties": False,
                },
            },
        },
        "additionalProperties": False,
    }


class SafeFallbackBackend:
    name = "safe"
    metadata = {"implementation": "deterministic-fallback/1.0"}

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def generate(self, context: dict[str, Any], schema: dict[str, Any]) -> str:
        record = {
            "schema_version": self._config.schema_version,
            "event_id": context["event_id"],
            "candidate_explanations": [
                {
                    "label": "INSUFFICIENT_EVIDENCE",
                    "explanation": (
                        "The deterministic fallback does not assert a fault signature."
                    ),
                    "variables": [],
                    "supporting_evidence": [],
                    "contradicting_evidence": [],
                    "missing_information": [
                        "A configured diagnostic model response is unavailable."
                    ],
                    "confidence": 0.0,
                    "action": "ESCALATE_TO_HUMAN",
                }
            ],
        }
        return json.dumps(record, ensure_ascii=False, allow_nan=False)


class RuleBasedDemoBackend:
    name = "rules"
    metadata = {"implementation": "rule-demo/1.0"}

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def generate(self, context: dict[str, Any], schema: dict[str, Any]) -> str:
        cards = sorted(
            context["candidate_observations"],
            key=lambda item: (-float(item["magnitude_z"]), item["alias"]),
        )
        top = cards[0] if cards else None
        label = (
            self._config.label_rules.get(str(top["variable"]).casefold())
            if top is not None
            else None
        )
        if (
            top is None
            or label is None
            or context["evidence_status"] != "sufficient_candidates"
        ):
            return SafeFallbackBackend(self._config).generate(context, schema)

        confidence = round(min(0.95, 0.55 + float(top["magnitude_z"]) / 20), 3)
        action = (
            "INSPECT_SENSOR_TRENDS"
            if "INSPECT_SENSOR_TRENDS" in self._config.allowed_actions
            else "ESCALATE_TO_HUMAN"
        )
        record = {
            "schema_version": self._config.schema_version,
            "event_id": context["event_id"],
            "candidate_explanations": [
                {
                    "label": label,
                    "explanation": (
                        f"{top['variable']} shows a {top['direction']} pattern with "
                        f"robust magnitude {top['magnitude_z']}."
                    ),
                    "variables": [top["variable"]],
                    "supporting_evidence": [top["alias"]],
                    "contradicting_evidence": [],
                    "missing_information": [],
                    "confidence": confidence,
                    "action": action,
                }
            ],
        }
        return json.dumps(record, ensure_ascii=False, allow_nan=False)


class ReplayBackend:
    name = "replay"

    def __init__(self, response_path: Path) -> None:
        self._response_path = response_path
        self.metadata = {"response_name": response_path.name}

    def generate(self, context: dict[str, Any], schema: dict[str, Any]) -> str:
        payload = read_json(self._response_path)
        return json.dumps(payload, ensure_ascii=False, allow_nan=False)


class OpenAICompatibleBackend:
    name = "openai-compatible"

    def __init__(self) -> None:
        self._base_url = os.environ.get("AEB_LLM_BASE_URL", "").rstrip("/")
        self._api_key = os.environ.get("AEB_LLM_API_KEY", "")
        self._model = os.environ.get("AEB_LLM_MODEL", "")
        if not self._base_url or not self._model:
            raise ValueError(
                "AEB_LLM_BASE_URL and AEB_LLM_MODEL are required for this backend"
            )
        self.metadata = {"model": self._model}

    def generate(self, context: dict[str, Any], schema: dict[str, Any]) -> str:
        system = (
            "You are an industrial post-alarm diagnostic assistant. Return one JSON "
            "object matching the supplied schema. Use only event-local evidence aliases. "
            "State support, contradiction, missing information, confidence, and one "
            "allowed action. Never propose direct equipment control."
        )
        body = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"context": context, "schema": schema},
                        ensure_ascii=False,
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "auditable_diagnosis",
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **(
                    {"Authorization": f"Bearer {self._api_key}"}
                    if self._api_key
                    else {}
                ),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"diagnostic model request failed: HTTP {exc.code}: {detail}")
        return str(payload["choices"][0]["message"]["content"])


def create_backend(
    name: str,
    config: AppConfig,
    replay_path: Path | None = None,
) -> DiagnosisBackend:
    if name == "safe":
        return SafeFallbackBackend(config)
    if name == "rules":
        return RuleBasedDemoBackend(config)
    if name == "replay":
        if replay_path is None:
            raise ValueError("--replay-response is required for the replay backend")
        return ReplayBackend(replay_path)
    if name == "openai-compatible":
        return OpenAICompatibleBackend()
    raise ValueError(f"unknown backend: {name}")
