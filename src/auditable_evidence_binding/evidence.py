from __future__ import annotations

import statistics

from .config import EvidenceConfig
from .domain import EvidenceCard, SensorEvent, SignalSeries


def _robust_scale(values: tuple[float, ...], floor: float) -> tuple[float, bool]:
    center = statistics.median(values)
    mad = statistics.median(abs(value - center) for value in values)
    scaled = 1.4826 * mad
    return max(scaled, floor), scaled < floor


def _extract_signal_card(
    signal: SignalSeries,
    event: SensorEvent,
    config: EvidenceConfig,
) -> EvidenceCard:
    event_values = signal.values[event.alarm.start_index : event.alarm.end_index + 1]
    local_start = max(0, event.alarm.start_index - config.local_reference_points)
    local_values = signal.values[local_start : event.alarm.start_index]
    global_center = statistics.median(signal.reference_values)
    local_center = statistics.median(local_values)
    event_center = statistics.median(event_values)
    scale, floor_applied = _robust_scale(
        signal.reference_values,
        config.robust_scale_floor,
    )

    global_z = (event_center - global_center) / scale
    local_z = (event_center - local_center) / scale
    peak_z = max(
        event_values,
        key=lambda value: abs(value - global_center),
    )
    peak_z = (peak_z - global_center) / scale
    trend_z = (event_values[-1] - event_values[0]) / scale
    direction_basis = local_z if abs(local_z) >= abs(global_z) else global_z
    if direction_basis > config.direction_epsilon:
        direction = "increase"
    elif direction_basis < -config.direction_epsilon:
        direction = "decrease"
    else:
        direction = "stable"

    flags: list[str] = []
    if floor_applied:
        flags.append("scale_floor_applied")
    if len(signal.reference_values) < 8:
        flags.append("short_global_reference")
    if len(local_values) < config.local_reference_points:
        flags.append("short_local_reference")
    if not flags:
        flags.append("none")

    score = (
        config.score_global_weight * abs(global_z)
        + config.score_local_weight * abs(local_z)
        + config.score_peak_weight * abs(peak_z)
        + config.score_trend_weight * abs(trend_z)
    )
    rounded = lambda value: round(float(value), 6)
    return EvidenceCard(
        variable=signal.name,
        unit=signal.unit,
        process_role=signal.process_role,
        direction=direction,
        magnitude_z=rounded(max(abs(global_z), abs(local_z), abs(peak_z))),
        global_deviation_z=rounded(global_z),
        local_deviation_z=rounded(local_z),
        peak_deviation_z=rounded(peak_z),
        trend_z=rounded(trend_z),
        duration_points=len(event_values),
        quality_flags=tuple(flags),
        score=rounded(score),
    )


def extract_candidate_cards(
    event: SensorEvent,
    config: EvidenceConfig,
) -> list[EvidenceCard]:
    cards = [_extract_signal_card(signal, event, config) for signal in event.signals]
    cards.sort(key=lambda card: (-card.score, card.variable.casefold()))
    return cards[: config.top_k]
