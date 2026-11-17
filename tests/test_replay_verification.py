import json
from pathlib import Path

from auditable_evidence_binding.canonical import read_json, write_json
from auditable_evidence_binding.cli import main
from auditable_evidence_binding.config import load_config
from auditable_evidence_binding.diagnosis import ReplayBackend, RuleBasedDemoBackend
from auditable_evidence_binding.pipeline import Pipeline


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "demo.toml"
EVENT = ROOT / "examples" / "demo-event.json"


def make_run(tmp_path):
    config = load_config(CONFIG)
    return Pipeline(config, RuleBasedDemoBackend(config)).run(EVENT, tmp_path / "original")


def verify(run_dir, config=CONFIG):
    return main(["verify", "--config", str(config), "--run-dir", str(run_dir)])


def test_verify_accepts_unchanged_run(tmp_path):
    result = make_run(tmp_path)
    assert verify(result.run_dir) == 0


def test_verify_rejects_changed_policy(tmp_path):
    result = make_run(tmp_path)
    changed = tmp_path / "changed.toml"
    changed.write_text(
        CONFIG.read_text(encoding="utf-8").replace(
            'reference_version = "', 'reference_version = "changed-'
        ),
        encoding="utf-8",
    )
    assert verify(result.run_dir, changed) == 2


def test_verify_rejects_changed_source_coordinates(tmp_path):
    result = make_run(tmp_path)
    registry_path = result.run_dir / "context" / "provenance-registry.json"
    registry = read_json(registry_path)
    first = next(iter(registry["cards"].values()))
    first["coordinates"]["start_index"] += 1
    write_json(registry_path, registry)
    assert verify(result.run_dir) == 2


def test_verify_rejects_changed_derived_record(tmp_path):
    result = make_run(tmp_path)
    record_path = result.run_dir / "diagnosis" / "record.json"
    record = read_json(record_path)
    record["candidate_explanations"][0]["confidence"] = 0.01
    write_json(record_path, record)
    assert verify(result.run_dir) == 2


def test_replay_preserves_duplicate_keys_for_strict_audit(tmp_path):
    original = make_run(tmp_path)
    raw = (original.run_dir / "diagnosis" / "raw-response.txt").read_text(encoding="utf-8")
    record = json.loads(raw)
    duplicated = '{"event_id": ' + json.dumps(record["event_id"]) + ", " + raw[1:]
    response = tmp_path / "duplicate-response.txt"
    response.write_text(duplicated, encoding="utf-8")
    config = load_config(CONFIG)
    replay = Pipeline(config, ReplayBackend(response)).run(EVENT, tmp_path / "replay")
    assert replay.status == "rejected"
    assert replay.audit_record["layers"]["strict_parse"]["status"] == "failed"
    assert (replay.run_dir / "diagnosis" / "raw-response.txt").read_text(
        encoding="utf-8"
    ) == duplicated


def test_replay_accepts_valid_frozen_response(tmp_path):
    original = make_run(tmp_path)
    response = original.run_dir / "diagnosis" / "raw-response.txt"
    config = load_config(CONFIG)
    replay = Pipeline(config, ReplayBackend(response)).run(EVENT, tmp_path / "replay")
    assert replay.status == "accepted"
    assert verify(replay.run_dir) == 0
