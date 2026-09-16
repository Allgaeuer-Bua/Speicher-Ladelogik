"""State-based charge-limit stability for Speicher-Ladelogik."""

from __future__ import annotations

from typing import Any

PEER_DISCHARGE_RELEASE_PERCENT = 14.0
DECISION_SLOT_SECONDS = 15 * 60

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
    """Evaluate only the device's configured upper SoC boundary."""
    if soc is None or lowest_soc is None:
        return False, "Messwert fehlt"

    if soc >= goal and lowest_soc >= goal:
        return True, "Ziel aktuell erreicht"

    return False, f"Ladebedarf unter {goal:g} %"


def peer_discharge_release(
    *,
    phase: str,
    target_soc: float | None,
    highest_pack_soc: float | None,
    prior_released: bool,
) -> tuple[bool, str]:
    """Release the peer battery once during calibration drain at 14 %."""
    if phase != "drain":
        return False, "Nur während der Entladevorbereitung"
    if prior_released:
        return True, "Freigabe bei 14 % bereits verriegelt"

    decisive_soc = highest_pack_soc
    if decisive_soc is None:
        decisive_soc = target_soc
    if decisive_soc is None:
        return False, "SoC für 14-%-Freigabe fehlt"
    if decisive_soc <= PEER_DISCHARGE_RELEASE_PERCENT:
        return True, "Kalibrierspeicher hat 14 % erreicht"
    return False, "Kalibrierspeicher noch über 14 %"


def quarter_hour_window(now_ts: float) -> tuple[int, int]:
    """Return the fixed 15-minute planning slot containing ``now_ts``."""
    start = int(now_ts // DECISION_SLOT_SECONDS) * DECISION_SLOT_SECONDS
    return start, start + DECISION_SLOT_SECONDS


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
    decision_locked: bool = False,
    slot_was_active: bool = False,
) -> tuple[int, bool, str]:
    """Keep a useful register value until a real state change requires another."""
    raw = int(max(0.0, min(current_cap, raw_limit)))
    previous = int(max(0.0, min(current_cap, previous_limit)))

    if safety_stop:
        return 0, False, "Sicherheitsstopp"
    if target_reached:
        # Das Geräteziel ist maßgeblich. Bei erreichtem Ziel bleibt der zuletzt
        # gesetzte Registerwert bestehen; das Gerät beendet die Aufnahme selbst.
        return previous, previous > 0, "Geräteziel erreicht; Registerwert bleibt stehen"
    if not eligible:
        return 0, False, "Speicher nicht für Fahrplan freigegeben"
    if decision_locked:
        # The forecast itself is resolved in 15-minute intervals. Once the
        # automatic planner has made a decision for the current interval, do
        # not let 30-second live-value fluctuations move the start time and
        # toggle the charge register repeatedly. AstraMeter still performs the
        # fast power control at the grid connection point.
        if slot_was_active:
            if previous > 0:
                return previous, True, "Aktiven 15-Minuten-Ladeslot beibehalten"
            if raw > 0:
                return raw, False, "Aktiven 15-Minuten-Ladeslot wiederherstellen"
        return 0, False, "15-Minuten-Pausenslot beibehalten"
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
