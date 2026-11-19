"""Verify the current manuscript snapshot using only the Python standard library."""
from hashlib import sha256
import json
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    package = root / "docs" / "manuscript" / "current"
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    checked = 0
    for name, expected in manifest["files"].items():
        path = (package / name).resolve()
        if not path.is_relative_to(package.resolve()):
            raise ValueError("manifest path leaves the manuscript package")
        data = path.read_bytes()
        if len(data) != expected["bytes"] or sha256(data).hexdigest() != expected["sha256"]:
            raise ValueError(f"manuscript checksum mismatch: {name}")
        checked += 1
    if checked == 0:
        raise ValueError("empty manuscript manifest")
    print(json.dumps({"package": package.name, "files_verified": checked, "status": "passed"}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
