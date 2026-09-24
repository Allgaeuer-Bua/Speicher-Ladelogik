"""Compact persisted calibration results for the dashboard."""

from __future__ import annotations

import math
from typing import Any


def _finite(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def last_successful_result(
    control: dict[str, Any], slot: str, success_ts: float | None
) -> dict[str, Any] | None:
    """Return the latest completed run, retaining older success-only records."""
    stamp = _finite(success_ts)
    if stamp is None or stamp <= 0:
        return None

    learning = control.get("lernspeicher")
    history = learning.get("history", []) if isinstance(learning, dict) else []
    records = [
        record for record in history if isinstance(record, dict)
        and record.get("battery") == slot and record.get("result") == "done"
        and (ended := _finite(record.get("end"))) is not None
        and abs(ended - stamp) <= 120
    ] if isinstance(history, list) else []
    latest = max(records, key=lambda item: float(item["end"])) if records else None
    energy = _finite(
        latest.get("ac_kwh") if latest else control.get(
            f"kalibrierung_{slot.lower()}_letzte_energie"
        )
    )
    drift = latest.get("drift_after_mv", []) if latest else []
    if not isinstance(drift, list):
        drift = []
    top_start = latest.get("drift_top_start_mv", []) if latest else []
    if not isinstance(top_start, list):
        top_start = []
    top_end = [_finite(value) for value in drift]
    top_start = [_finite(value) for value in top_start]
    change = [round(after - before, 1) if before is not None and after is not None else None
              for before, after in zip(top_start, top_end)]
    return {
        "end_ts": stamp,
        "ac_kwh": energy if energy is not None and energy > 0 else None,
        "learned": bool(latest.get("learning_valid")) if latest else None,
        "drift_after_mv": top_end,
        "drift_top_start_mv": top_start,
        "drift_top_change_mv": change,
    }
