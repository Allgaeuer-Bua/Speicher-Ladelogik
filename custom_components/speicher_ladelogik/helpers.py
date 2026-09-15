"""Pure helper functions for Speicher-Ladelogik."""

from __future__ import annotations

from math import isfinite
from typing import Any


def as_number(value: Any) -> float | None:
    """Return a finite float or None."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def power_in_watts(value: Any, unit: str | None) -> float | None:
    """Convert a numeric W/kW value to watts."""
    result = as_number(value)
    if result is None:
        return None
    normalized = (unit or "W").strip().lower()
    if normalized == "kw":
        return result * 1000
    if normalized == "w":
        return result
    return None


def is_usable_state(value: Any) -> bool:
    """Return whether a Home Assistant state contains usable data."""
    return value is not None and str(value).lower() not in {
        "",
        "none",
        "unknown",
        "unavailable",
    }


def conversion_metrics(ac_w: float | None, dc_w: float | None) -> dict[str, Any]:
    """Return direction-aware efficiency and loss for the Venus sign convention."""
    mode = "Leerlauf"
    efficiency = None
    loss = None
    if ac_w is not None and dc_w is not None:
        if ac_w < -1 and dc_w > 1:
            mode = "Laden"
            input_w, output_w = abs(ac_w), abs(dc_w)
        elif ac_w > 1 and dc_w < -1:
            mode = "Entladen"
            input_w, output_w = abs(dc_w), abs(ac_w)
        else:
            input_w = output_w = 0
        if input_w > 1:
            candidate = output_w / input_w * 100
            if 0 < candidate <= 120:
                efficiency = round(candidate, 1)
                loss = round(max(0.0, input_w - output_w))
            else:
                mode = "Messwerte nicht plausibel"
    return {
        "wirkungsgrad": efficiency,
        "verlust_w": loss,
        "modus": mode,
        "ac_w": ac_w,
        "dc_w": dc_w,
    }
