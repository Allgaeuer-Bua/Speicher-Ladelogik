"""State-based charge-limit stability for Speicher-Ladelogik A/E."""

from __future__ import annotations

from typing import Any

PEER_DISCHARGE_RELEASE_PERCENT = 14.0
PEER_GRID_IMPORT_RELEASE_W = 50.0
PEER_GRID_IMPORT_CLEAR_W = 25.0
PEER_GRID_DELAY_SECONDS = 15.0
FORECAST_EVIDENCE_START_WH = 750.0
FORECAST_EVIDENCE_FULL_WH = 5000.0
DAY_CLASS_CONFIRM_SECONDS = 15 * 60
DAY_CLASS_MARGIN_KWH = 2.0

def forecast_day_factor(actual_kwh: float | None, past_wh: float) -> tuple[float, float]:
    """Use a measured PV shortfall gradually after enough predicted morning energy."""
    if actual_kwh is None or past_wh <= FORECAST_EVIDENCE_START_WH:
        return 1.0, 0.0
    confidence = min(1.0, (past_wh - FORECAST_EVIDENCE_START_WH)
                     / (FORECAST_EVIDENCE_FULL_WH - FORECAST_EVIDENCE_START_WH))
    observed = max(0.2, min(1.0, actual_kwh * 1000 / past_wh))
    return 1.0 - (1.0 - observed) * confidence, confidence


def forecast_factor(short_factor: float, day_factor: float, horizon_seconds: float) -> float:
    """Trust current output near term, but restore the independent later forecast.

    A cloudy morning is evidence for the next hours, not for the whole day.
    """
    hours = max(0.0, horizon_seconds) / 3600
    if hours < 2:
        return short_factor + (day_factor - short_factor) * hours / 2
    if hours < 4:
        return day_factor + (1.0 - day_factor) * (hours - 2) / 2
    return 1.0


def stable_day_class(
    expected_kwh: float, boundaries: tuple[float, float, float],
    now_ts: float, day_start_ts: float, prior: dict[str, Any],
) -> tuple[str, str | None, float | None]:
    """Confirm a class change across a small deadband for fifteen minutes."""
    weak, _middle, strong = boundaries
    classes = ("schwach", "mittel", "stark")
    desired = "schwach" if expected_kwh <= weak else "mittel" if expected_kwh < strong else "stark"
    previous = prior.get("tagesklasse")
    previous_ts = prior.get("berechnet_ts")
    if previous not in classes or not isinstance(previous_ts, (int, float)) \
            or not day_start_ts <= previous_ts <= now_ts or now_ts - previous_ts > 3600:
        return desired, None, None
    current_index, desired_index = classes.index(previous), classes.index(desired)
    if current_index == desired_index:
        return previous, None, None
    boundary = (weak, strong)
    if desired_index > current_index:
        crossed = expected_kwh >= boundary[current_index] + DAY_CLASS_MARGIN_KWH
    else:
        crossed = expected_kwh <= boundary[current_index - 1] - DAY_CLASS_MARGIN_KWH
    if not crossed:
        return previous, None, None
    since = prior.get("tagesklasse_kandidat_seit_ts")
    if prior.get("tagesklasse_kandidat") != desired or not isinstance(since, (int, float)) \
            or since > now_ts or since < day_start_ts:
        return previous, desired, now_ts
    if now_ts - since < DAY_CLASS_CONFIRM_SECONDS:
        return previous, desired, since
    return desired, None, None


def migrate_legacy_day_class_goals(
    control: dict[str, Any], persisted: dict[str, Any], day_classes: tuple[str, ...],
) -> None:
    """Keep the previous storage target in every class on first upgrade."""
    for slot in ("a", "d", "e"):
        legacy = control[f"fruehes_ladeziel_{slot}_soc"]
        for day_class in day_classes:
            key = f"fruehes_ladeziel_{slot}_{day_class}_soc"
            if key not in persisted:
                control[key] = legacy


def calibration_available_surplus(
    live_surplus_w: float,
    actual_charge_w: float | None,
    *,
    running: bool,
) -> float:
    """The PV/house and grid/battery balances already exclude battery draw.

    Keep the call signature compatible; never add measured charging a second
    time, which would classify grid-supported charging as available PV.
    """
    return max(0.0, float(live_surplus_w))


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


def peer_grid_support(
    *,
    phase: str,
    now_ts: float,
    grid_power_w: float | None,
    permanent_release: bool,
    temporary_release: bool,
    import_since_ts: float | None,
    clear_since_ts: float | None,
) -> tuple[bool, float | None, float | None, str]:
    """Temporarily release the peer after sustained grid import.

    Positive grid power means import. The small on/off power hysteresis keeps
    normal zero-point noise from toggling the peer discharge register. The
    timers are stored in otherwise unused drain-session fields so the decision
    survives coordinator updates and Home Assistant restarts.
    """
    if phase != "drain":
        return False, None, None, "Nur während der Entladevorbereitung"
    if permanent_release:
        return False, None, None, "Dauerfreigabe bei 14 % hat Vorrang"
    if grid_power_w is None:
        return (
            temporary_release,
            import_since_ts,
            clear_since_ts,
            "Netzleistung fehlt; bisherigen Zustand beibehalten",
        )

    grid_power = float(grid_power_w)
    if temporary_release:
        if grid_power <= PEER_GRID_IMPORT_CLEAR_W:
            clear_since = clear_since_ts or now_ts
            if now_ts - clear_since >= PEER_GRID_DELAY_SECONDS:
                return False, None, None, "Seit 15 Sekunden kein Netzbezug"
            return True, import_since_ts, clear_since, "Netzbezug klingt ab"
        return True, import_since_ts, None, "Partner wegen Netzbezug freigegeben"

    if grid_power >= PEER_GRID_IMPORT_RELEASE_W:
        import_since = import_since_ts or now_ts
        if now_ts - import_since >= PEER_GRID_DELAY_SECONDS:
            return True, import_since, None, "Netzbezug seit 15 Sekunden"
        return False, import_since, None, "Netzbezug wird bestätigt"
    return False, None, None, "Kein anhaltender Netzbezug"


def calibration_required_seconds(required_hours: float) -> int:
    """Return the exact whole-second charging requirement for a PV window."""
    return max(1, int(required_hours * 3600 + 0.5))
