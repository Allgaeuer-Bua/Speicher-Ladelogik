"""State-based charge-limit stability for Speicher-Ladelogik."""

from __future__ import annotations

from typing import Any

TARGET_RELEASE_HYSTERESIS_PERCENT = 2.0

DELIBERATE_ZERO_STATUSES = {
    "Datenfehler",
    "Platz für Mittagsspitze halten",
    "Speicher einzeln gesperrt / vorgemerkt",
    "Ziel erreicht",
    "Zurückhalten",
}


def target_latch(
    *,
    goal: float,
    soc: float | None,
    lowest_soc: float | None,
    prior_latched: bool,
    prior_goal: Any,
) -> tuple[bool, str]:
    """Latch a reached charge target until SoC drops meaningfully below it."""
    if soc is None or lowest_soc is None:
        return False, "Messwert fehlt"

    if soc >= goal and lowest_soc >= goal:
        return True, "Ziel aktuell erreicht"

    try:
        same_goal = abs(float(prior_goal) - goal) < 0.01
    except (TypeError, ValueError):
        same_goal = False

    release_at = max(0.0, goal - TARGET_RELEASE_HYSTERESIS_PERCENT)
    if prior_latched and same_goal and soc >= release_at and lowest_soc >= release_at:
        return True, f"Ziel gehalten bis unter {release_at:g} %"

    return False, f"Ladebedarf unter {goal:g} %"


def stable_charge_limit(
    *,
    raw_limit: float,
    previous_limit: float,
    current_cap: float,
    eligible: bool,
    target_reached: bool,
    within_window: bool,
    planner_status: str,
    safety_stop: bool,
) -> tuple[int, bool, str]:
    """Keep a useful register value until a real state change requires another."""
    raw = int(max(0.0, min(current_cap, raw_limit)))
    previous = int(max(0.0, min(current_cap, previous_limit)))

    if safety_stop:
        return 0, False, "Sicherheitsstopp"
    if not eligible:
        return 0, False, "Speicher nicht für Fahrplan freigegeben"
    if target_reached:
        return 0, False, "Ziel erreicht"
    if planner_status in DELIBERATE_ZERO_STATUSES:
        return 0, False, "Bewusste Fahrplanpause"
    if not within_window:
        return 0, False, "Außerhalb des Ladefensters"

    if raw > previous:
        return raw, False, "Höhere Leistung erforderlich"
    if raw > 0:
        if previous > raw:
            return previous, True, "Bisherigen Fahrplanwert beibehalten"
        return raw, False, "Fahrplanwert aktiv"
    if previous > 0:
        return previous, True, "Bei kurzer Überschusspause beibehalten"
    return 0, False, "Keine Ladephase aktiv"
