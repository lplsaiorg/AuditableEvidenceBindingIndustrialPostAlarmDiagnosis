import json
from pathlib import Path

import pytest

from auditable_evidence_binding.config import load_config
from auditable_evidence_binding.diagnosis import (
    RuleBasedDemoBackend,
    SafeFallbackBackend,
)
from auditable_evidence_binding.pipeline import Pipeline


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _events_from_log(path: Path) -> list[str]:
    return [
        json.loads(line)["event"]
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


def test_rule_backend_runs_complete_auditable_pipeline(tmp_path: Path) -> None:
    config = load_config(REPOSITORY_ROOT / "configs" / "demo.toml")
    result = Pipeline(config, RuleBasedDemoBackend(config)).run(
        REPOSITORY_ROOT / "examples" / "demo-event.json",
        tmp_path / "accepted-run",
    )

    assert result.status == "accepted"
    assert (result.run_dir / "run-manifest.json").is_file()
    assert (result.run_dir / "diagnosis" / "record.json").is_file()
    assert (result.run_dir / "audit" / "audit-record.json").is_file()
    events = _events_from_log(result.run_dir / "logs" / "pipeline.jsonl")
    assert events[0] == "run_started"
    assert events[-1] == "run_completed"
    assert events.count("stage_completed") == 7

    manifest = json.loads(
        (result.run_dir / "run-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["final_status"] == "accepted"
    assert manifest["backend_metadata"]["implementation"] == "rule-demo/1.0"
    assert all(not Path(name).is_absolute() for name in manifest["artifacts"])
    assert all(not Path(name).is_absolute() for name in manifest["logs"])

    human_log = (result.run_dir / "logs" / "pipeline.log").read_text(
        encoding="utf-8"
    )
    structured_log = (result.run_dir / "logs" / "pipeline.jsonl").read_text(
        encoding="utf-8"
    )
    assert str(REPOSITORY_ROOT) not in human_log
    assert str(REPOSITORY_ROOT) not in structured_log
    assert "extract_evidence" in human_log
    assert "bind_provenance" in human_log
    assert "audit_diagnosis" in human_log
    assert "ACCEPTED" in human_log


def test_safe_backend_completes_with_human_escalation(tmp_path: Path) -> None:
    config = load_config(REPOSITORY_ROOT / "configs" / "demo.toml")
    result = Pipeline(config, SafeFallbackBackend(config)).run(
        REPOSITORY_ROOT / "examples" / "demo-event.json",
        tmp_path / "escalated-run",
    )

    assert result.status == "escalated"
    assert result.audit_record["layers"]["schema"]["status"] == "passed"
    assert result.audit_record["layers"]["provenance"]["status"] == "passed"
    assert result.audit_record["layers"]["safety"]["status"] == "passed"


def test_force_refuses_to_delete_an_unrelated_directory(tmp_path: Path) -> None:
    config = load_config(REPOSITORY_ROOT / "configs" / "demo.toml")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    sentinel = unrelated / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="not created by this pipeline"):
        Pipeline(config, RuleBasedDemoBackend(config)).run(
            REPOSITORY_ROOT / "examples" / "demo-event.json",
            unrelated,
            force=True,
        )

    assert sentinel.read_text(encoding="utf-8") == "keep"
