from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .audit import audit_response
from .canonical import read_json, write_json
from .config import load_config
from .diagnosis import build_diagnosis_schema, create_backend
from .pipeline import Pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aeb-diagnose",
        description="Run auditable evidence binding for one frozen alarm event.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="execute the complete diagnosis pipeline")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--run-dir", type=Path, required=True)
    run.add_argument(
        "--backend",
        choices=("safe", "rules", "replay", "openai-compatible"),
        default="safe",
    )
    run.add_argument("--replay-response", type=Path)
    run.add_argument("--force", action="store_true")

    schema = commands.add_parser("schema", help="materialize the dynamic JSON schema")
    schema.add_argument("--config", type=Path, required=True)
    schema.add_argument("--output", type=Path, required=True)

    verify = commands.add_parser("verify", help="re-audit an existing run")
    verify.add_argument("--config", type=Path, required=True)
    verify.add_argument("--run-dir", type=Path, required=True)
    return parser


def _run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    backend = create_backend(args.backend, config, args.replay_response)
    result = Pipeline(config, backend).run(
        args.input,
        args.run_dir,
        force=args.force,
    )
    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "final_status": result.status,
                "manifest": "run-manifest.json",
                "human_log": "logs/pipeline.log",
                "structured_log": "logs/pipeline.jsonl",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.status in {"accepted", "escalated"} else 2


def _schema(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    aliases = [f"E{index:02d}" for index in range(1, config.evidence.top_k + 1)]
    write_json(args.output, build_diagnosis_schema(config, aliases))
    print(json.dumps({"schema": args.output.name}, indent=2))
    return 0


def _verify(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    run_dir = args.run_dir
    raw = (run_dir / "diagnosis" / "raw-response.txt").read_text(encoding="utf-8")
    outcome = audit_response(
        raw,
        read_json(run_dir / "diagnosis" / "diagnosis.schema.json"),
        read_json(run_dir / "context" / "model-visible-context.json"),
        read_json(run_dir / "context" / "provenance-registry.json"),
        config,
    )
    print(json.dumps(outcome.audit_record, ensure_ascii=False, indent=2))
    return 0 if outcome.status in {"accepted", "escalated"} else 2


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "run":
            return _run(args)
        if args.command == "schema":
            return _schema(args)
        if args.command == "verify":
            return _verify(args)
        raise AssertionError(f"unhandled command: {args.command}")
    except Exception as exc:
        print(f"ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
