from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .audit import audit_response
from .canonical import read_json, sha256_bytes, sha256_json, write_json, write_text
from .config import AppConfig
from .diagnosis import DiagnosisBackend, build_diagnosis_schema
from .domain import parse_event
from .evidence import extract_candidate_cards
from .observability import RunLogger
from .provenance import bind_evidence


@dataclass(frozen=True)
class PipelineResult:
    run_id: str
    status: str
    run_dir: Path
    audit_record: dict[str, Any]


class Pipeline:
    def __init__(self, config: AppConfig, backend: DiagnosisBackend) -> None:
        self._config = config
        self._backend = backend

    @staticmethod
    def _prepare_run_dir(run_dir: Path, force: bool) -> None:
        resolved = run_dir.resolve()
        protected = {
            Path.cwd().resolve(),
            Path.home().resolve(),
            Path(resolved.anchor).resolve(),
        }
        if resolved in protected:
            raise ValueError("run directory must not be a filesystem or workspace root")
        if run_dir.exists() and any(run_dir.iterdir()):
            if not force:
                raise FileExistsError(
                    "run directory is not empty; choose another directory or use --force"
                )
            generated_run = (run_dir / "run-manifest.json").is_file() or (
                run_dir / "logs" / "pipeline.jsonl"
            ).is_file()
            if not generated_run:
                raise FileExistsError(
                    "refusing to replace a non-empty directory not created by this pipeline"
                )
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        input_path: Path,
        run_dir: Path,
        *,
        force: bool = False,
    ) -> PipelineResult:
        self._prepare_run_dir(run_dir, force)
        logger = RunLogger(run_dir)
        try:
            raw_input = input_path.read_bytes()
            input_hash = sha256_bytes(raw_input)
            config_hash = sha256_json(
                {
                    "schema_version": self._config.schema_version,
                    "extractor_version": self._config.extractor_version,
                    "reference_version": self._config.reference_version,
                    "alias_salt_sha256": sha256_bytes(
                        self._config.alias_salt.encode("utf-8")
                    ),
                    "allowed_labels": self._config.allowed_labels,
                    "allowed_actions": self._config.allowed_actions,
                    "label_rules": self._config.label_rules,
                    "evidence": self._config.evidence.__dict__,
                    "safety": self._config.safety.__dict__,
                }
            )
        except Exception as exc:
            logger.emit(
                "run_failed",
                stage="pipeline",
                status="failed",
                message="auditable diagnosis run failed before event loading",
                error_type=type(exc).__name__,
            )
            logger.close()
            raise
        logger.emit(
            "run_started",
            stage="pipeline",
            status="running",
            message="auditable diagnosis run started",
            backend=self._backend.name,
            backend_metadata=self._backend.metadata,
            input_name=input_path.name,
            input_sha256=input_hash,
            config_sha256=config_hash,
        )

        try:
            with logger.stage("load_event") as details:
                event = parse_event(read_json(input_path))
                details.update(
                    event_id_hash=sha256_json(event.event_id),
                    signal_count=len(event.signals),
                    alarm_start_index=event.alarm.start_index,
                    alarm_end_index=event.alarm.end_index,
                    detector=event.detector.name,
                )

            with logger.stage("extract_evidence") as details:
                cards = extract_candidate_cards(event, self._config.evidence)
                details.update(
                    card_count=len(cards),
                    minimum_required=self._config.evidence.minimum_cards,
                    top_variables=[card.variable for card in cards],
                    top_scores=[card.score for card in cards],
                )

            with logger.stage("bind_provenance") as details:
                prepared = bind_evidence(event, cards, self._config)
                context_path = run_dir / "context" / "model-visible-context.json"
                registry_path = run_dir / "context" / "provenance-registry.json"
                write_json(context_path, prepared.model_context)
                write_json(registry_path, prepared.registry)
                details.update(
                    event_alias=prepared.event_alias,
                    registered_aliases=sorted(prepared.registry["cards"]),
                    context_sha256=sha256_json(prepared.model_context),
                    registry_sha256=sha256_json(prepared.registry),
                )

            with logger.stage("build_schema") as details:
                aliases = sorted(prepared.registry["cards"])
                schema = build_diagnosis_schema(self._config, aliases)
                schema_path = run_dir / "diagnosis" / "diagnosis.schema.json"
                write_json(schema_path, schema)
                details.update(
                    schema_version=self._config.schema_version,
                    dynamic_alias_count=len(aliases),
                    schema_sha256=sha256_json(schema),
                )

            with logger.stage("generate_diagnosis") as details:
                raw_response = self._backend.generate(prepared.model_context, schema)
                raw_path = run_dir / "diagnosis" / "raw-response.txt"
                write_text(raw_path, raw_response)
                details.update(
                    backend=self._backend.name,
                    response_bytes=len(raw_response.encode("utf-8")),
                    response_sha256=sha256_bytes(raw_response.encode("utf-8")),
                )

            with logger.stage("audit_diagnosis") as details:
                outcome = audit_response(
                    raw_response,
                    schema,
                    prepared.model_context,
                    prepared.registry,
                    self._config,
                )
                audit_path = run_dir / "audit" / "audit-record.json"
                write_json(audit_path, outcome.audit_record)
                if outcome.parsed_record is not None:
                    write_json(
                        run_dir / "diagnosis" / "record.json",
                        outcome.parsed_record,
                    )
                details.update(
                    final_status=outcome.status,
                    layer_statuses={
                        name: layer["status"]
                        for name, layer in outcome.audit_record["layers"].items()
                    },
                )

            with logger.stage("write_manifest") as details:
                artifact_names = [
                    "context/model-visible-context.json",
                    "context/provenance-registry.json",
                    "diagnosis/diagnosis.schema.json",
                    "diagnosis/raw-response.txt",
                    "audit/audit-record.json",
                ]
                record_path = run_dir / "diagnosis" / "record.json"
                if record_path.exists():
                    artifact_names.append("diagnosis/record.json")
                artifacts = {
                    name: sha256_bytes((run_dir / name).read_bytes())
                    for name in artifact_names
                }
                manifest = {
                    "manifest_version": "aeb-run-manifest/1.0",
                    "software_version": __version__,
                    "run_id": logger.run_id,
                    "input_name": input_path.name,
                    "input_sha256": input_hash,
                    "config_sha256": config_hash,
                    "backend": self._backend.name,
                    "backend_metadata": self._backend.metadata,
                    "final_status": outcome.status,
                    "artifacts": artifacts,
                    "logs": [
                        "logs/pipeline.log",
                        "logs/pipeline.jsonl",
                    ],
                }
                write_json(run_dir / "run-manifest.json", manifest)
                details.update(
                    artifact_count=len(artifacts),
                    manifest_sha256=sha256_json(manifest),
                )

            logger.emit(
                "run_completed",
                stage="pipeline",
                status=outcome.status,
                message=f"auditable diagnosis run completed: {outcome.status}",
                final_status=outcome.status,
                manifest="run-manifest.json",
            )
            return PipelineResult(
                run_id=logger.run_id,
                status=outcome.status,
                run_dir=run_dir,
                audit_record=outcome.audit_record,
            )
        except Exception:
            logger.emit(
                "run_failed",
                stage="pipeline",
                status="failed",
                message="auditable diagnosis run failed closed",
            )
            raise
        finally:
            logger.close()
