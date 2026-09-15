"""Pure control helpers for the guarded Beta-7 register writer."""

from __future__ import annotations

from typing import Any

WRITE_TOLERANCE_W = 25.0

REQUEST_ENTITIES = {
    "input_button.speicher_ladelogik_kalibrierung_a_anfordern": "cal_a",
    "input_button.speicher_ladelogik_kalibrierung_e_anfordern": "cal_e",
    "input_button.speicher_ladelogik_kalibrierung_a_morgen": "cal_a_tomorrow",
    "input_button.speicher_ladelogik_kalibrierung_e_morgen": "cal_e_tomorrow",
    "input_button.speicher_ladelogik_kalibrierung_a_entfernen": "cancel_a",
    "input_button.speicher_ladelogik_kalibrierung_e_entfernen": "cancel_e",
    "input_button.speicher_ladelogik_kalibrierung_abbrechen": "cancel",
    "input_button.speicher_ladelogik_fehler_quittieren": "ack",
    "input_button.pv_kalibrierung_a_anfordern": "cal_a",
    "input_button.pv_kalibrierung_e_anfordern": "cal_e",
    "input_button.pv_kalibrierung_a_morgen": "cal_a_tomorrow",
    "input_button.pv_kalibrierung_e_morgen": "cal_e_tomorrow",
    "input_button.pv_kalibrierung_a_entfernen": "cancel_a",
    "input_button.pv_kalibrierung_e_entfernen": "cancel_e",
    "input_button.pv_kalibrierung_abbrechen": "cancel",
    "input_button.pv_ladelogik_fehler_quittieren": "ack",
}

SESSION_ENTITY = "input_text.speicher_ladelogik_kalibrierung_sitzung"
QUEUE_ENTITY = "input_text.speicher_ladelogik_kalibrierung_vormerkungen"
BACKUP_ENTITY = "input_text.speicher_ladelogik_sicherung"
CAL_BACKUP_ENTITY = "input_text.speicher_ladelogik_kalibrierung_sicherung"
CONTROL_HELPERS = (SESSION_ENTITY, QUEUE_ENTITY, BACKUP_ENTITY, CAL_BACKUP_ENTITY)

LEGACY_CONTROLLER_ENTITIES = (
    "automation.pv_ladelogik_astrameter_regelung",
    "automation.pv_ladelogik_v2_planungswachter",
    "automation.speicher_ladelogik_astrameter_regelung",
    "automation.speicher_ladelogik_planungswachter",
)


def validate_number_target(
    *, current: Any, minimum: Any, maximum: Any, step: Any, target: Any
) -> str | None:
    """Validate a number write against the entity's advertised range and step."""
    try:
        current_value = float(current)
        minimum_value = float(minimum)
        maximum_value = float(maximum)
        step_value = float(step)
        target_value = float(target)
    except (TypeError, ValueError):
        return "Zustand oder Gerätegrenzen sind nicht numerisch"
    if step_value <= 0:
        return "Ungültige Schrittweite"
    if not minimum_value <= target_value <= maximum_value:
        return "Zielwert liegt außerhalb der Gerätegrenzen"
    steps = (target_value - minimum_value) / step_value
    if abs(steps - round(steps)) >= 0.001:
        return "Zielwert passt nicht zur Schrittweite"
    if any(value != value for value in (current_value, target_value)):
        return "Ungültiger Zahlenwert"
    return None


def write_needed(current: Any, target: Any) -> bool:
    """Return whether a register differs materially from its target."""
    try:
        return abs(float(current) - float(target)) >= WRITE_TOLERANCE_W
    except (TypeError, ValueError):
        return True
