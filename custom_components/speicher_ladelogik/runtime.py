"""Persistent native controls and planner-state bridge."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util


CONTROL_DEFAULTS: dict[str, Any] = {
    "mode": "Beobachten",
    "mittagsspitzen": True,
    "manuell_a_aktiv": False,
    "manuell_e_aktiv": False,
    "manuell_d_aktiv": False,
    "manuell_laden_a_w": 0.0,
    "manuell_entladen_a_w": 1500.0,
    "manuell_laden_e_w": 0.0,
    "manuell_entladen_e_w": 2500.0,
    "manuell_laden_d_w": 0.0,
    "manuell_entladen_d_w": 2500.0,
    "bevorzugte_ladeleistung_a_w": 1100.0,
    "bevorzugte_ladeleistung_e_w": 1300.0,
    "bevorzugte_ladeleistung_d_w": 1300.0,
    "nennkapazitaet_a_kwh": 4.16,
    "nennkapazitaet_e_kwh": 5.12,
    "nennkapazitaet_d_kwh": 5.12,
    "mindestreserve": 2.0,
    "prognose_sicherheit": 90.0,
    "unplanbare_reserve": 1.0,
    "ladewirkungsgrad": 90.0,
    "hysterese": 0.2,
    "schwacher_tag": 25.0,
    "mittlerer_tag": 50.0,
    "starker_tag": 85.0,
    "knappheitsreserve": 125.0,
    "min_effiziente_leistung": 800.0,
    "venus_a_packs": 2.0,
    "venus_d_packs": 2.0,
    "kalibrierung_a_freigegeben": False,
    "kalibrierung_e_freigegeben": False,
    "kalibrierung_d_freigegeben": False,
    "kalibrierung_a_laden_sperren": False,
    "kalibrierung_e_laden_sperren": False,
    "kalibrierung_d_laden_sperren": False,
    "kalibrierung_a_erfolg_bekannt": False,
    "kalibrierung_e_erfolg_bekannt": False,
    "kalibrierung_d_erfolg_bekannt": False,
    "kalibrierung_sitzung": "",
    "kalibrierung_vormerkungen": "",
    "sicherung": "",
    "kalibrierung_sicherung": "",
    "schreibfehler_a": 0,
    "schreibfehler_e": 0,
    "schreibfehler_d": 0,
    "laden_freigegeben": False,
    "lernspeicher": {"active": {}, "history": [], "models": {"A": {}, "D": {}, "E": {}}},
    "kalibrierung_a_letzter_erfolg": None,
    "kalibrierung_e_letzter_erfolg": None,
    "kalibrierung_d_letzter_erfolg": None,
    "kalibrierung_a_letzte_energie": 0.0,
    "kalibrierung_e_letzte_energie": 0.0,
    "kalibrierung_d_letzte_energie": 0.0,
    "kalibrierung_a_p1_letzte_drift": 0.0,
    "kalibrierung_a_p2_letzte_drift": 0.0,
    "kalibrierung_e_letzte_drift": 0.0,
    "kalibrierung_d_p1_letzte_drift": 0.0,
    "kalibrierung_d_p2_letzte_drift": 0.0,
    "migrated_from_legacy": False,
}


HELPER_TO_CONTROL: dict[str, str] = {
    "input_boolean.speicher_ladelogik_mittagsspitzen": "mittagsspitzen",
    "input_boolean.speicher_ladelogik_manuell_a_aktiv": "manuell_a_aktiv",
    "input_boolean.speicher_ladelogik_manuell_e_aktiv": "manuell_e_aktiv",
    "input_boolean.speicher_ladelogik_manuell_d_aktiv": "manuell_d_aktiv",
    "input_boolean.speicher_ladelogik_kalibrierung_a_freigegeben": "kalibrierung_a_freigegeben",
    "input_boolean.speicher_ladelogik_kalibrierung_e_freigegeben": "kalibrierung_e_freigegeben",
    "input_boolean.speicher_ladelogik_kalibrierung_d_freigegeben": "kalibrierung_d_freigegeben",
    "input_boolean.speicher_ladelogik_kalibrierung_a_laden_sperren": "kalibrierung_a_laden_sperren",
    "input_boolean.speicher_ladelogik_kalibrierung_e_laden_sperren": "kalibrierung_e_laden_sperren",
    "input_boolean.speicher_ladelogik_kalibrierung_d_laden_sperren": "kalibrierung_d_laden_sperren",
    "input_boolean.speicher_ladelogik_kalibrierung_a_erfolg_bekannt": "kalibrierung_a_erfolg_bekannt",
    "input_boolean.speicher_ladelogik_kalibrierung_e_erfolg_bekannt": "kalibrierung_e_erfolg_bekannt",
    "input_boolean.speicher_ladelogik_kalibrierung_d_erfolg_bekannt": "kalibrierung_d_erfolg_bekannt",
    "input_boolean.speicher_ladelogik_laden_freigegeben": "laden_freigegeben",
    "input_text.speicher_ladelogik_kalibrierung_sitzung": "kalibrierung_sitzung",
    "input_text.speicher_ladelogik_kalibrierung_vormerkungen": "kalibrierung_vormerkungen",
    "input_text.speicher_ladelogik_sicherung": "sicherung",
    "input_text.speicher_ladelogik_kalibrierung_sicherung": "kalibrierung_sicherung",
    "input_number.speicher_ladelogik_mindestreserve": "mindestreserve",
    "input_number.speicher_ladelogik_prognose_sicherheit": "prognose_sicherheit",
    "input_number.speicher_ladelogik_unplanbare_reserve": "unplanbare_reserve",
    "input_number.speicher_ladelogik_ladewirkungsgrad": "ladewirkungsgrad",
    "input_number.speicher_ladelogik_hysterese": "hysterese",
    "input_number.speicher_ladelogik_schwacher_tag": "schwacher_tag",
    "input_number.speicher_ladelogik_mittlerer_tag": "mittlerer_tag",
    "input_number.speicher_ladelogik_starker_tag": "starker_tag",
    "input_number.speicher_ladelogik_knappheitsreserve": "knappheitsreserve",
    "input_number.speicher_ladelogik_min_effiziente_leistung": "min_effiziente_leistung",
    "input_number.speicher_ladelogik_venus_a_packs": "venus_a_packs",
    "input_number.speicher_ladelogik_venus_d_packs": "venus_d_packs",
    "input_number.speicher_ladelogik_schreibfehler_a": "schreibfehler_a",
    "input_number.speicher_ladelogik_schreibfehler_e": "schreibfehler_e",
    "input_number.speicher_ladelogik_schreibfehler_d": "schreibfehler_d",
    "input_number.speicher_ladelogik_manuell_laden_a_w": "manuell_laden_a_w",
    "input_number.speicher_ladelogik_manuell_entladen_a_w": "manuell_entladen_a_w",
    "input_number.speicher_ladelogik_manuell_laden_e_w": "manuell_laden_e_w",
    "input_number.speicher_ladelogik_manuell_entladen_e_w": "manuell_entladen_e_w",
    "input_number.speicher_ladelogik_manuell_laden_d_w": "manuell_laden_d_w",
    "input_number.speicher_ladelogik_manuell_entladen_d_w": "manuell_entladen_d_w",
    "input_number.speicher_ladelogik_bevorzugte_ladeleistung_a_w": "bevorzugte_ladeleistung_a_w",
    "input_number.speicher_ladelogik_bevorzugte_ladeleistung_e_w": "bevorzugte_ladeleistung_e_w",
    "input_number.speicher_ladelogik_bevorzugte_ladeleistung_d_w": "bevorzugte_ladeleistung_d_w",
    "input_number.speicher_ladelogik_nennkapazitaet_a_kwh": "nennkapazitaet_a_kwh",
    "input_number.speicher_ladelogik_nennkapazitaet_e_kwh": "nennkapazitaet_e_kwh",
    "input_number.speicher_ladelogik_nennkapazitaet_d_kwh": "nennkapazitaet_d_kwh",
    "input_datetime.speicher_ladelogik_kalibrierung_a_letzter_erfolg": "kalibrierung_a_letzter_erfolg",
    "input_datetime.speicher_ladelogik_kalibrierung_e_letzter_erfolg": "kalibrierung_e_letzter_erfolg",
    "input_datetime.speicher_ladelogik_kalibrierung_d_letzter_erfolg": "kalibrierung_d_letzter_erfolg",
    "input_number.speicher_ladelogik_kalibrierung_a_letzte_energie": "kalibrierung_a_letzte_energie",
    "input_number.speicher_ladelogik_kalibrierung_e_letzte_energie": "kalibrierung_e_letzte_energie",
    "input_number.speicher_ladelogik_kalibrierung_d_letzte_energie": "kalibrierung_d_letzte_energie",
    "input_number.speicher_ladelogik_kalibrierung_a_p1_letzte_drift": "kalibrierung_a_p1_letzte_drift",
    "input_number.speicher_ladelogik_kalibrierung_a_p2_letzte_drift": "kalibrierung_a_p2_letzte_drift",
    "input_number.speicher_ladelogik_kalibrierung_e_letzte_drift": "kalibrierung_e_letzte_drift",
    "input_number.speicher_ladelogik_kalibrierung_d_p1_letzte_drift": "kalibrierung_d_p1_letzte_drift",
    "input_number.speicher_ladelogik_kalibrierung_d_p2_letzte_drift": "kalibrierung_d_p2_letzte_drift",
}


@dataclass(slots=True)
class PlannerState:
    """Small State-compatible object used for internal planner values."""

    state: str
    attributes: dict[str, Any] = field(default_factory=dict)
    last_reported: datetime = field(default_factory=dt_util.utcnow)
    last_updated: datetime = field(default_factory=dt_util.utcnow)


def _on_off(value: Any) -> str:
    return "on" if bool(value) else "off"


def planner_states(control: dict[str, Any]) -> dict[str, PlannerState]:
    """Expose native controls to the proven planner without HA input helpers."""
    mode = str(control.get("mode", "Beobachten"))
    # Beobachten calculates the complete automatic plan but never writes it.
    planner_mode = "Automatik" if mode in {"Beobachten", "Automatik"} else "Aus"
    result: dict[str, PlannerState] = {
        "input_select.speicher_ladelogik_betriebsart": PlannerState(planner_mode),
        "input_boolean.speicher_ladelogik_aktiv": PlannerState(
            _on_off(mode != "Aus")
        ),
        "input_boolean.speicher_ladelogik_v1_beta_1_initialisiert": PlannerState(
            "on"
        ),
        "input_number.speicher_ladelogik_schreibfehler": PlannerState(
            str(max(int(control.get("schreibfehler_a", 0)), int(control.get("schreibfehler_d", 0)), int(control.get("schreibfehler_e", 0))))
        ),
        "sensor.speicher_ladelogik_lernspeicher": PlannerState(
            "bereit", dict(control.get("lernspeicher", {}))
        ),
        "input_number.venus_a_verfugbare_kapazitat": PlannerState(
            str(float(control.get("nennkapazitaet_a_kwh", 4.16)) * 0.88)
        ),
        "input_number.venus_e_verfugbare_kapazitat": PlannerState(
            str(float(control.get("nennkapazitaet_e_kwh", 5.12)) * 0.88)
        ),
        "input_number.venus_d_verfugbare_kapazitat": PlannerState(
            str(float(control.get("nennkapazitaet_d_kwh", 5.12)) * 0.88)
        ),
    }
    for entity_id, key in HELPER_TO_CONTROL.items():
        value = control.get(key, CONTROL_DEFAULTS.get(key))
        if entity_id.startswith("input_boolean."):
            state = _on_off(value)
        elif value is None:
            state = "unknown"
        else:
            state = str(value)
        result[entity_id] = PlannerState(state)
    return result
