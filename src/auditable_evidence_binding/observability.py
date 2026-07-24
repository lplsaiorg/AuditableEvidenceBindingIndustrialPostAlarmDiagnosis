from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class RunLogger:
    def __init__(self, run_dir: Path) -> None:
        log_dir = run_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = uuid.uuid4().hex
        self._jsonl = (log_dir / "pipeline.jsonl").open("w", encoding="utf-8")
        self._human = (log_dir / "pipeline.log").open("w", encoding="utf-8")
        self._sequence = 0
        self._started = time.perf_counter()

    def close(self) -> None:
        self._jsonl.close()
        self._human.close()

    def emit(
        self,
        event: str,
        *,
        stage: str,
        status: str,
        message: str,
        **fields: Any,
    ) -> None:
        self._sequence += 1
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_ms": round((time.perf_counter() - self._started) * 1000, 3),
            "sequence": self._sequence,
            "run_id": self.run_id,
            "event": event,
            "stage": stage,
            "status": status,
            "message": message,
            **fields,
        }
        self._jsonl.write(
            json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n"
        )
        self._jsonl.flush()
        human = (
            f"[{record['sequence']:02d}] {stage:<20} {status.upper():<10} "
            f"{message}"
        )
        self._human.write(human + "\n")
        self._human.flush()
        print(human, flush=True)

    @contextmanager
    def stage(self, name: str) -> Iterator[dict[str, Any]]:
        started = time.perf_counter()
        self.emit(
            "stage_started",
            stage=name,
            status="running",
            message=f"{name} started",
        )
        result: dict[str, Any] = {}
        try:
            yield result
        except Exception as exc:
            self.emit(
                "stage_failed",
                stage=name,
                status="failed",
                message=f"{name} failed",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise
        else:
            self.emit(
                "stage_completed",
                stage=name,
                status="completed",
                message=f"{name} completed",
                duration_ms=round((time.perf_counter() - started) * 1000, 3),
                **result,
            )
