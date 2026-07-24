from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


class EventValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Alarm:
    start_index: int
    end_index: int
    score: float


@dataclass(frozen=True)
class Detector:
    name: str
    version: str
    threshold: float


@dataclass(frozen=True)
class SignalSeries:
    name: str
    unit: str
    process_role: str
    values: tuple[float, ...]
    reference_values: tuple[float, ...]


@dataclass(frozen=True)
class SensorEvent:
    event_id: str
    dataset_name: str
    dataset_version: str
    source_id: str
    timestamps: tuple[str, ...]
    alarm: Alarm
    detector: Detector
    signals: tuple[SignalSeries, ...]


@dataclass(frozen=True)
class EvidenceCard:
    variable: str
    unit: str
    process_role: str
    direction: str
    magnitude_z: float
    global_deviation_z: float
    local_deviation_z: float
    peak_deviation_z: float
    trend_z: float
    duration_points: int
    quality_flags: tuple[str, ...]
    score: float

    def model_content(self) -> dict[str, Any]:
        return {
            "variable": self.variable,
            "unit": self.unit,
            "process_role": self.process_role,
            "direction": self.direction,
            "magnitude_z": self.magnitude_z,
            "global_deviation_z": self.global_deviation_z,
            "local_deviation_z": self.local_deviation_z,
            "peak_deviation_z": self.peak_deviation_z,
            "trend_z": self.trend_z,
            "duration_points": self.duration_points,
            "quality_flags": list(self.quality_flags),
        }


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EventValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _finite_number(value: Any, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise EventValidationError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise EventValidationError(f"{field} must be finite")
    return result


def _integer(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise EventValidationError(f"{field} must be an integer")
    return value


def _number_tuple(value: Any, field: str) -> tuple[float, ...]:
    if not isinstance(value, list) or not value:
        raise EventValidationError(f"{field} must be a non-empty array")
    return tuple(_finite_number(item, field) for item in value)


def parse_event(payload: Any) -> SensorEvent:
    if not isinstance(payload, dict):
        raise EventValidationError("event payload must be an object")
    dataset = payload.get("dataset")
    alarm = payload.get("alarm")
    detector = payload.get("detector")
    signals = payload.get("signals")
    timestamps = payload.get("timestamps")
    if not isinstance(dataset, dict):
        raise EventValidationError("dataset must be an object")
    if not isinstance(alarm, dict):
        raise EventValidationError("alarm must be an object")
    if not isinstance(detector, dict):
        raise EventValidationError("detector must be an object")
    if not isinstance(signals, list) or not signals:
        raise EventValidationError("signals must be a non-empty array")
    if not isinstance(timestamps, list) or not timestamps:
        raise EventValidationError("timestamps must be a non-empty array")

    parsed_timestamps = tuple(_non_empty_string(item, "timestamps[]") for item in timestamps)
    start = _integer(alarm.get("start_index"), "alarm.start_index")
    end = _integer(alarm.get("end_index"), "alarm.end_index")
    if start < 1 or end < start or end >= len(parsed_timestamps):
        raise EventValidationError("alarm interval must have pre-alarm data and valid bounds")

    parsed_signals: list[SignalSeries] = []
    names: set[str] = set()
    for index, item in enumerate(signals):
        if not isinstance(item, dict):
            raise EventValidationError(f"signals[{index}] must be an object")
        name = _non_empty_string(item.get("name"), f"signals[{index}].name")
        normalized_name = name.casefold()
        if normalized_name in names:
            raise EventValidationError(f"duplicate signal name: {name}")
        names.add(normalized_name)
        values = _number_tuple(item.get("values"), f"signals[{index}].values")
        if len(values) != len(parsed_timestamps):
            raise EventValidationError(f"signal {name} length must match timestamps")
        parsed_signals.append(
            SignalSeries(
                name=name,
                unit=_non_empty_string(item.get("unit"), f"signals[{index}].unit"),
                process_role=_non_empty_string(
                    item.get("process_role"), f"signals[{index}].process_role"
                ),
                values=values,
                reference_values=_number_tuple(
                    item.get("reference_values"),
                    f"signals[{index}].reference_values",
                ),
            )
        )

    return SensorEvent(
        event_id=_non_empty_string(payload.get("event_id"), "event_id"),
        dataset_name=_non_empty_string(dataset.get("name"), "dataset.name"),
        dataset_version=_non_empty_string(dataset.get("version"), "dataset.version"),
        source_id=_non_empty_string(dataset.get("source_id"), "dataset.source_id"),
        timestamps=parsed_timestamps,
        alarm=Alarm(
            start_index=start,
            end_index=end,
            score=_finite_number(alarm.get("score"), "alarm.score"),
        ),
        detector=Detector(
            name=_non_empty_string(detector.get("name"), "detector.name"),
            version=_non_empty_string(detector.get("version"), "detector.version"),
            threshold=_finite_number(detector.get("threshold"), "detector.threshold"),
        ),
        signals=tuple(parsed_signals),
    )
