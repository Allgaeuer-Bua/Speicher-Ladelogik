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
