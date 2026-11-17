from __future__ import annotations

from pathlib import Path

from .canonical import read_json, sha256_bytes
from .config import AppConfig, config_fingerprint


def artifact_issues(run_dir: Path, config: AppConfig) -> list[str]:
    """Check saved artifacts against their original local run manifest."""
    manifest_path = run_dir / "run-manifest.json"
    if not manifest_path.is_file():
        return ["run manifest is missing"]
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict):
        return ["run manifest must be an object"]

    issues = []
    if manifest.get("manifest_version") != "aeb-run-manifest/1.0":
        issues.append("unsupported run manifest version")
    if manifest.get("config_sha256") != config_fingerprint(config):
        issues.append("configuration hash mismatch")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        return [*issues, "artifact hash mapping is missing"]

    required = {
        "context/model-visible-context.json",
        "context/provenance-registry.json",
        "diagnosis/diagnosis.schema.json",
        "diagnosis/raw-response.txt",
        "audit/audit-record.json",
    }
    if (run_dir / "diagnosis" / "record.json").exists():
        required.add("diagnosis/record.json")
    for name in sorted(required - artifacts.keys()):
        issues.append(f"artifact missing from manifest: {name}")

    root = run_dir.resolve()
    for name, expected in artifacts.items():
        relative = Path(name)
        path = (run_dir / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(root):
            issues.append("artifact path must stay inside the run directory")
        elif not path.is_file():
            issues.append(f"artifact is missing: {name}")
        elif sha256_bytes(path.read_bytes()) != expected:
            issues.append(f"artifact hash mismatch: {name}")
    return issues
