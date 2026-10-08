"""Planner ported from the proven V1 Beta calculation script."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import persistence
from .charge_plan import daily_plan
from .telemetry import ac_feedback
from .const import VERSION as INTEGRATION_VERSION
from .stability import (
    calibration_required_seconds,
    forecast_day_factor,
    forecast_factor,
    peer_discharge_release,
    peer_grid_support,
    stable_day_class,
    target_latch,
)
from .storage import (
    MODEL_REFERENCE_AC_KWH,
    MODEL_REFERENCE_AC_PER_MODULE_KWH,
)


def calculate_plan(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Calculate a plan without performing Home Assistant service calls."""
    # Pure planner; hardware/BMS limits remain authoritative.

    output = {}

    VERSION = INTEGRATION_VERSION
    NOW = float(data.get("now", time.time()))
    DAY0 = float(data.get("day0", 0))
    DAY1 = float(data.get("day1", 0))
    DAY2 = float(data.get("day2", 0))
    NINE = float(data.get("nine", 0))
    ELEVEN = float(data.get("eleven", 0))
    DEADLINE = float(data.get("deadline", 0))
    SOLAR_NOON = float(data.get("solar_noon", 0))
    MIDDAY_START = float(data.get("midday_start", NINE))
    MIDDAY_END = float(data.get("midday_end", DEADLINE))
    REQUEST = str(data.get("request", "tick"))
    BATTERY_KEYS = [
        key for key in data.get("battery_keys", ["A", "E"])
        if key in {"A", "E"}
    ] or ["A", "E"]
    MANUAL_ENABLED = {
        "A": "input_boolean.speicher_ladelogik_ae_manuell_a_aktiv",
        "E": "input_boolean.speicher_ladelogik_ae_manuell_e_aktiv",
    }
    MANUAL_CHARGE = {
        "A": "input_number.speicher_ladelogik_ae_manuell_laden_a_w",
        "E": "input_number.speicher_ladelogik_ae_manuell_laden_e_w",
    }
    MANUAL_DISCHARGE = {
        "A": "input_number.speicher_ladelogik_ae_manuell_entladen_a_w",
        "E": "input_number.speicher_ladelogik_ae_manuell_entladen_e_w",
    }

    # Physical A and E have one planner slot each.
    SLOT_ENTITIES = {
        "A": {
            "soc": "sensor.marstek_venus_a_soc_batterie",
            "power": "sensor.marstek_venus_a_ac_leistung",
            "inverter": "sensor.marstek_venus_a_wechselrichter_status",
            "charge": "number.marstek_venus_a_maximale_ladeleistung",
            "discharge": "number.marstek_venus_a_maximale_entladeleistung",
            "auto": "switch.astrameter_venus_a_auto_target",
            "active": "switch.astrameter_venus_a_active",
            "override": "input_boolean.venus_a_nicht_laden",
            "top": "number.marstek_venus_a_maximaler_soc",
            "bottom": "number.marstek_venus_a_minimaler_soc",
            "vmax": "sensor.marstek_venus_a_maximale_zellenspannung",
            "tmax": "sensor.marstek_venus_a_maximale_zellentemperatur",
            "tmin": "sensor.marstek_venus_a_minimale_zellentemperatur",
            "usable": "input_number.venus_a_verfugbare_kapazitat",
        },
        "E": {
            "soc": "sensor.marstek_venus_e_soc",
            "power": "sensor.marstek_venus_e_ac_leistung",
            "inverter": "sensor.marstek_venus_e_wechselrichter_status",
            "charge": "number.marstek_venus_e_ladeleistung",
            "discharge": "number.marstek_venus_e_entladeleistung",
            "auto": "switch.astrameter_venus_e_auto_target",
            "active": "switch.astrameter_venus_e_active",
            "override": "input_boolean.venus_e_nicht_laden",
            "top": "number.marstek_venus_e_obere_ladegrenze_kapazitat",
            "bottom": "number.marstek_venus_e_untere_ladegrenze_kapazitat",
            "vmax": "sensor.marstek_venus_e_max_zellspannung",
            "tmax": "sensor.marstek_venus_e_max_zelltemperatur",
            "tmin": "sensor.marstek_venus_e_min_zelltemperatur",
            "usable": "input_number.venus_e_verfugbare_kapazitat",
        },
    }
    MODEL_SPECS = {
        # AC reference values include conversion losses.
        "A": {
            "charge_sign": -1, "usable_default": 3.6608, "floor": 12,
            "maximum": 1500, "tail": 500,
            "reference_ac_per_module": MODEL_REFERENCE_AC_PER_MODULE_KWH["A"],
            "preferred": 1100, "has_packs": True, "module_kwh": 2.08,
        },
        "E": {
            "charge_sign": -1, "usable_default": 4.5568, "floor": 11,
            "maximum": 2500, "tail": 1100,
            "reference_ac": MODEL_REFERENCE_AC_KWH["E"],
            "preferred": 1300, "has_packs": False, "module_kwh": None,
        },
    }
    SLOT_MODELS = {
        key: str(data.get("slot_models", {}).get(key, key))
        for key in ("A", "E")
    }
    SLOT_NAMES = {
        key: str(
            data.get("slot_names", {}).get(key, f"Venus {SLOT_MODELS[key]}")
        )
        for key in ("A", "E")
    }
    BATTERIES = {
        key: {**SLOT_ENTITIES[key], **MODEL_SPECS[SLOT_MODELS[key]], "model": SLOT_MODELS[key]}
        for key in ("A", "E")
    }

    PACKS = {
        "A": [
            "sensor.marstek_venus_a_soc_batteriepack_1",
            "sensor.marstek_venus_a_soc_batteriepack_2",
        ],
        "E": [],
    }
    DRIFTS = {
        "A": ["sensor.venus_a_pack_1_zelldrift", "sensor.venus_a_pack_2_zelldrift"],
        "E": ["sensor.marstek_venus_e_zellspannungs_differenz"],
    }
    for key, entities in data.get("pack_entities", {}).items():
        if key in PACKS and isinstance(entities, list) and entities:
            PACKS[key] = [entity for entity in entities if isinstance(entity, str)]
    for key, entities in data.get("drift_entities", {}).items():
        if key in DRIFTS and isinstance(entities, list) and entities:
            DRIFTS[key] = [entity for entity in entities if isinstance(entity, str)]
    GRID = "sensor.stromzahler_leistung"  # positive import; negative export
    PV = "sensor.aktuelle_pv_leistung"
    MPPTS = ["sensor.sg10rt_mppt1_leistung", "sensor.sg10rt_mppt2_leistung",
             "sensor.sg12rt_mppt1_leistung", "sensor.sg12rt_mppt2_leistung"]
    LEARNING_ID = "sensor.speicher_ladelogik_ae_lernspeicher"
    SUN = "sun.sun"
    LOAD = "sensor.hausleistung_gesamt_30_min"
    LIVE_LOAD = "sensor.hausleistung_gesamt"
    DAILY = "sensor.pv_produktion_tag"
    SESSION_ID = "input_text.speicher_ladelogik_ae_kalibrierung_sitzung"
    BACKUP_ID = "input_text.speicher_ladelogik_ae_sicherung"
    CAL_BACKUP_ID = "input_text.speicher_ladelogik_ae_kalibrierung_sicherung"
    QUEUE_ID = "input_text.speicher_ladelogik_ae_kalibrierung_vormerkungen"
    REST_TIMEOUT_GRACE_SECONDS = 30 * 60
    ACTIVE_PHASES = [
        "requested",
        "drain",
        "empty_rest",
        "wait",
        "charge",
        "rest",
        "full_rest",
        "paused",
        "restore",
    ]
    PHASE_LABELS = {
        "requested": "Auftrag vorgemerkt",
        "drain": "Entladen auf 14 %",
        "empty_rest": "Untere Ruhephase",
        "wait": "Wartet auf 600 W Einspeisung",
        "charge": "Kalibrierladung",
        "rest": "Obere Ruhephase",
        "full_rest": "Obere Ruhephase",
        "paused": "Pausiert – Auftrag bleibt erhalten",
        "restore": "Grenzwerte wiederherstellen",
    }



    def raw(entity):
        state = hass.states.get(entity)
        return state.state if state is not None else "unavailable"


    def number(value, default=None):
        try:
            result = float(value)
            if result != result or abs(result) > 1000000000000:
                return default
            return result
        except (ValueError, TypeError):
            return default


    def flag(value):
        return value is True or str(value).lower() in ["true", "on", "1"]


    def setting(name, default, lower, upper):
        value = number(raw("input_number.speicher_ladelogik_ae_" + name), default)
        return max(lower, min(upper, value))


    def charging_power(key, power):
        if power is None:
            return None
        return max(0, power * BATTERIES[key]["charge_sign"])


    def measurement(entity, kind, age=None):
        state = hass.states.get(entity)
        if state is None:
            return None
        value = number(state.state)
        if value is None:
            return None
        unit = str(state.attributes.get("unit_of_measurement", "")).lower()
        units = {"power": {"w": 1, "kw": 1000},
                 "energy": {"wh": 0.001, "kwh": 1, "mwh": 1000},
                 "soc": {"%": 1}, "voltage": {"v": 1, "mv": 0.001},
                 "temperature": {"°c": 1}, "delta": {"mv": 1, "v": 1000}}
        if kind in units:
            if unit not in units[kind]:
                return None
            value = value * units[kind][unit]
        if age is not None:
            stamp = dt_util.as_timestamp(state.last_reported)
            if NOW - stamp > age or stamp > NOW + 10:
                return None
        if kind == "soc" and not 0 <= value <= 100:
            return None
        return value


    def reported_timestamp(entity):
        state = hass.states.get(entity)
        if state is None:
            return None
        try:
            stamp = dt_util.as_timestamp(state.last_reported)
            return stamp if stamp <= NOW + 10 else None
        except (ValueError, TypeError, AttributeError):
            return None


    def writable(entity, value):
        state = hass.states.get(entity)
        if state is None or number(state.state) is None:
            return False
        lo = number(state.attributes.get("min"))
        hi = number(state.attributes.get("max"))
        step = number(state.attributes.get("step"))
        return (lo is not None and hi is not None and step is not None and step > 0
                and lo <= value <= hi and abs((value - lo) / step - round((value - lo) / step)) < 0.001)


    def source_description(entity):
        state = hass.states.get(entity)
        source = getattr(state, "entity_id", None) or entity
        value = raw(entity)
        return f"{source}: {value}"


    def soc_error(entity, label):
        state = hass.states.get(entity)
        value = number(raw(entity))
        if value is None:
            detail = "kein numerischer Wert"
        elif not 0 <= value <= 100:
            detail = "Wert außerhalb 0–100 %"
        else:
            unit = state.attributes.get("unit_of_measurement", "") if state else ""
            detail = f"Einheit {unit!r}; erwartet '%'"
        return f"{label} ungültig ({source_description(entity)}; {detail})"


    def charge_limit_error(entity, maximum):
        state = hass.states.get(entity)
        if state is None or number(state.state) is None:
            return f"Ladegrenze nicht verfügbar ({source_description(entity)}; numerischen Zustand erwartet)"
        attrs = state.attributes
        lo, hi, step = (number(attrs.get(key)) for key in ("min", "max", "step"))
        if lo is None or hi is None or step is None or step <= 0:
            return (f"Ladegrenze: Stellbereich ungültig ({source_description(entity)}; "
                    f"min={attrs.get('min')}, max={attrs.get('max')}, step={attrs.get('step')})")
        targets = ", ".join(f"{value:g} W" for value in (0, maximum) if not writable(entity, value))
        return (f"Ladegrenze: {targets} nicht einstellbar ({source_description(entity)}; "
                f"Bereich {lo:g}–{hi:g} W, Schritt {step:g} W)")


    def write_needed(current, target):
        return current is None or abs(current - target) >= 25


    def rounded_limit(value, maximum):
        return int(max(0, min(maximum, round(value / 50) * 50)))


    def advertised_maximum(entity, fallback):
        state = hass.states.get(entity)
        if state is None:
            return fallback
        return max(0, number(state.attributes.get("max"), fallback))


    def energy(nominal, floor, soc, goal):
        return {"stored": nominal * max(0, soc - floor) / 100,
                "target": nominal * max(0, goal - floor) / 100,
                "need": nominal * max(0, goal - soc) / 100}


    def forecast(suffix, start, end):
        errors = []
        maps = []
        expected = int(round((end - start) / 900))
        if expected not in [92, 96, 100]:
            return {"ok": False, "rows": [], "errors": ["Ungültige Tagesgrenzen"]}
        for direction in ["sw", "so", "no"]:
            entity = "sensor." + direction + "_energy_production_" + suffix
            state = hass.states.get(entity)
            readings = state.attributes.get("wh_period_15m") if state is not None else None
            parsed = {}
            try:
                entries = readings.items()
            except (AttributeError, TypeError):
                entries = None
            if entries is None or measurement(entity, "energy", 43200) is None:
                errors.append(entity + ": keine aktuellen wh_period_15m")
            else:
                for key, entry_value in entries:
                    try:
                        instant = dt_util.parse_datetime(str(key))
                        if instant is None or instant.tzinfo is None:
                            raise ValueError("Zeitzone fehlt")
                        stamp = dt_util.as_timestamp(instant)
                        value = number(entry_value)
                        if start <= stamp < end:
                            index = int(round((stamp - start) / 900))
                            if abs(stamp - (start + index * 900)) > 1 or index in parsed or value is None or value < 0:
                                errors.append(entity + ": ungültiges Intervall")
                            else:
                                parsed[index] = value
                    except (ValueError, TypeError, AttributeError):
                        errors.append(entity + ": Zeitstempel ungültig")
                if len(parsed) != expected:
                    errors.append(entity + ": Intervallücke/falsches Datum")
            maps.append(parsed)
        rows = []
        if not errors:
            for index in range(expected):
                wh = sum([part[index] for part in maps])
                rows.append({"t": start + index * 900, "wh": wh})
            if sum([row["wh"] for row in rows]) > 300000:
                errors.append("Tagesprognose > 300 kWh")
        return {"ok": not errors, "rows": rows if not errors else [], "errors": errors}




    def continuous_window(rows, after, required_hours, load, factor):
        # The forecast itself is provided in 15-minute buckets, but the
        # measured energy requirement is exact. Rounding 7.54 h up to 7.75 h
        # blocked an otherwise sufficient Venus-A window by only a few
        # minutes. Keep the display rounded, never the hard start gate.
        required = calibration_required_seconds(required_hours)
        beginning = None
        longest = 0
        match = None
        previous_end = None
        for row in rows:
            start = max(after, row["t"])
            end = row["t"] + 900
            if end <= after:
                continue
            adequate = row["wh"] * 4 * factor - load >= calibration_power + 100
            if adequate:
                if beginning is None or previous_end is None or abs(row["t"] - previous_end) > 1:
                    beginning = start
                longest = max(longest, end - beginning)
                if match is None and end - beginning >= required:
                    match = {"start": beginning, "end": beginning + required}
            else:
                beginning = None
            previous_end = end
        return {"ok": match is not None, "start": match["start"] if match else None,
                "end": match["end"] if match else None,
                "longest_h": round(longest / 3600, 2),
                "required_h": round(required / 3600, 2)}


    read_session = persistence.read_session
    encode_session = persistence.encode_session
    read_backup = persistence.read_backup
    encode_backup = persistence.encode_backup
    read_queue = persistence.read_queue
    encode_queue = persistence.encode_queue


    def cap_snapshot():
        return {
            **{key: number(raw(BATTERIES[key]["charge"])) for key in BATTERY_KEYS},
            **{"D" + key: number(raw(BATTERIES[key]["discharge"])) for key in BATTERY_KEYS},
        }


    def backup_restored(saved, current):
        return saved is not None and all([saved[key] == -1 or (current[key] is not None
            and abs(current[key] - saved[key]) < 25) for key in saved])


    def transition(session, phase, reason):
        session["p"] = phase
        session["t"] = int(NOW)
        session["l"] = 0
        session["f"] = 0
        session["r"] = reason


    def pause_session(session, reason):
        session["u"] = session["p"]
        lower_rest_start = (session["t"] if session["p"] == "empty_rest" else
                            session["l"] if session["p"] == "wait" else 0)
        if session["p"] == "charge":
            session["i"] = 1
        transition(session, "paused", reason)
        # Keep the start for a short, verifiably idle telemetry interruption.
        # The existing numeric field is only used for grid support in drain.
        if lower_rest_start:
            session["l"] = lower_rest_start


    def start_calibration_charge(session, preview, lower_rest_start, result):
        transition(session, "charge", "charging")
        result["lower_rest_s"] = max(0, int(NOW - lower_rest_start)) if lower_rest_start else 0
        session["s"] = int(NOW)
        session["x"] = int(preview["end"] or 0)
        session["q"] = int(NOW)
        session["v"] = session["w"] = session["h"] = session["i"] = 0


    def calibration_step(session, context):
        s = session.copy()
        p = s["p"]
        # Compatibility for sessions written by v1.1.0 while an upper rest
        # check was active.
        if p == "rest":
            p = "full_rest"
            s["p"] = p
        result = {"session": s, "charge": {}, "discharge": {}, "finish": False,
                  "notify": "", "release": False, "retry": False,
                  "peer_grid_release": False, "peer_grid_reason": ""}
        if p not in ACTIVE_PHASES:
            return result
        key = s["b"]
        peers = [candidate for candidate in BATTERY_KEYS if candidate != key]
        request = context["request"]
        # The configured grid meter is positive for import and negative for
        # export. A fresh 600 W export is the only PV start gate.
        export_ready = (context.get("grid_power") is not None
                        and context["grid_power"] <= -600)
        if key not in BATTERY_KEYS:
            transition(s, "error", "state_corrupt")
        elif p != "restore" and (request == "cancel" or not context["automatic"] or not context["armed"][key]):
            transition(s, "restore", "cancelled")
        elif p != "restore" and BATTERIES[key]["has_packs"] and s["z"] != context["pack_count"]:
            transition(s, "restore", "pack_changed")
        elif p not in ["requested", "restore"] and request == "start":
            transition(s, "restore", "restart")
        elif p not in ["requested", "restore"] and context["backup"] is None:
            transition(s, "error", "backup_missing")
        elif p == "restore":
            if context["backup"] is None and s["s"] != 0:
                transition(s, "error", "backup_missing")
        elif p != "requested" and context.get("critical", {}).get(key, False):
            transition(s, "restore", "device_limit")
        elif p != "requested" and not context["safe"][key]:
            if p != "paused":
                pause_session(s, "data_pause")
        elif p == "paused":
            resume = s["u"] or "requested"
            if resume in ACTIVE_PHASES:
                lower_rest_start = s["l"] if resume in {"empty_rest", "wait"} else 0
                pause_started = s["t"]
                transition(s, resume, "resumed")
                if lower_rest_start and 0 <= NOW - pause_started <= 90:
                    bat = context["batteries"][key]
                    reported = bat.get("power_reported_ts")
                    if (bat["power"] is not None and abs(bat["power"]) <= 50
                            and reported is not None and reported >= NOW - 30
                            and bat["soc"] is not None and bat["soc"] <= 15):
                        if resume == "empty_rest":
                            s["t"] = lower_rest_start
                        else:
                            s["l"] = lower_rest_start
                if resume == "wait" and not s["l"] and lower_rest_start:
                    s["l"] = int(NOW)
                s["u"] = ""
                s["q"] = int(NOW)
                s["v"] = 0
        elif p == "requested":
            bat = context["batteries"][key]
            use_today = s["n"] <= DAY0
            preview = context["today"][key] if use_today else context["tomorrow"][key]
            if preview["ok"] and preview["start"] >= s["n"]:
                s["s"] = int(preview["start"])
                s["x"] = int(preview["end"])
            else:
                s["s"] = 0
                s["x"] = 0
            if not context["safe"][key]:
                s["r"] = "waiting_data"
            elif bat["cal_empty_ready"] and use_today and export_ready:
                start_calibration_charge(s, preview, 0, result)
            elif bat["cal_empty_ready"]:
                transition(s, "empty_rest", "empty_resting")
            else:
                # Der Tastendruck ist die ausdrückliche Benutzerfreigabe für
                # die Vorbereitung. Uhrzeit, momentane PV-Leistung und ein
                # bereits sicher prognostiziertes Ladefenster verzögern das
                # Entladen daher nicht.
                transition(s, "drain", "natural_discharge")
                if not preview["ok"]:
                    s["r"] = "no_window"
        elif p == "drain":
            preview = (
                context["today"][key]
                if s["n"] <= DAY0
                else context["tomorrow"][key]
            )
            if preview["ok"] and preview["start"] >= s["n"]:
                s["s"] = int(preview["start"])
                s["x"] = int(preview["end"])
            else:
                s["s"] = 0
                s["x"] = 0
            released, _release_reason = peer_discharge_release(
                phase=p,
                target_soc=context["batteries"][key]["soc"],
                highest_pack_soc=context["batteries"][key]["highest_soc"],
                prior_released=bool(s["h"]),
            )
            if released:
                # During drain, h is a one-way peer-release latch. It is reset
                # before the later charge-confirmation use of the same field.
                s["h"] = 1
            if context["batteries"][key]["cal_empty_ready"]:
                transition(s, "empty_rest", "empty_resting")
            # A short forecast does not discard a prepared calibration.
        elif p == "empty_rest":
            bat = context["batteries"][key]
            # A resting BMS can report a one-percent SoC rebound. Once the
            # lower rest has begun, only a material rise invalidates it.
            still_empty = (bat["cal_empty_ready"] or
                           (bat["soc"] is not None and bat["soc"] <= 15 and
                            bat["highest_soc"] is not None and bat["highest_soc"] <= 15.5))
            if not still_empty:
                transition(s, "drain", "natural_discharge")
            else:
                preview = (
                    context["today"][key]
                    if s["n"] <= DAY0
                    else context["tomorrow"][key]
                )
                if s["n"] <= DAY0 and export_ready:
                    start_calibration_charge(s, preview, s["t"], result)
                elif s["n"] <= DAY0:
                    lower_rest_start = s["t"]
                    transition(s, "wait", "waiting_pv")
                    s["l"] = lower_rest_start
                    s["s"] = s["x"] = 0
        elif p == "wait":
            preview = (
                context["today"][key]
                if s["n"] <= DAY0
                else context["tomorrow"][key]
            )
            if s["n"] <= DAY0 and export_ready:
                bat = context["batteries"][key]
                still_empty = (bat["cal_empty_ready"] or
                               (s["l"] > 0 and bat["soc"] is not None and bat["soc"] <= 15 and
                                bat["highest_soc"] is not None and bat["highest_soc"] <= 15.5))
                if still_empty:
                    start_calibration_charge(s, preview, s["l"], result)
                else:
                    transition(s, "restore", "retry_empty")
        elif p == "charge":
            bat = context["batteries"][key]
            power = charging_power(key, bat["power"])
            report_after_start = (bat["power_reported_ts"] is not None
                                  and bat["power_reported_ts"] >= s["t"] - 1)
            if not s["h"] and report_after_start and power is not None and power >= calibration_min_power:
                s["h"] = 1
            if not s["h"] and NOW - s["t"] >= 180:
                pause_session(s, "telemetry_no_response")
            if s["p"] == "charge" and power is not None:
                elapsed = NOW - s["q"]
                if 0 < elapsed <= 90:
                    s["w"] = round(s["w"] + (s["v"] + power) / 2 * elapsed / 3600, 2)
                elif s["q"] and elapsed > 90:
                    pause_session(s, "sample_gap")
                s["q"] = int(NOW)
                s["v"] = power
            if s["p"] == "charge":
                if bat["all_full"] and s["h"]:
                    s["f"] = s["f"] or int(NOW)
                    if NOW - s["f"] >= 60:
                        transition(s, "full_rest", "full_resting")
                else:
                    s["f"] = 0
                if s["p"] == "charge":
                    if s["h"] and power is not None and power <= 400 and not bat["all_full"]:
                        s["l"] = s["l"] or int(NOW)
                    else:
                        s["l"] = 0
                if s["p"] == "charge" and NOW - s["t"] > 64800:
                    transition(s, "restore", "charge_timeout")
        elif p == "full_rest":
            bat = context["batteries"][key]
            report_after_rest = (bat["power_reported_ts"] is not None
                                 and bat["power_reported_ts"] >= s["t"] - 1)
            if bat["lowest_soc"] < 98 or bat["soc"] < 98:
                transition(s, "restore", "full_unconfirmed")
            elif report_after_rest and bat["power"] is not None and abs(bat["power"]) <= 50:
                s["f"] = s["f"] or int(NOW)
                if NOW - s["f"] >= FULL_REST_SECONDS:
                    transition(s, "restore", "interrupted_full" if s["i"] else "success")
            else:
                s["f"] = 0
            if (s["p"] == "full_rest"
                    and NOW - s["t"] > FULL_REST_SECONDS + REST_TIMEOUT_GRACE_SECONDS):
                transition(s, "restore", "rest_timeout")
        if s["p"] == "restore":
            result["release"] = True
            if p == "requested" and context["backup"] is None:
                s["s"] = 0
                s["x"] = 0
            if context["restored"] or (p == "requested" and context["backup"] is None):
                result["finish"] = s["r"] == "success"
                result["retry"] = s["r"] in ["retry_empty", "retry_window", "charge_timeout", "restart", "interrupted_full"]
                phase = "done" if result["finish"] else ("incomplete" if result["retry"] else "cancelled")
                transition(s, phase, s["r"])
                result["notify"] = "Kalibrierung " + SLOT_NAMES[key] + ": " + s["r"]
        elif s["p"] == "drain":
            temporary_release, import_since, clear_since, grid_reason = peer_grid_support(
                phase=s["p"],
                now_ts=NOW,
                grid_power_w=context.get("grid_power"),
                permanent_release=bool(s["h"]),
                temporary_release=bool(s["v"]),
                import_since_ts=number(s["l"]),
                clear_since_ts=number(s["f"]),
            )
            s["v"] = 1 if temporary_release else 0
            s["l"] = import_since or 0
            s["f"] = clear_since or 0
            result["peer_grid_reason"] = grid_reason
            result["peer_grid_release"] = temporary_release
            result["charge"][key] = 0
            if context["backup"] is not None and context["backup"]["D" + key] >= 0:
                result["discharge"][key] = context["backup"]["D" + key]
            for other in peers:
                if context["batteries"][other]["owns"] and context.get("peer_drain_ok", {}).get(other, False):
                    result["discharge"][other] = (
                        context.get("peer_discharge_max", {}).get(
                            other, BATTERIES[other]["maximum"]
                        )
                        if s["h"] or temporary_release
                        else 0
                    )
        elif s["p"] == "wait":
            result["charge"][key] = 0
            # Nach der unteren Ruhephase bis zum Ladebeginn ruhig halten.
            result["discharge"][key] = 0
        elif s["p"] in ["empty_rest", "full_rest", "paused"]:
            result["charge"][key] = 0
            result["discharge"][key] = 0
        elif s["p"] == "charge":
            result["charge"][key] = calibration_power
            result["discharge"][key] = 0
        return result


    def read_learning():
        state = hass.states.get(LEARNING_ID)
        saved = state.attributes if state is not None else {}
        result = {"active": {}, "active_runs": {}, "history": [],
                  "last_precharge_rest": {}, "models": {key: {} for key in BATTERY_KEYS}}
        try:
            active = saved.get("active", {})
            if active.get("battery") in BATTERY_KEYS and 0 < number(active.get("start"), 0) <= NOW:
                result["active"] = active.copy()
                result["active_runs"][active["battery"]] = active.copy()
            for key, run in saved.get("active_runs", {}).items():
                if (key in BATTERY_KEYS and isinstance(run, dict)
                        and run.get("battery") == key and 0 < number(run.get("start"), 0) <= NOW):
                    result["active_runs"][key] = run.copy()
            for record in saved.get("history", [])[-20:]:
                if record.get("battery") in BATTERY_KEYS and number(record.get("end")) is not None:
                    result["history"].append(record.copy())
            for key in BATTERY_KEYS:
                rest = saved.get("last_precharge_rest", {}).get(key, {})
                seconds = number(rest.get("seconds"))
                stamp = number(rest.get("timestamp"))
                if (seconds is not None and 0 <= seconds <= 7 * 86400
                        and stamp is not None and 0 < stamp <= NOW):
                    result["last_precharge_rest"][key] = {"seconds": seconds, "timestamp": stamp}
                model = saved.get("models", {}).get(key, {})
                if (0 < number(model.get("count"), 0) <= 10000 and 0 < number(model.get("ac_kwh"), 0) <= 30
                        and 0 < number(model.get("usable_reference"), 0) < 20):
                    result["models"][key] = model.copy()
        except (AttributeError, TypeError):
            return {"active": {}, "active_runs": {}, "history": [],
                    "last_precharge_rest": {}, "models": {key: {} for key in BATTERY_KEYS}}
        return result


    EMPTY_REST_SECONDS = setting("kalibrierung_ruhe_unten_min", 90, 0, 240) * 60
    FULL_REST_SECONDS = setting("kalibrierung_ruhe_oben_min", 90, 0, 240) * 60
    learning = read_learning()
    eta = setting("ladewirkungsgrad", 90, 50, 100) / 100
    safety = setting("prognose_sicherheit", 90, 50, 100) / 100
    extra = setting("unplanbare_reserve", 1, 0, 20)
    weak = setting("schwacher_tag", 25, 0, 200)
    middle = max(weak, setting("mittlerer_tag", 50, 0, 200))
    strong = max(middle, setting("starker_tag", 85, 0, 200))
    pack_counts = {
        key: int(setting("venus_" + key.lower() + "_packs", 2, 1, 6))
        for key in BATTERY_KEYS if BATTERIES[key]["has_packs"]
    }
    mode = raw("input_select.speicher_ladelogik_ae_betriebsart")
    automatic = mode == "Automatik" and raw("input_boolean.speicher_ladelogik_ae_aktiv") == "on"

    supplied_prior_plan = data.get("prior_plan")
    prior_plan_state = hass.states.get("sensor.speicher_ladelogik_ae_planung")
    if isinstance(supplied_prior_plan, dict):
        prior_attributes = supplied_prior_plan
    elif prior_plan_state is not None:
        prior_attributes = prior_plan_state.attributes
    else:
        prior_attributes = {}

    # Manuelle Grenzen bleiben je Speicher aktiv, bis der Benutzer sie ausschaltet.
    # Es wird keine Leistung erzwungen; AstraMeter entscheidet weiterhin die Richtung.
    manual_requested = {key: raw(MANUAL_ENABLED[key]) == "on" for key in BATTERY_KEYS}
    manual_active_by_key = {key: manual_requested[key] and automatic for key in BATTERY_KEYS}
    manual_active = any(manual_active_by_key.values())
    for key in BATTERY_KEYS:
        cfg = BATTERIES[key]
        cfg["device_maximum"] = advertised_maximum(cfg["charge"], cfg["maximum"])
        cfg["device_discharge_maximum"] = advertised_maximum(
            cfg["discharge"], cfg["device_maximum"]
        )
        cfg["maximum"] = rounded_limit(
            setting(
                "maximale_ladeleistung_" + key.lower() + "_w",
                cfg["device_maximum"],
                0,
                cfg["device_maximum"],
            ),
            cfg["device_maximum"],
        )
        cfg["discharge_maximum"] = rounded_limit(
            setting(
                "maximale_entladeleistung_" + key.lower() + "_w",
                cfg["device_discharge_maximum"],
                0,
                cfg["device_discharge_maximum"],
            ),
            cfg["device_discharge_maximum"],
        )
        cfg["preferred"] = rounded_limit(
            setting(
                "bevorzugte_ladeleistung_" + key.lower() + "_w",
                cfg["preferred"],
                0,
                cfg["maximum"],
            ),
            cfg["maximum"],
        )
    calibration_power = rounded_limit(
        setting("kalibrierleistung_w", 500, 400, 1500),
        1500,
    )
    calibration_min_power = max(300, calibration_power * 0.8)
    manual_charge = {key: rounded_limit(number(raw(MANUAL_CHARGE[key]), 0),
                                        BATTERIES[key]["device_maximum"]) for key in BATTERY_KEYS}
    manual_discharge = {key: rounded_limit(number(raw(MANUAL_DISCHARGE[key]), 0),
                                           BATTERIES[key]["device_discharge_maximum"]) for key in BATTERY_KEYS}
    failure_counts = {}
    for key in BATTERY_KEYS:
        failure_counts[key] = number(raw("input_number.speicher_ladelogik_ae_schreibfehler_" + key.lower()),
                                     number(raw("input_number.speicher_ladelogik_ae_schreibfehler"), 0))
        if REQUEST == "ack":
            failure_counts[key] = 0
    failure_count = max(failure_counts.values())
    pv_fresh = measurement(PV, "power", 960)
    pv_without_age_limit = measurement(PV, "power")
    pv_held_zero = pv_fresh is None and pv_without_age_limit == 0
    pv_measured = 0 if pv_held_zero else pv_fresh
    sun_below_horizon = raw(SUN) == "below_horizon"

    pv_night_fallback = pv_measured is None and sun_below_horizon
    pv = 0 if pv_night_fallback else pv_measured
    grid = measurement(GRID, "power", 180)
    load_raw = measurement(LOAD, "power", 3600)
    live_load = measurement(LIVE_LOAD, "power", 180)
    load = max(350, load_raw) if load_raw is not None else 1000
    actual_today = measurement(DAILY, "energy")
    daily_ok = actual_today is not None and 0 <= actual_today <= 300
    errors = []
    warnings = []
    bats = {}
    for key in BATTERY_KEYS:
        cfg = BATTERIES[key]
        soc = measurement(cfg["soc"], "soc")
        power_fresh = measurement(cfg["power"], "power", 90)
        power_usable = measurement(cfg["power"], "power", 180)
        power_latest = measurement(cfg["power"], "power")
        power_reported_ts = reported_timestamp(cfg["power"])
        power_age_min = max(0, (NOW - power_reported_ts) / 60) if power_reported_ts is not None else None
        inverter_status = raw(cfg["inverter"])
        inverter_ts = reported_timestamp(cfg["inverter"])
        inverter_fresh = (inverter_status in ("Charge", "Discharge", "Standby")
                          and inverter_ts is not None and NOW - inverter_ts <= 90)
        # Ein unveraenderter numerischer Wert bleibt verwendbar. "Frisch" ist
        # weiterhin separat sichtbar und wird fuer Netz-/Batteriebilanzen benutzt.
        power_held_zero = power_usable is None and power_latest is not None and abs(power_latest) <= 0.5
        power_for_cal = power_usable
        power_display = power_latest
        power_status = ("frisch" if power_fresh is not None else
                        ("verzögert; letzter Wert nutzbar" if power_usable is not None else
                         ("veraltet; letzter numerischer Wert" if power_latest is not None
                          else "nicht verfuegbar")))
        power = power_usable
        if power_fresh is None and power_usable is not None:
            warnings.append(SLOT_NAMES[key] + ": AC-Leistung verzögert; letzter Wert wird kurz weiterverwendet")
        floor = number(raw(cfg["bottom"]), cfg["floor"])
        top = number(raw(cfg["top"]), 100)
        limits_ok = (
            floor is not None
            and top is not None
            and 0 <= floor < top <= 100
        )
        if not limits_ok:
            errors.append(
                f"{key}: SoC-Grenzen ungültig: unten {floor:g} %, oben {top:g} %. "
                "Erwartet: 0 ≤ unten < oben ≤ 100 %. "
                f"[{source_description(cfg['bottom'])}; {source_description(cfg['top'])}]"
            )
            floor = cfg["floor"]
            top = 100
        model_nominal = (
            cfg["module_kwh"] * pack_counts.get(key, 1)
            if cfg["module_kwh"] is not None
            else cfg["usable_default"] / (1 - cfg["floor"] / 100)
        )
        nominal = setting(
            "nennkapazitaet_" + key.lower() + "_kwh",
            model_nominal,
            0.1,
            30,
        )
        if cfg["module_kwh"] is not None:
            nominal = model_nominal
        usable = nominal * (1 - floor / 100)
        capacity_ok = 0 < usable < 20
        if not capacity_ok:
            errors.append(f"{key}: Nutzbare Kapazität {usable:g} kWh ungültig; erwartet größer 0 und kleiner 20 kWh")
            nominal = model_nominal
            usable = nominal * (1 - floor / 100)
        pack_count = pack_counts.get(key, 1)
        packs = []
        if soc is None:
            errors.append(key + ": " + soc_error(cfg["soc"], "Gesamt-SoC"))
        if cfg["has_packs"]:
            if len(PACKS[key]) < pack_count:
                errors.append(f"{key}: Pack-SoC-Zuordnung unvollständig: {len(PACKS[key])} Sensoren für {pack_count} erwartete Packs")
            for index, entity in enumerate(PACKS[key][:pack_count], start=1):
                value = measurement(entity, "soc")
                if value is None:
                    errors.append(key + ": " + soc_error(entity, f"Pack {index}-SoC"))
                else:
                    packs.append(value)
            packs_ok = len(packs) == pack_count
        else:
            packs_ok = soc is not None
            packs = [soc] if soc is not None else []
        effective_goal = top
        values = energy(nominal, floor, soc if soc is not None else floor, effective_goal)
        lower_soc = min(packs) if packs else soc
        higher_soc = max(packs) if packs else soc

        cal_empty_ready = (soc is not None and soc <= 14 and higher_soc is not None
                           and higher_soc <= 14.5)
        all_full = packs_ok and lower_soc is not None and lower_soc >= 100 and soc is not None and soc >= 100
        prior_target_met = flag(
            prior_attributes.get("ziel_venus_" + key.lower() + "_erreicht", False)
        )
        prior_target_goal = prior_attributes.get(
            "ziel_venus_" + key.lower() + "_latch_soc"
        )
        target_met, target_latch_reason = target_latch(
            goal=effective_goal,
            soc=soc,
            lowest_soc=lower_soc if packs_ok else None,
            prior_latched=prior_target_met,
            prior_goal=prior_target_goal,
        )

        if target_met:
            values["need"] = 0
        elif packs_ok and soc is not None:
            values["need"] = max(values["need"], nominal / len(packs) * max(0, effective_goal - lower_soc) / 100, 0.001)
        cap = cfg["maximum"]
        owns = (raw(cfg["auto"]) == "on" and raw(cfg["active"]) == "on"
                and raw(cfg["override"]) != "on")

        charge_limit_ok = writable(cfg["charge"], 0) and writable(cfg["charge"], cap)
        usable_data = (soc is not None and packs_ok and capacity_ok and limits_ok and charge_limit_ok)
        if not charge_limit_ok:
            errors.append(key + ": " + charge_limit_error(cfg["charge"], cap))
        values.update({"soc": soc, "power": power, "power_live": power_usable,
                       "power_display": power_display,
                       "inverter_status": inverter_status, "inverter_fresh": inverter_fresh,
                       "power_fresh": power_fresh is not None, "power_status": power_status,
                       "power_reported_ts": power_reported_ts, "power_age_min": power_age_min,
                       "power_held_zero": power_held_zero, "power_for_cal": power_for_cal,
                       "charge_power": charging_power(key, power),
                       "grid_effect": power_usable * cfg["charge_sign"] if power_usable is not None else None,
                       "nominal": nominal, "usable": usable, "floor": floor,
                       "goal": effective_goal, "packs_ok": packs_ok, "packs": packs,
                       "lowest_soc": lower_soc, "highest_soc": higher_soc,
                       "cal_empty_ready": cal_empty_ready,
                       "all_full": all_full, "target_met": target_met,
                       "target_latch_reason": target_latch_reason, "owns": owns,
                       "usable_data": usable_data, "cap": cap})
        bats[key] = values

    mppt_values = [measurement(entity, "power", 180) for entity in MPPTS]
    mppt_fresh = all([value is not None and 0 <= value <= 20000 for value in mppt_values])
    mppt_sum = sum(mppt_values) if mppt_fresh else None
    balance_surplus = None
    if grid is not None and all([bats[key]["power_live"] is not None for key in BATTERY_KEYS]):
        balance_surplus = max(0, sum([bats[key]["grid_effect"] for key in BATTERY_KEYS]) - grid)

    balance_lower = None
    if grid is not None:
        balance_lower = max(0, -grid + sum([bats[key]["grid_effect"] if bats[key]["power_live"] is not None
                            else -(BATTERIES[key]["maximum"] * 1.1 + 100) for key in BATTERY_KEYS]))
    pv_status = "frisch" if pv_fresh is not None else ("Nacht-Ersatzwert" if pv_night_fallback else
                 ("0 W ohne Neumeldung" if pv_held_zero else "AC-Summe nicht frisch"))
    pv_estimate = pv if pv_fresh is not None or pv_night_fallback else None
    pv_estimate_source = "AC-Messung" if pv_fresh is not None else ("Nacht-Ersatzwert" if pv_night_fallback else "keine")
    if pv_estimate is None and balance_surplus is not None and live_load is not None:
        pv_estimate = max(0, live_load + sum([bats[key]["grid_effect"] for key in BATTERY_KEYS]) - grid)
        pv_estimate_source = "Rekonstruktion aus Hauslast, Netz und Batterien"
    elif pv_estimate is None and mppt_fresh:
        pv_estimate = mppt_sum * 0.85
        pv_estimate_source = "MPPT-DC x 0.85"
    if pv_fresh is None and pv_estimate is not None:
        warnings.append("AC-PV-Summe nicht frisch; Ersatzwert nutzt " + pv_estimate_source)

    pv_live = pv if pv_fresh is not None or pv_night_fallback else (
        mppt_sum * 0.85 if mppt_fresh else None)
    pv_live_source = ("PV-AC" if pv_fresh is not None else
                      ("Nacht" if pv_night_fallback else
                       ("MPPT-DC x 0.85" if mppt_fresh else "keine")))

    today = forecast("today", DAY0, DAY1)
    tomorrow = forecast("tomorrow", DAY1, DAY2)
    past_wh = 0
    now_forecast = 0
    for row in today["rows"]:
        fraction = max(0, min(1, (NOW - row["t"]) / 900))
        past_wh = past_wh + row["wh"] * fraction
        if row["t"] <= NOW < row["t"] + 900:
            now_forecast = row["wh"] * 4
    day_factor, forecast_confidence = forecast_day_factor(
        actual_today if daily_ok else None, past_wh
    )
    short_factor = max(0.2, min(1, pv_estimate / now_forecast)) if pv_estimate is not None and now_forecast >= 1000 else 1

    rows = []
    corrected_rest_wh = 0
    for row in today["rows"]:
        correction = forecast_factor(short_factor, day_factor, row["t"] - NOW)
        factor = correction * safety
        rows.append({"t": row["t"], "wh": row["wh"] * factor})
        remaining_fraction = max(0, min(1, (row["t"] + 900 - NOW) / 900))
        corrected_rest_wh += row["wh"] * correction * remaining_fraction
    raw_total = sum([row["wh"] for row in today["rows"]]) / 1000
    raw_rest = max(0, raw_total - past_wh / 1000)
    expected_rest = corrected_rest_wh / 1000
    expected_total = (actual_today if daily_ok else past_wh / 1000) + expected_rest
    category, category_candidate, category_candidate_since = stable_day_class(
        expected_total, (weak, middle, strong), NOW, DAY0, prior_attributes
    )
    if category == "schwach":
        preferred = DAY0
    elif category == "mittel":
        if expected_total < middle:
            preferred = NINE - 7200 * max(0, min(1, (middle - expected_total) / max(0.01, middle - weak)))
        else:
            preferred = NINE + (ELEVEN - NINE) * max(0, min(1, (expected_total - middle) / max(0.01, strong - middle)))
    else:
        preferred = ELEVEN
    # "Wechselhaft" is an early-target profile based on measured uncertainty,
    # never a fourth daily yield class. Preserve the existing user settings.
    early_profile = ("wechselhaft" if category == "mittel" and
                     (short_factor < 0.7 or day_factor < 0.9) else category)
    early_soc_goals = {
        key: setting(
            "fruehes_ladeziel_" + key.lower() + "_" + early_profile + "_soc",
            setting("fruehes_ladeziel_" + key.lower() + "_soc", 0, 0, 100),
            0, 100,
        )
        for key in BATTERY_KEYS
    }

    direct_surplus = max(0, pv_live - live_load) if pv_live is not None and live_load is not None else None
    live_valid = grid is not None and (direct_surplus is not None or balance_surplus is not None
                                       or (balance_lower is not None and balance_lower >= 200))
    live_surplus = 0
    surplus_source = "ungültig"
    night_zero_certified = sun_below_horizon and pv == 0
    if night_zero_certified:
        live_valid = True
        live_surplus = 0
        surplus_source = "Nacht: bestätigte 0 W PV"
    elif live_valid:
        live_surplus = min(direct_surplus, balance_surplus) if direct_surplus is not None and balance_surplus is not None else (direct_surplus if direct_surplus is not None else balance_surplus)
        direct_label = pv_live_source + " minus Hauslast"
        surplus_source = direct_label if balance_surplus is None else ("Bilanz und " + direct_label if direct_surplus is not None else "Netz-/Batteriebilanz")
        if direct_surplus is None and balance_surplus is None:
            live_surplus = balance_lower
            surplus_source = "Netzeinspeisung abzüglich maximaler unbekannter Batterieentladung"
        if pv is None:
            warnings.append("PV-Summe ersetzt keine Messung: Ladefreigabe durch " + surplus_source)
        if direct_surplus is not None and balance_surplus is not None and abs(direct_surplus - balance_surplus) > 500:
            warnings.append("Live-Überschussprüfungen weichen um mehr als 500 W voneinander ab")
    data_errors = []
    if pv is None and not live_valid:
        data_errors.append("PV-Leistung fehlt oder ist veraltet")
    if grid is None:
        data_errors.append("Netzleistung fehlt oder ist veraltet")
    if load_raw is None:
        warnings.append("Hauslastmittel fehlt: Planung mit 1000 W Ersatzlast")
    if not live_valid and pv is not None and grid is not None:
        data_errors.append("Weder aktuelle Hauslast noch vollständige Batteriebilanz verfügbar")
    data_errors.extend(errors)
    pv_chance = live_valid and live_surplus >= 200
    reaction_blocked_prior = {}
    for key in BATTERY_KEYS:
        # Eine ausbleibende AC-Reaktion ist nur ein Hinweis.
        # Eine aus einer frueheren Installation uebernommene Sperre darf nicht weiterwirken.
        reaction_blocked_prior[key] = False
    last_data_errors = data_errors
    last_data_error_ts = NOW if data_errors else None
    if not data_errors and prior_attributes:
        last_data_errors = prior_attributes.get("letzte_datenfehler", [])
        last_data_error_ts = number(prior_attributes.get("letzter_datenfehler_ts"))

    previews_today = {}
    previews_tomorrow = {}
    cal_safe = {}
    cal_critical = {}
    cal_armed = {}
    cal_errors = {}
    for key in BATTERY_KEYS:
        cfg = BATTERIES[key]
        model = learning["models"][key]
        learned_ac = 0
        if (number(model.get("count"), 0) >= 1
                and abs(number(model.get("usable_reference"), 0) - bats[key]["usable"]) < 0.01):
            learned_ac = number(model.get("ac_kwh"), 0)

        if learned_ac > 0:
            # A measured AC value already contains inverter and battery losses.
            calibration_energy = learned_ac
            calibration_energy_source = "gelernt"
        elif cfg.get("reference_ac_per_module") is not None:
            calibration_energy = cfg["reference_ac_per_module"] * pack_counts.get(key, 1)
            calibration_energy_source = "Modellreferenz"
        else:
            calibration_energy = number(cfg.get("reference_ac"), bats[key]["usable"] / eta)
            calibration_energy_source = "Modellreferenz"
        hours = calibration_energy / (calibration_power / 1000)
        # The lower rest is preferred, but must not remove a usable PV window
        # from the forecast. Its actual duration is recorded at charge start.
        earliest = NOW
        # Match the time-dependent correction used by the normal PV plan.
        # A temporary live PV shortfall must not discount every later bucket
        # by the same near-term factor. `rows` already includes safety.
        previews_today[key] = continuous_window(rows, earliest, hours, load, 1)
        previews_tomorrow[key] = continuous_window(tomorrow["rows"], max(DAY1, earliest), hours, load, safety)
        previews_today[key]["energy_kwh"] = round(calibration_energy, 4)
        previews_today[key]["energy_source"] = calibration_energy_source
        previews_tomorrow[key]["energy_kwh"] = round(calibration_energy, 4)
        previews_tomorrow[key]["energy_source"] = calibration_energy_source
        # Keine Altersgrenze fuer die Zelltemperatur -- der LilyGo-
        # Sensor meldet nur bei tatsaechlicher Wertaenderung und kann bei einer
        # Kalibrier-Vormerkung fuer den naechsten Tag 24h+ ohne neue Meldung
        # bleiben, ohne dass das ein Fehler ist. Wertebereich (5-40 C) und
        # Vorhandensein werden weiterhin geprueft, nur die Alterssperre entfaellt.
        tmin = measurement(cfg["tmin"], "temperature")
        tmax = measurement(cfg["tmax"], "temperature")
        vmax = measurement(cfg["vmax"], "voltage")
        problems = []
        if not bats[key]["owns"]:
            problems.append(SLOT_NAMES[key] + ": Auto Target/Active oder manuelle Sperre prüfen")
        if not bats[key]["usable_data"]:
            problems.append(SLOT_NAMES[key] + ": eigene SoC-/Ladegrenzendaten ungültig")
        if bats[key]["power_for_cal"] is None:
            problems.append(SLOT_NAMES[key] + ": eigene AC-Leistung für Kalibrierung nicht frisch")
        if tmin is None or tmax is None or not 5 <= tmin <= tmax <= 40:
            problems.append(SLOT_NAMES[key] + ": Temperaturfenster 5–40 °C nicht bestätigt")
        if vmax is None or not 2.5 <= vmax < 3.60:
            problems.append(SLOT_NAMES[key] + ": Zellspannung fehlt oder ausserhalb des Kalibrierfensters")
        if number(raw(cfg["top"])) != 100:
            problems.append(SLOT_NAMES[key] + ": oberes SoC-Limit muss 100 % sein")
        if number(raw(cfg["bottom"]), cfg["floor"]) != 12:
            problems.append(SLOT_NAMES[key] + ": unteres SoC-Limit muss für die Kalibrierung 12 % sein")
        if not writable(cfg["discharge"], 0) or not writable(
            cfg["charge"], calibration_power
        ):
            problems.append(
                "Venus "
                + key
                + ": eigene 0-W-Entlade-/"
                + str(calibration_power)
                + "-W-Ladegrenze fehlt"
            )
        if failure_counts[key] >= 3:
            problems.append(SLOT_NAMES[key] + ": drei Schreibfehler; Quittierung erforderlich")
        cal_safe[key] = not problems
        cal_critical[key] = ((tmin is not None and tmax is not None and not 5 <= tmin <= tmax <= 40)
                             or (vmax is not None and not 2.5 <= vmax < 3.60))
        cal_errors[key] = problems
        cal_armed[key] = raw("input_boolean.speicher_ladelogik_ae_kalibrierung_" + key.lower() + "_freigegeben") == "on"

    backup = read_backup(raw(BACKUP_ID))
    cal_backup = read_backup(raw(CAL_BACKUP_ID))
    allowed_backup_fields = {
        field
        for key in BATTERY_KEYS
        for field in (key, "D" + key)
    }
    for saved in (backup, cal_backup):
        if saved is not None:
            for field in tuple(saved):
                if field not in allowed_backup_fields:
                    saved.pop(field)
            for key in BATTERY_KEYS:
                saved.setdefault(key, -1)
                saved.setdefault("D" + key, -1)
    session = read_session(raw(SESSION_ID))
    secondary = read_session(data.get("parallel_session", ""))
    parallel_enabled = bool(data.get("parallel_calibration", False))
    # A completed primary yields its slot to a still active secondary. This
    # preserves the legacy session helper and its existing HA migrations.
    if session["p"] in {"idle", "done", "incomplete", "cancelled"} and secondary["p"] in ACTIVE_PHASES:
        session, secondary = secondary, read_session("")
    queue_value = raw(QUEUE_ID)

    if queue_value in ["unknown", "unavailable"] and raw("input_boolean.speicher_ladelogik_ae_v1_beta_1_initialisiert") != "on":
        queue_value = ""
    queue = read_queue(queue_value)
    current_caps = cap_snapshot()
    records_ok = (session["p"] != "error" and secondary["p"] != "error"
                  and (secondary["p"] not in ACTIVE_PHASES or secondary["b"] != session["b"])
                  and raw(SESSION_ID) not in ["unknown", "unavailable"]
                  and (backup is not None or raw(BACKUP_ID) == "")
                  and (cal_backup is not None or raw(CAL_BACKUP_ID) == "") and queue is not None)
    if queue is None:
        queue = {}
    else:
        queue = {key: value for key, value in queue.items() if key in BATTERY_KEYS}
        for item in queue.values():
            if item.get("d") not in {"-", *BATTERY_KEYS}:
                item["d"] = "-"
    original_phase = session["p"]
    original_battery = session["b"]
    secondary_original_phase = secondary["p"]
    save_backup = ""
    save_cal_backup = ""
    clear_cal_backup = False
    clear_backup = False
    queue_notify = ""
    effective_request = REQUEST
    request_map = {
        request: key
        for key in BATTERY_KEYS
        for request in ("cal_" + key.lower(), "cal_" + key.lower() + "_tomorrow")
    }
    if REQUEST in request_map and records_ok:
        key = request_map[REQUEST]
        not_before = int(DAY1 if REQUEST.endswith("tomorrow") else DAY0)
        if not automatic or not cal_armed[key]:
            queue_notify = "Vormerkung erfordert Automatik und die Kalibrierfreigabe für " + SLOT_NAMES[key] + "."
        elif any(s["p"] in ACTIVE_PHASES and s["b"] == key for s in (session, secondary)):
            current = next(s for s in (session, secondary) if s["p"] in ACTIVE_PHASES and s["b"] == key)
            if current["p"] in {"requested", "drain", "empty_rest", "wait"} or (
                current["p"] == "paused" and current["u"] in {"requested", "drain", "empty_rest", "wait"}
            ):
                current["n"] = not_before
                if current["p"] == "requested":
                    current["s"] = 0
                    current["x"] = 0
                elif current["p"] == "wait" or current["p"] == "paused" and current["u"] == "wait":
                    # Re-evaluate the chosen day immediately on the next step.
                    current["s"] = 0
                    current["x"] = 0
                queue_notify = "Termin für " + SLOT_NAMES[key] + " aktualisiert."
            elif current["p"] == "restore":
                queue[key] = {"n": not_before, "t": int(NOW), "d": "-"}
                queue_notify = SLOT_NAMES[key] + " wird nach Rückgabe der Grenzwerte erneut vorbereitet."
            else:
                queue_notify = SLOT_NAMES[key] + " wird bereits vorbereitet oder kalibriert."
        else:
            depends = session["b"] if session["p"] in ACTIVE_PHASES and not parallel_enabled else "-"
            queue[key] = {"n": not_before, "t": int(NOW), "d": depends}
            queue_notify = SLOT_NAMES[key] + (" für morgen vorgemerkt." if REQUEST.endswith("tomorrow") else " für das nächste geeignete Fenster vorgemerkt.")
    if REQUEST == "cancel":
        queue = {}
    elif REQUEST.startswith("cancel_") and REQUEST[-1:].upper() in BATTERY_KEYS:
        key = REQUEST[-1:].upper()
        queue.pop(key, None)
        if session["b"] == key and session["p"] in ACTIVE_PHASES:
            effective_request = "cancel"
            for item in queue.values():
                if item["d"] == key:
                    queue_notify = "Folgeauftrag bleibt vorgemerkt und wartet auf erneute Anforderung."
    for key in BATTERY_KEYS:
        if key in queue and not cal_armed[key]:
            queue.pop(key)

    cancel_requests = ["cancel_" + key.lower() for key in BATTERY_KEYS]
    if session["p"] not in ACTIVE_PHASES and secondary["p"] not in ACTIVE_PHASES and records_ok and automatic and REQUEST not in ["start", "cancel", *cancel_requests]:
        candidates = [key for key in BATTERY_KEYS if key in queue and queue[key]["d"] == "-"
                      and cal_armed[key] and failure_counts[key] < 3]
        chosen = None
        for key in candidates:
            if chosen is None or queue[key]["t"] < queue[chosen]["t"]:
                chosen = key
        if chosen is not None:
            q = queue.pop(chosen)
            session = read_session("")
            session["b"] = chosen
            session["z"] = pack_counts.get(chosen, 1)
            session["n"] = q["n"]
            transition(session, "requested", "requested")

    if (parallel_enabled and records_ok and automatic
            and session["p"] in {"wait", "charge"}
            and secondary["p"] not in ACTIVE_PHASES
            and REQUEST not in ["cancel", *cancel_requests, "start"]):
        eligible = [key for key in BATTERY_KEYS
                    if key in queue and queue[key]["d"] == "-" and queue[key]["n"] <= DAY0
                    and key != session["b"] and cal_armed[key]
                    and failure_counts[key] < 3 and cal_safe[key]
                    and bats[key]["cal_empty_ready"]
                    and previews_today[key]["ok"]]
        if eligible:
            chosen = min(eligible, key=lambda key: queue[key]["t"])
            q = queue.pop(chosen)
            secondary = read_session("")
            secondary["b"] = chosen
            secondary["z"] = pack_counts.get(chosen, 1)
            secondary["n"] = q["n"]
            transition(secondary, "requested", "requested")

    cal_restored = cal_backup is None and session["s"] == 0
    if cal_backup is not None and session["b"] in BATTERY_KEYS:
        key = session["b"]
        own_saved = {key: cal_backup[key], "D" + key: cal_backup["D" + key]}
        cal_restored = backup_restored(own_saved, current_caps)
    other_running = [s for s in (session, secondary) if s["p"] == "charge"
                     or (s["p"] == "paused" and s.get("u") == "charge")]
    shared_surplus = live_surplus
    active_parallel = secondary["p"] in ACTIVE_PHASES
    factor = sum(s["p"] in {"wait", "charge"} or (s["p"] == "paused" and s["u"] == "charge")
                 for s in (session, secondary))
    cal_context = {"request": effective_request, "automatic": automatic,
        "armed": cal_armed, "safe": cal_safe, "critical": cal_critical,
        "batteries": bats, "today": previews_today, "tomorrow": previews_tomorrow,
        "backup": cal_backup, "restored": cal_restored,
        "grid_power": grid, "live_surplus": live_surplus,
        "parallel": active_parallel, "shared_surplus": shared_surplus,
        "parallel_factor": max(1, factor), "running_factor": max(1, len(other_running)),
        "pack_count": pack_counts.get(session.get("b"), 1),
        "peer_drain_ok": {key: failure_counts[key] < 3 and writable(BATTERIES[key]["discharge"], 0) for key in BATTERY_KEYS},
        "peer_discharge_max": {
            key: number(
                hass.states.get(BATTERIES[key]["discharge"]).attributes.get("max")
                if hass.states.get(BATTERIES[key]["discharge"]) is not None
                else None,
                BATTERIES[key]["maximum"],
            )
            for key in BATTERY_KEYS
        }}
    cal = calibration_step(session, cal_context)
    session = cal["session"]
    secondary_cal = None
    if secondary["p"] in ACTIVE_PHASES:
        other = secondary["b"]
        secondary_restored = cal_backup is None and secondary["s"] == 0
        if cal_backup is not None and other in BATTERY_KEYS:
            secondary_restored = backup_restored(
                {other: cal_backup[other], "D" + other: cal_backup["D" + other]}, current_caps)
        secondary_context = {**cal_context,
            "request": "cancel" if REQUEST == "cancel" or REQUEST == "cancel_" + other.lower() else "tick",
            "restored": secondary_restored,
            "pack_count": pack_counts.get(other, 1),
            "parallel_factor": max(1, factor + int(session["p"] == "charge" and original_phase != "charge")),
        }
        secondary_cal = calibration_step(secondary, secondary_context)
        secondary = secondary_cal["session"]
        for action in ("charge", "discharge"):
            # Secondary is only admitted when already empty; it never issues
            # peer drain overrides against the primary calibration.
            cal[action].update(secondary_cal[action])
    if not records_ok:
        cal["finish"] = False
        cal["retry"] = False
        if secondary_cal:
            secondary_cal["finish"] = secondary_cal["retry"] = False
    for outcome in (cal, secondary_cal):
        if outcome is not None and "lower_rest_s" in outcome and outcome["session"]["b"] in BATTERY_KEYS:
            learning["last_precharge_rest"][outcome["session"]["b"]] = {
                "seconds": outcome["lower_rest_s"], "timestamp": NOW,
            }
    for current, outcome in ((session, cal), (secondary, secondary_cal)):
        if outcome is None:
            continue
        if outcome["finish"]:
            for item in queue.values():
                if item["d"] == current["b"]:
                    item["d"] = "-"
        if outcome["retry"]:
            key = current["b"]
            queue[key] = {"n": int(max(current["n"], DAY1)), "t": int(NOW), "d": "-"}

    if automatic and records_ok:
        if backup is None:
            backup = {
                **{key: -1 for key in BATTERY_KEYS},
                **{"D" + key: -1 for key in BATTERY_KEYS},
            }
        changed = False
        for key in BATTERY_KEYS:
            fields = [key, "D" + key]
            for field in fields:
                entity = BATTERIES[key]["discharge" if field == "D" + key else "charge"]
                if (bats[key]["owns"] and failure_counts[key] < 3 and backup[field] == -1
                        and current_caps[field] is not None and writable(entity, current_caps[field])):
                    backup[field] = current_caps[field]
                    changed = True
        if changed:
            save_backup = encode_backup(backup)

    if (any(s["p"] in ["drain", "empty_rest", "wait", "charge", "rest", "full_rest", "paused"]
            for s in (session, secondary)) and records_ok):
        if cal_backup is None:
            cal_backup = {
                **{key: -1 for key in BATTERY_KEYS},
                **{"D" + key: -1 for key in BATTERY_KEYS},
            }
        previous_backup = encode_backup(cal_backup)
        for current in (session, secondary):
            if current["p"] in ["drain", "empty_rest", "wait", "charge", "rest", "full_rest", "paused"]:
                key = current["b"]
                for field in [key, "D" + key]:
                    if cal_backup[field] == -1 and current_caps[field] is not None:
                        cal_backup[field] = current_caps[field]
        for other in cal["discharge"]:
            if cal_backup["D" + other] == -1 and current_caps["D" + other] is not None:
                cal_backup["D" + other] = current_caps["D" + other]
        if previous_backup != encode_backup(cal_backup):
            save_cal_backup = encode_backup(cal_backup)

    held = {}
    for key in BATTERY_KEYS:
        pending = key in queue or any(s["p"] in ACTIVE_PHASES and s["b"] == key
                                      for s in (session, secondary))
        held[key] = pending and raw("input_boolean.speicher_ladelogik_ae_kalibrierung_" + key.lower() + "_laden_sperren") == "on"
    cal_active = session["b"] if session["p"] in [
        "drain",
        "empty_rest",
        "wait",
        "charge",
        "rest",
        "full_rest",
        "paused",
        "restore",
    ] else ""
    cal_active_keys = {s["b"] for s in (session, secondary) if s["p"] in ACTIVE_PHASES}
    normal_eligible = {
        key: bats[key]["owns"] and bats[key]["usable_data"] and failure_counts[key] < 3
        and not reaction_blocked_prior[key]
        and key not in cal_active_keys and not held[key] and not manual_active_by_key[key]
        and BATTERIES[key]["maximum"] > 0 and BATTERIES[key]["preferred"] > 0
        for key in BATTERY_KEYS
    }
    needs = {key: bats[key]["need"] if normal_eligible[key] else 0 for key in BATTERY_KEYS}
    need = sum(needs.values())
    stored = sum(bats[key]["stored"] for key in BATTERY_KEYS)
    target_energy = sum(bats[key]["target"] for key in BATTERY_KEYS)
    normal_stored = sum(bats[key]["stored"] for key in BATTERY_KEYS if normal_eligible[key])
    normal_target = sum(bats[key]["target"] for key in BATTERY_KEYS if normal_eligible[key])
    cal_draw = calibration_power * sum(s["p"] == "charge" for s in (session, secondary))
    manual_draw = sum(manual_charge[key] for key in BATTERY_KEYS
                      if manual_active_by_key[key] and not bats[key]["target_met"])
    normal_rows = []
    for row in rows:
        reservation = manual_draw
        for current in (session, secondary):
            if current["b"] in cal_active_keys and current["p"] in ["wait", "charge", "paused"]:
                overlap = max(0, min(row["t"] + 900, max(NOW, current["x"]) + 1800)
                              - max(row["t"], current["s"]))
                reservation += calibration_power * overlap / 900
        normal_rows.append({"t": row["t"], "wh": max(0, row["wh"] - reservation / 4)})
    solar_rows = [row for row in rows if row["wh"] * 4 > load]
    solar_start = solar_rows[0]["t"] if solar_rows else None
    solar_end = solar_rows[-1]["t"] + 900 if solar_rows else NOW
    end = max(NOW, solar_end)
    peak_configured = raw("input_boolean.speicher_ladelogik_ae_mittagsspitzen") != "off"
    peak_enabled = peak_configured and category != "schwach"
    normal_live = max(0, live_surplus - cal_draw - manual_draw)
    automatic_limits = {}
    automatic_limit_held = {}
    automatic_limit_reason = {}
    specs = {
        key: {**bats[key], "maximum": BATTERIES[key]["maximum"],
              "discharge_maximum": BATTERIES[key]["discharge_maximum"],
              "preferred": BATTERIES[key]["preferred"], "tail": BATTERIES[key]["tail"],
              "actual_limit": number(current_caps[key], 0), "early_goal": early_soc_goals[key]}
        for key in BATTERY_KEYS if normal_eligible[key]
    }
    daily = daily_plan(
        now=NOW, day=DAY0, end=end, midday_start=MIDDAY_START, midday_end=MIDDAY_END,
        preferred_start=preferred, category=category, peak_enabled=peak_enabled,
        forecast_ok=today["ok"], live_surplus=normal_live,
        pv_chance=live_valid and normal_live >= 200,
        rows=normal_rows, load=load, efficiency=eta, cloud_reserve=extra,
        reserve_factor=setting("knappheitsreserve", 125, 100, 200) / 100,
        hysteresis=setting("hysterese", 0.2, 0.05, 1), batteries=specs, prior=prior_attributes,
    )
    decisions = daily["decisions"]
    early_soc_keys = daily["early_keys"]
    scarce = daily["scarce"]
    safe_rest = daily["available_kwh"]
    window_wh = safe_rest * 1000 / eta
    normal_sim = daily["result"]
    start = min((d["released_at"] if d["released_at"] is not None else d["start"]
                 for d in decisions.values()), default=NOW)
    early = any(d["start"] < preferred for d in decisions.values())
    efficient_caps = {key: BATTERIES[key]["preferred"] if normal_eligible[key] else 0 for key in BATTERY_KEYS}
    simulation_end = end
    morning = sum(row["wh"] / 1000 for row in rows if row["t"] < SOLAR_NOON)
    afternoon = sum(row["wh"] / 1000 for row in rows if row["t"] >= SOLAR_NOON)
    export_since = None
    rescue_morning, rescue_keys = False, []
    peak_live_override, peak_live_headroom, peak_live_since = False, 0, None
    peak = {"ok": daily["peak_possible"], "target": daily["peak_export"],
            "start": start if daily["peak_possible"] else None,
            "end": MIDDAY_END if daily["peak_possible"] else None,
            "finish": normal_sim["finish"] if daily["peak_possible"] else None}
    automatic_slot_active = {}
    for key in BATTERY_KEYS:
        d = decisions.get(key)
        safety_stop = (not automatic or not records_ok or not live_valid
                       or not bats[key]["usable_data"] or failure_counts[key] >= 3)
        value = d["limit"] if d else 0
        why = d["reason"] if d else "Speicher nicht für Fahrplan freigegeben"
        if safety_stop:
            value, why = 0, "Sicherheitsstopp"
        automatic_limits[key] = value
        automatic_limit_reason[key] = why
        automatic_limit_held[key] = bool(value > 0 and number(current_caps[key], 0) == value)
        automatic_slot_active[key] = bool(d and d["active"] and not safety_stop)
    # The displayed raw and selected limits now describe the same decision.
    automatic_limits_raw = automatic_limits.copy()
    limits = automatic_limits.copy()
    if not live_valid:
        automatic_status, automatic_reason = "Datenfehler", "Keine verlässliche Live-Überschusserkennung"
    elif need <= 0:
        automatic_status, automatic_reason = "Ziel erreicht", "Kein Restbedarf in den freigegebenen Speichern"
    elif any(automatic_slot_active.values()):
        automatic_status = "Ladefreigabe aktiv" if normal_live >= 200 else "Ladegrenze bleibt gesetzt"
        automatic_reason = "; ".join(SLOT_NAMES[k] + ": " + automatic_limit_reason[k]
                                     for k in BATTERY_KEYS if automatic_slot_active[k])
    else:
        automatic_status = "Platz für Mittagsspitze halten" if peak["ok"] else "Warten auf Ladebeginn"
        automatic_reason = "Jeder Speicher startet zum eigenen geplanten Zeitpunkt mit PV-Überschuss"
    efficiency_mode = ("Bedarfsgerecht erhöhte Ladegrenze" if daily["boosted"]
                       else "Bevorzugte Leistung; Freigabe bleibt nach Start bestehen")

    manual_allowed = {}
    for key in BATTERY_KEYS:
        manual_allowed[key] = (manual_active_by_key[key] and key not in cal_active_keys
                               and bats[key]["owns"] and failure_counts[key] < 3)
        if manual_allowed[key]:
            limits[key] = manual_charge[key]

    manual_keys = [key for key in BATTERY_KEYS if manual_active_by_key[key]]
    if manual_keys:
        status = "Manuelle Grenze " + "/".join(manual_keys)
        efficiency_mode = "Manuelle Grenze nur für " + "/".join(manual_keys)
        descriptions = []
        for key in manual_keys:
            descriptions.append(key + " Laden/Entladen " + str(manual_charge[key])
                                + "/" + str(manual_discharge[key]) + " W")
        reason = "Manuell: " + "; ".join(descriptions) + ". Anderer Speicher bleibt im Fahrplan."
    else:
        status = automatic_status
        reason = automatic_reason
        if sum(automatic_limits_raw.values()) == 0 and any(automatic_slot_active.values()):
            status = "Sollwert wird gehalten"
            reason = "Grenzwert bleibt gesetzt; AstraMeter begrenzt die reale Leistung am Netzanschlusspunkt"

    reaction = {}
    reaction_newly_blocked = []  # Compatibility name: these are hints, never locks.
    reaction_resolved = []
    for key in BATTERY_KEYS:
        name = key.lower()
        requested = (limits[key] > 0 and key not in cal["charge"]
                     and (manual_active_by_key[key] or automatic_limits_raw[key] > 0))
        feedback = ac_feedback(
            now=NOW, requested=requested, fresh=bats[key]["power_fresh"],
            inverter_status=bats[key]["inverter_status"],
            inverter_fresh=bats[key]["inverter_fresh"],
            prior=prior_attributes.get("ac_rueckmeldung_venus_" + name) or {},
        )
        reaction[key] = feedback
        if feedback["notify"]:
            reaction_newly_blocked.append(key)
        if feedback["resolved"]:
            reaction_resolved.append(key)
        if feedback["issue"]:
            warnings.append(SLOT_NAMES[key] + ": " + feedback["message"])

    reaction_blocked_keys = [key for key in BATTERY_KEYS if reaction[key]["blocked"]]

    if data_errors:
        last_data_errors = data_errors
        last_data_error_ts = NOW
    normal_limits = automatic_limits.copy()
    normal_status = automatic_status
    normal_reason = automatic_reason

    hardware_commands = []
    release_ready = True
    normal_release = not automatic and backup is not None
    cal_release = (cal["release"] or bool(secondary_cal and secondary_cal["release"])) and cal_backup is not None
    release = normal_release or cal_release
    cal_changed = False
    normal_changed = False
    order = list(BATTERY_KEYS)
    for current in (secondary, session):
        if current["p"] in ACTIVE_PHASES and current["b"] in order:
            order.remove(current["b"])
            order.insert(0, current["b"])
    for key in order:
        permitted = records_ok and bats[key]["owns"] and failure_counts[key] < 3 and backup is not None and backup[key] >= 0
        active_own = any(s["p"] in [
            "drain",
            "empty_rest",
            "wait",
            "charge",
            "rest",
            "full_rest",
            "paused",
        ] and s["b"] == key for s in (session, secondary))
        restoring_fields = []
        if cal_backup is not None:
            for field in ["D" + key, key]:
                preserve = (active_own or (field == "D" + key and key in cal["discharge"]))
                if cal_backup[field] >= 0 and not preserve:
                    restoring_fields.append(field)
        key_restoring = bool(restoring_fields)
        for field in restoring_fields:
            value = cal_backup[field]
            entity = BATTERIES[key]["discharge" if field == "D" + key else "charge"]
            if current_caps[field] is not None and abs(current_caps[field] - value) < 25:
                cal_backup[field] = -1
                cal_changed = True
            elif permitted and writable(entity, value):
                hardware_commands.append({"entity": entity, "value": value, "battery": key, "restore": True})
            else:
                release_ready = False
        manual_d_field = "D" + key
        restore_manual_discharge = (backup is not None and backup[manual_d_field] >= 0
                                    and not automatic
                                    and not active_own and key not in cal["discharge"]
                                    and not key_restoring)
        if restore_manual_discharge:
            value = backup[manual_d_field]
            if (current_caps[manual_d_field] is not None
                    and abs(current_caps[manual_d_field] - value) < 25):
                backup[manual_d_field] = -1
                normal_changed = True
            elif permitted and writable(BATTERIES[key]["discharge"], value):
                hardware_commands.append({"entity": BATTERIES[key]["discharge"], "value": value,
                                          "battery": key, "restore": True})
            else:
                release_ready = False
        if normal_release and not key_restoring and backup[key] >= 0:
            value = backup[key]
            if current_caps[key] is not None and abs(current_caps[key] - value) < 25:
                backup[key] = -1
                normal_changed = True
            elif permitted and writable(BATTERIES[key]["charge"], value):
                hardware_commands.append({"entity": BATTERIES[key]["charge"], "value": value, "battery": key, "restore": True})
            else:
                release_ready = False
        elif automatic:
            if key in cal["charge"]:
                limits[key] = cal["charge"][key]
            if ((not manual_active_by_key[key] and (not bats[key]["usable_data"] or not live_valid))
                    or failure_counts[key] >= 3):
                limits[key] = 0
            if permitted:
                if key in cal["discharge"]:
                    value = cal["discharge"][key]
                    if (cal_backup is not None and cal_backup["D" + key] >= 0
                            and writable(BATTERIES[key]["discharge"], value)
                            and write_needed(current_caps["D" + key], value)):
                        hardware_commands.append({"entity": BATTERIES[key]["discharge"], "value": value, "battery": key, "restore": False})
                elif manual_active_by_key[key] and manual_allowed.get(key, False) and not key_restoring:
                    value = manual_discharge[key]
                    if (writable(BATTERIES[key]["discharge"], value)
                            and write_needed(current_caps["D" + key], value)):
                        hardware_commands.append({"entity": BATTERIES[key]["discharge"], "value": value,
                                                  "battery": key, "restore": False})
                elif not active_own and not key_restoring:
                    value = BATTERIES[key]["discharge_maximum"]
                    if (writable(BATTERIES[key]["discharge"], value)
                            and write_needed(current_caps["D" + key], value)):
                        hardware_commands.append({"entity": BATTERIES[key]["discharge"], "value": value,
                                                  "battery": key, "restore": False})
                if (not key_restoring and writable(BATTERIES[key]["charge"], limits[key])
                        and write_needed(current_caps[key], limits[key])) or (key_restoring and all([field == "D" + key for field in restoring_fields])
                        and writable(BATTERIES[key]["charge"], limits[key])
                        and write_needed(current_caps[key], limits[key])):
                    hardware_commands.append({"entity": BATTERIES[key]["charge"], "value": limits[key], "battery": key, "restore": False})
    if cal_changed:
        if all([value == -1 for value in cal_backup.values()]):
            clear_cal_backup = True
            save_cal_backup = ""
        else:
            save_cal_backup = encode_backup(cal_backup)
    if normal_changed:
        if all([value == -1 for value in backup.values()]):
            clear_backup = True
            save_backup = ""
        else:
            save_backup = encode_backup(backup)
    can_execute = records_ok and bool(hardware_commands)

    reasons = {"requested": "Auftrag gespeichert; wartet auf 600 W gemessene Einspeisung",
        "scheduled": "Termin vorgemerkt; Vorbereitung beginnt abends bei geringer PV",
        "no_window": "Prognosefenster knapp; Start bei 600 W gemessener Einspeisung möglich",
        "waiting_data": "Auftrag bleibt vorgemerkt; erforderliche eigene Daten fehlen",
        "waiting_pv": "Leer vorbereitet; wartet auf 600 W gemessene Netzeinspeisung",
        "natural_discharge": "Vorbereitung durch Hausverbrauch; keine erzwungene Einspeisung",
        "charging": str(calibration_power) + "-W-Limit; tatsächliche Ladeleistung wird überwacht",
        "empty_resting": f"14 % erreicht; {EMPTY_REST_SECONDS / 60:g} Minuten untere Ruhephase angestrebt",
        "resting": "Alle erwarteten SoCs bei 100 %; obere Ruhephase",
        "full_resting": f"100 % bestätigt; {FULL_REST_SECONDS / 60:g} Minuten obere Ruhephase für das BMS",
        "success": f"100 % und {FULL_REST_SECONDS / 60:g} Minuten obere Ruhephase bestätigt; eigene Grenzwerte zurückgegeben",
        "cancelled": "Vom Benutzer, Betriebsmodus oder eigener Freigabe beendet",
        "restart": "Neustart: vorheriger Lauf zurückgegeben; neuer Versuch vorgemerkt",
        "data_pause": "Pausiert: erforderliche eigene Daten oder Steuerung ungültig",
        "data_invalid": "Abbruch: kritische Daten oder Steuerfreigaben waren ungültig",
        "pv_pause": "Pausiert: PV-Überschuss reicht aktuell nicht für die Kalibrierladung",
        "resumed": "Ladung nach Pause wieder aufgenommen; Unterbrechung bleibt protokolliert",
        "device_limit": "Eigene Zellspannung oder Temperatur ausserhalb des Kalibrierfensters",
        "pack_changed": "Packzahl während des Versuchs geändert",
        "backup_missing": "Gesicherte Ausgangswerte fehlen: manuell prüfen",
        "state_corrupt": "Gespeicherter Sitzungszustand ungültig",
        "retry_empty": "Speicher noch nicht leer; Auftrag für nächsten geeigneten Tag erhalten",
        "retry_window": "PV-Fenster reicht nicht mehr; Auftrag für nächsten geeigneten Tag erhalten",
        "charge_timeout": "Kalibrierladung über 18 Stunden ohne bestätigtes Vollziel; erneuter Versuch vorgemerkt",
        "under_400w": (
            "Pausiert: eigene Ladeleistung mindestens 5 Minuten unter "
            + str(round(calibration_min_power))
            + " W"
        ),
        "full_unconfirmed": "100 % nicht bestätigt; 99 % gilt nicht als Erfolg",
        "sample_gap": "Pausiert: Messlücke über 90 Sekunden; Kontinuität nicht belegbar",
        "telemetry_no_response": "Pausiert: nach Ladefreigabe keine neue AC-Rückmeldung innerhalb von drei Minuten",
        "interrupted_full": "Volladung nach Pause; kein durchgehender Kalibriererfolg, Wiederholung vorgemerkt",
        "rest_timeout": "Ruhephase nicht erreichbar"}
    cal_reason = reasons.get(session["r"], session["r"])
    if session["p"] in ["requested", "paused"] and session["b"] in cal_errors and cal_errors[session["b"]]:
        cal_reason = cal_reason + ": " + "; ".join(cal_errors[session["b"]])
    if session["p"] in [
        "drain",
        "empty_rest",
        "wait",
        "charge",
        "rest",
        "full_rest",
        "paused",
        "restore",
    ]:
        status = "Kalibrierung " + SLOT_NAMES.get(session["b"], session["b"]) + ": " + PHASE_LABELS.get(session["p"], session["p"])
        reason = cal_reason
    if all([failure_counts[key] >= 3 for key in BATTERY_KEYS]):
        status = "Schreibfehler - gesperrt"
        reason = "Alle konfigurierten Speicher nach drei eigenen Schreibfehlern gesperrt"
    elif failure_count >= 3:
        warnings.append(
            "Schreibsperre betrifft nur "
            + "/".join(key for key in BATTERY_KEYS if failure_counts[key] >= 3)
        )
    if not records_ok or session["p"] == "error":
        status = "Sitzungsfehler - gesperrt"
        reason = "Sitzung/Ausgangswerte/Vormerkungen ungültig: vor manueller Bereinigung prüfen"
    if errors:
        warnings.extend(errors)
    if not release_ready:
        warnings.append("Rückgabe eines Speichers wartet auf dessen Steuerbarkeit; anderer Speicher arbeitet weiter")
    reported_need = sum([bats[key]["need"] for key in BATTERY_KEYS])
    effective_limits = {
        key: limit if ((automatic_slot_active[key] and normal_live >= 200)
                       or manual_active_by_key[key]
                       or key in cal["charge"]) else 0
        for key, limit in limits.items()
    }

    plan = {
        "version": VERSION, "status": status, "berechnet_ts": NOW,
        "betriebsart": mode, "regelung_aktiv": automatic and records_ok,
        "daten_gueltig": live_valid and not data_errors and today["ok"],
        "datenfehler_aktuell": data_errors,
        "letzte_datenfehler": last_data_errors,
        "letzter_datenfehler_ts": last_data_error_ts,
        "prognose_intervalle_ok": today["ok"], "prognose_morgen_intervalle_ok": tomorrow["ok"],
        "prognose_heute_roh_kwh": round(raw_total, 3), "prognose_heute_erwartet_kwh": round(expected_total, 3),
        "prognose_rest_erwartet_kwh": round(expected_rest, 3),
        "prognose_korrektur_vertrauen": round(forecast_confidence, 3),
        "prognose_bis_jetzt_kwh": round(past_wh / 1000, 3), "pv_real_bis_jetzt_kwh": actual_today if daily_ok else None,
        "pv_prognose_abweichung_bisher_kwh": (
            round(actual_today - past_wh / 1000, 3) if daily_ok else None
        ),
        "pv_real_bis_jetzt_roh": raw(DAILY), "pv_real_bis_jetzt_einheit": "kWh",
        "pv_real_tageswert_plausibel": daily_ok, "prognose_jetzt_w": round(now_forecast),
        "pv_real_jetzt_roh": raw(PV), "pv_real_jetzt_w": pv,
        "pv_nacht_ersatzwert": pv_night_fallback,
        "pv_0w_gehalten": pv_held_zero,
        "pv_ac_status": pv_status,
        "pv_mppt_frisch": mppt_fresh, "pv_mppt_summe_dc_w": mppt_sum,
        "pv_mppt_werte_w": mppt_values,
        "pv_planungswert_w": round(pv_estimate) if pv_estimate is not None else None,
        "pv_planungswert_quelle": pv_estimate_source,
        "ueberschuss_untergrenze_w": balance_lower,
        "effizienzmodus": efficiency_mode,
        "sollwertstrategie": "Tagesfreigabe je Speicher; nach Start positive Ladegrenze halten",
        "bevorzugte_ladeleistung_a_w": BATTERIES["A"]["preferred"],
        "bevorzugte_ladeleistung_e_w": BATTERIES["E"]["preferred"],
        "maximale_ladeleistung_a_w": BATTERIES["A"]["maximum"],
        "maximale_ladeleistung_e_w": BATTERIES["E"]["maximum"],
        "maximale_entladeleistung_a_w": BATTERIES["A"].get("discharge_maximum", BATTERIES["A"]["maximum"]),
        "maximale_entladeleistung_e_w": BATTERIES["E"].get("discharge_maximum", BATTERIES["E"]["maximum"]),
        "prognose_tagesfaktor": round(day_factor, 3),
        "prognose_kurzfristfaktor": round(short_factor, 3), "prognose_qualitaetsfaktor": round(day_factor, 3),
        "prognose_effektivfaktor": round(short_factor * safety, 3), "prognose_rest_roh_kwh": round(raw_rest, 3),
        "pv_ladechance": pv_chance, "hausleistung_30_min_roh": raw(LOAD), "hausleistung_30_min_einheit": "W",
        "hausleistung_30_min_w": load, "hausleistung_aktuell_roh": raw(LIVE_LOAD),
        "hausleistung_aktuell_w": live_load,
        "ueberschuss_direkt_w": round(direct_surplus) if direct_surplus is not None else None,
        "ueberschuss_bilanz_w": round(balance_surplus) if balance_surplus is not None else None,
        "tagesklasse": category,
        "tagesklasse_kandidat": category_candidate,
        "tagesklasse_kandidat_seit_ts": category_candidate_since,
        "solarfenster_start_ts": solar_start, "solarfenster_ende_ts": solar_end,
        "sonnenhoechststand_ts": SOLAR_NOON,
        "mittagsfenster_start_ts": MIDDAY_START,
        "mittagsfenster_ende_ts": MIDDAY_END,
        "ladefenster_start_ts": start, "ladefenster_ende_ts": end,
        "ladefenster_dauer_h": round(max(0, end - start) / 3600, 2),
        "fenster_fortschritt_prozent": round(max(0, min(100, (NOW - start) / max(1, end - start) * 100)), 1),
        "fahrplan_basisleistung_w": sum(limits.values()),
        "max_ladeleistung_gesamt_w": sum(BATTERIES[key]["maximum"] for key in BATTERY_KEYS),
        "sicher_speicherbar_rest_kwh": round(safe_rest, 3),
        "sicher_speicherbar_fenster_rest_kwh": round(window_wh / 1000 * eta, 3),
        "deckungsfaktor": round(safe_rest / reported_need, 2) if reported_need > 0.001 else 99,
        "knapp": scarce, "gespeicherte_energie_kwh": round(stored, 4), "zielenergie_kwh": round(target_energy, 4),
        "netzeinspeisung_seit_ts": export_since,
        "morgenueberschuss_aktiv": rescue_morning,
        "morgenueberschuss_speicher": rescue_keys if rescue_morning else [],
        "restbedarf_kwh": round(reported_need, 4), "restbedarf_ac_kwh": round(reported_need / eta, 4),
        "fahrplanenergie_jetzt_kwh": round(stored - normal_stored + max(0, normal_target - window_wh / 1000 * eta), 3),
        "mindestenergie_jetzt_kwh": round(stored - normal_stored + min(normal_target, max(0, normal_target - window_wh / 1000 * eta)), 3),
        "energieluecke_kwh": round(normal_target - window_wh / 1000 * eta - normal_stored, 3),
        "soll_laden": sum(effective_limits.values()) > 0,
        "soll_ladeleistung_gesamt_w": sum(effective_limits.values()),
        "soll_ladegrenze_venus_a_w": limits.get("A", 0),
        "soll_ladegrenze_venus_e_w": limits.get("E", 0),
        "verteilungsmodus": (
            "geteilt" if sum(value > 0 for value in effective_limits.values()) > 1
            else next(("nur " + key for key, value in effective_limits.items() if value > 0), "aus")
        ),
        "manuell_aktiv": manual_active,
        "manuell_a_aktiv": manual_active_by_key.get("A", False),
        "manuell_e_aktiv": manual_active_by_key.get("E", False),
        "manuell_laden_a_w": manual_charge.get("A", 0),
        "manuell_entladen_a_w": manual_discharge.get("A", 0),
        "manuell_laden_e_w": manual_charge.get("E", 0),
        "manuell_entladen_e_w": manual_discharge.get("E", 0),
        "entscheidungsgrund": reason, "pv_vormittag_kwh": round(morning, 2), "pv_nachmittag_kwh": round(afternoon, 2),
        "prognose_morgen_kwh": round(sum([row["wh"] for row in tomorrow["rows"]]) / 1000, 2) if tomorrow["ok"] else None,
        "vorziehen_noetig": early, "fruehestens_voll_ts": normal_sim["finish"],
        "ziel_fehlmenge_simulation_kwh": round(normal_sim["missing"], 3),
        "warnungen": warnings, "prognose_fehler": today["errors"], "prognose_morgen_fehler": tomorrow["errors"],
        "packs_a_erwartet": pack_counts.get("A", 0),
        "packs_a_gueltig": len(bats.get("A", {}).get("packs", [])),
        "packs_a_soc": bats.get("A", {}).get("packs", []),
        "netto_ueberschuss_w": round(live_surplus),
    }
    plan["planungsmodus"] = "Tagesfreigabe je Speicher"
    plan["fahrplan_slot_start_ts"] = start
    plan["fahrplan_slot_ende_ts"] = end
    plan["fahrplan_entscheidung_fixiert_bis_ts"] = None
    plan["fahrplan_slot_verriegelt"] = False
    plan["fahrplan_slot_aktiv"] = any(automatic_slot_active.values())
    plan["fahrplan_slot_status"] = "Freigegeben" if any(automatic_slot_active.values()) else "Warten"
    for key in BATTERY_KEYS:
        name = key.lower()
        d = decisions.get(key, {})
        release_stamp = d.get("released_at", prior_attributes.get("ladefreigabe_venus_" + name + "_seit_ts"))
        if not automatic_slot_active[key]:
            release_stamp = prior_attributes.get("ladefreigabe_venus_" + name + "_seit_ts")
        plan["ladefreigabe_venus_" + name + "_seit_ts"] = (
            release_stamp if automatic and key not in cal_active_keys and not manual_active_by_key[key]
            and isinstance(release_stamp, (int, float)) and DAY0 <= release_stamp <= NOW else None
        )
        plan["ladebeginn_venus_" + name + "_ts"] = plan["ladefreigabe_venus_" + name + "_seit_ts"] or d.get("start")
        plan["voll_venus_" + name + "_ts"] = d.get("finish")
        plan["fahrplan_slot_aktiv_venus_" + name] = automatic_slot_active[key]
        plan["fahrplan_slot_grund_venus_" + name] = automatic_limit_reason[key]
        plan["fahrplan_slot_verriegelt_venus_" + name] = False
        stamp = plan["ladefreigabe_venus_" + name + "_seit_ts"]
        prior_stamp = prior_attributes.get("ladefreigabe_venus_" + name + "_seit_ts")
        old_origin = prior_attributes.get("ladefreigabe_venus_" + name + "_ursprung")
        origin = None
        if stamp is not None:
            if stamp == prior_stamp and old_origin:
                origin = old_origin
            elif stamp == NOW:
                origin = {"zeit_ts": stamp, "grund": automatic_limit_reason[key],
                          "tagesklasse": category, "soc_profil": early_profile,
                          "soc_ziel": early_soc_goals[key], "soc": bats[key]["soc"],
                          "kurzfristfaktor": short_factor, "tagesfaktor": day_factor}
            else:
                origin = {"zeit_ts": stamp, "grund": "Bestehende Freigabe übernommen; ursprünglicher Auslöser nicht aufgezeichnet"}
        plan["ladefreigabe_venus_" + name + "_ursprung"] = origin
        plan["fahrplan_slot_startgrund_venus_" + name] = origin["grund"] if origin else None
    for key in BATTERY_KEYS:
        name = key.lower()
        decision = {"zeit_ts": NOW, "bevorzugt_w": efficient_caps[key],
                    "roh_w": automatic_limits_raw[key], "stabil_w": automatic_limits[key],
                    "restbedarf_kwh": bats[key]["need"], "grund": automatic_limit_reason[key],
                    "fahrplan_status": automatic_status, "fahrplan_grund": automatic_reason,
                    "sollwert_grund": automatic_limit_reason[key],
                    "datenfehler": list(data_errors),
                    "live_ueberschuss_w": round(normal_live),
                    "fenster_start_ts": decisions.get(key, {}).get("start"), "simulation_ende_ts": simulation_end,
                    "fehlmenge_bevorzugt_kwh": round(decisions.get(key, {}).get("preferred_missing", 0), 4)}
        plan["leistungsentscheidung_venus_" + name] = decision
        plan["soc_venus_" + name] = bats[key]["soc"]
        plan["restbedarf_venus_" + name + "_kwh"] = round(bats[key]["need"], 4)
        plan["kapazitaet_venus_" + name + "_kwh"] = round(bats[key]["usable"], 4)
        plan["nennkapazitaet_venus_" + name + "_kwh"] = round(bats[key]["nominal"], 4)
        plan["untere_geraetegrenze_venus_" + name + "_prozent"] = bats[key]["floor"]
        plan["obere_geraetegrenze_venus_" + name + "_prozent"] = bats[key]["goal"]
        plan["ziel_venus_" + name + "_erreicht"] = bats[key]["target_met"]
        plan["ziel_venus_" + name + "_latch_soc"] = bats[key]["goal"]
        plan["ziel_venus_" + name + "_latch_grund"] = bats[key]["target_latch_reason"]
        plan["ziel_venus_" + name + "_latch_aktiv"] = (
            bats[key]["target_latch_reason"].startswith("Ziel gehalten")
        )
        plan["fahrplan_ladegrenze_roh_venus_" + name + "_w"] = automatic_limits_raw[key]
        plan["fahrplan_ladegrenze_stabil_venus_" + name + "_w"] = automatic_limits[key]
        plan["sollwert_venus_" + name + "_gehalten"] = automatic_limit_held[key]
        plan["sollwert_venus_" + name + "_grund"] = automatic_limit_reason[key]
        plan["auto_target_venus_" + name] = raw(BATTERIES[key]["auto"])
        plan["aktuelle_ladegrenze_venus_" + name + "_w"] = current_caps[key]
        plan["ac_leistung_venus_" + name + "_roh_w"] = bats[key]["power_display"]
        plan["ac_ladeleistung_venus_" + name + "_w"] = (charging_power(key, bats[key]["power_display"])
                                                           if bats[key]["power_display"] is not None else None)
        plan["ac_leistung_venus_" + name + "_0w_gehalten"] = bats[key]["power_held_zero"]
        plan["ac_leistung_venus_" + name + "_frisch"] = bats[key]["power_fresh"]
        plan["ac_leistung_venus_" + name + "_status"] = bats[key]["power_status"]
        plan["ac_leistung_venus_" + name + "_alter_min"] = (round(bats[key]["power_age_min"], 1)
                                                              if bats[key]["power_age_min"] is not None else None)
        plan["ac_rueckmeldung_venus_" + name] = reaction[key]
        plan["wechselrichter_status_venus_" + name] = bats[key]["inverter_status"]
        plan["wechselrichter_status_venus_" + name + "_frisch"] = bats[key]["inverter_fresh"]
        plan["ladeanforderung_venus_" + name + "_seit_ts"] = reaction[key]["requested_since"]
        plan["ladeleistung_venus_" + name + "_bestaetigt"] = reaction[key]["confirmed"]
        plan["ladereaktion_venus_" + name + "_gesperrt"] = reaction[key]["blocked"]
        plan["ladereaktion_venus_" + name + "_status"] = reaction[key]["status"]
        plan["kalibrier_leer_venus_" + name] = bats[key]["cal_empty_ready"]


    def bat_summary(key, bats, limits, session, cal_active, held, reaction, manual_active_by_key):
        b = bats[key]
        soc = b["soc"]
        soc_str = (str(round(soc, 1)) + " %") if soc is not None else "SoC ?"
        lw = limits.get(key, 0)
        own_session = next((s for s in (session, secondary) if s["b"] == key and s["p"] in ACTIVE_PHASES), None)
        if own_session is not None:
            lade_str = "Kalibrierung (" + own_session.get("p", "?") + ")"
        elif held.get(key):
            lade_str = "Gesperrt (Kalibrierung wartet)"
        elif manual_active_by_key.get(key, False) and lw > 0:
            lade_str = "Manuell " + str(lw) + " W"
        elif b.get("target_met"):
            lade_str = "Ziel erreicht"
        elif lw > 0:
            lade_str = "Laden " + str(lw) + " W"
        else:
            lade_str = "Wartet"
        react = reaction.get(key, {})
        conf_str = " v" if react.get("confirmed") else (" !" if key in [r for r in reaction if not reaction[r].get("confirmed") and reaction[r].get("requested_since")] else "")
        need_kwh = b.get("need", 0)
        need_str = (" - noch " + str(round(need_kwh, 2)) + " kWh") if need_kwh > 0.05 else ""
        return soc_str + " - " + lade_str + conf_str + need_str


    calibration = {"phase": session["p"], "batterie": session["b"],
        "phase_seit_ts": session["t"] or None,
        "grund": cal_reason, "grund_code": session["r"],
        "leistung_w": calibration_power,
        "energie_ac_kwh": round(session["w"] / 1000, 3), "start_ts": session["s"] or None,
        "ende_ts": session["x"] or None,
        "ruhedauer_unten_min": EMPTY_REST_SECONDS // 60,
        "ruhedauer_oben_min": FULL_REST_SECONDS // 60,
        "ruhe_verbleibend_s": (
            max(0, EMPTY_REST_SECONDS - (NOW - session["t"]))
            if session["p"] == "empty_rest"
            else max(0, FULL_REST_SECONDS - (NOW - (session["f"] or NOW)))
            if session["p"] in ["rest", "full_rest"]
            else 0
        ),
        "ladebeginn_voraussichtlich_ts": None if session["p"] in {"empty_rest", "wait"} else session["s"] or None,
        "peer_entladesperre_freigegeben": bool(
            session["p"] == "drain" and (session["h"] or session["v"])
        ),
        "peer_dauerfreigabe_14_prozent": bool(
            session["p"] == "drain" and session["h"]
        ),
        "peer_netzbezug_freigegeben": bool(
            session["p"] == "drain" and session["v"]
        ),
        "peer_netzbezug_seit_ts": (
            (session["l"] or None) if session["p"] == "drain" else None
        ),
        "peer_netzfrei_seit_ts": (
            (session["f"] or None) if session["p"] == "drain" else None
        ),
        "peer_freigabe_grund": (
            "Kalibrierspeicher hat 14 % erreicht"
            if session["p"] == "drain" and session["h"]
            else cal.get("peer_grid_reason", "")
        ),
        "netzleistung_w": round(grid) if grid is not None else None,
        "peer_freigabe_schwelle_prozent": 14,
        "hinweis": (
            "Prognose ist keine Garantie; "
            + str(calibration_power)
            + " W sind ein Limit."
        )}
    for key in BATTERY_KEYS:
        name = key.lower()
        calibration["kalibrieren_" + name + "_sicher"] = cal_safe[key]
        calibration[name + "_pruefhinweise"] = cal_errors[key]
        calibration["heute_" + name] = previews_today[key]
        calibration["morgen_" + name] = previews_tomorrow[key]
        calibration["dashboard_" + name] = bat_summary(
            key, bats, limits, session, cal_active, held, reaction,
            manual_active_by_key,
        )
        for index, entity_id in enumerate(DRIFTS[key], start=1):
            calibration[
                "drift_" + name + ("_p" + str(index) if len(DRIFTS[key]) > 1 else "") + "_mv"
            ] = measurement(entity_id, "delta", 600)

    output["plan"] = plan
    output["calibration"] = calibration
    output["session"] = encode_session(session)
    output["parallel_session"] = encode_session(secondary) if secondary["p"] in ACTIVE_PHASES else ""
    output["save_backup"] = save_backup
    output["clear_backup"] = clear_backup
    output["save_cal_backup"] = save_cal_backup
    output["clear_cal_backup"] = clear_cal_backup
    output["capture_drift"] = original_phase in ["rest", "full_rest"] and session["r"] == "success"
    output["commands"] = hardware_commands
    output["execute"] = can_execute
    output["finish"] = cal["finish"]
    output["finish_events"] = [
        {"battery": s["b"], "energy_kwh": round(s["w"] / 1000, 3),
         "capture_drift": previous in ["rest", "full_rest"] and s["r"] == "success"}
        for s, previous, outcome in ((session, original_phase, cal),
                                      (secondary, secondary_original_phase, secondary_cal))
        if outcome is not None and outcome["finish"] and s["b"] in BATTERY_KEYS
    ]

    reset_after_calibration = []
    for event in output["finish_events"]:
        key_cal = event["battery"].lower()
        reset_after_calibration.extend([
            "input_boolean.speicher_ladelogik_ae_kalibrierung_" + key_cal + "_freigegeben",
            "input_boolean.speicher_ladelogik_ae_kalibrierung_" + key_cal + "_laden_sperren",
        ])
    output["reset_after_calibration"] = reset_after_calibration
    notifications = ["Kalibrierung " + SLOT_NAMES.get(session["b"], session["b"]) + ": " + cal_reason] if cal["notify"] else []
    if secondary_cal and secondary_cal["notify"]:
        notifications.append("Kalibrierung " + SLOT_NAMES.get(secondary["b"], secondary["b"])
                             + ": " + reasons.get(secondary["r"], secondary["r"]))
    output["notify"] = "; ".join(notifications) if notifications else queue_notify
    output["ack"] = REQUEST == "ack"

    plan["daten_gueltig_gemeinsam"] = live_valid
    plan["ueberschuss_quelle"] = surplus_source
    plan["normaler_fahrplan_status"] = normal_status
    plan["normaler_fahrplan_grund"] = normal_reason
    plan["mittagsspitzen_aktiv"] = peak_enabled and peak["ok"]
    plan["mittagsspitzen_konfiguriert"] = peak_configured
    plan["mittagsspitzen_planbar"] = peak["ok"]
    plan["einspeiseziel_w"] = peak["target"] if peak["ok"] else None
    plan["mittagsspitze_live_freigabe_w"] = round(peak_live_headroom) if peak_live_override else 0
    plan["mittagsspitze_live_seit_ts"] = peak_live_since
    plan["spitzenfenster_start_ts"] = peak["start"]
    plan["spitzenfenster_ende_ts"] = peak["end"]
    plan["spitzenplan_voll_ts"] = peak["finish"]
    plan["kalibrier_reserviert_w"] = cal_draw
    plan["normaler_restbedarf_kwh"] = round(need, 4)
    plan["fruehe_soc_ziele_prozent"] = early_soc_goals
    plan["fruehes_soc_ziel_tagesklasse"] = early_profile
    plan["fruehes_soc_ziel_offen"] = early_soc_keys
    for key in BATTERY_KEYS:
        name = key.lower()
        plan["daten_gueltig_venus_" + name] = bats[key]["usable_data"] and not reaction[key]["blocked"]
        plan["schreibfehler_venus_" + name] = failure_counts[key]
        plan["fahrplan_ladegrenze_venus_" + name + "_w"] = normal_limits[key]
        plan["vorgemerkt_ladesperre_venus_" + name] = held[key]
        own_session = next((s for s in (session, secondary) if s["p"] in ACTIVE_PHASES and s["b"] == key), None)
        key_errors = [item for item in data_errors
                      if item.startswith(key + ":") or item.startswith("Venus " + key + ":")]
        if own_session:
            plan["status_venus_" + name] = "Kalibrierung: " + PHASE_LABELS.get(own_session["p"], own_session["p"])
            plan["grund_venus_" + name] = reason
        elif key_errors:
            plan["status_venus_" + name] = "Datenfehler"
            plan["grund_venus_" + name] = "; ".join(key_errors)
        elif manual_active_by_key[key]:
            plan["status_venus_" + name] = "Manuelle Grenze"
            plan["grund_venus_" + name] = (key + " Laden/Entladen " + str(manual_charge[key])
                                               + "/" + str(manual_discharge[key]) + " W")
        elif bats[key]["target_met"]:
            plan["status_venus_" + name] = "Ziel erreicht"
            plan["grund_venus_" + name] = "Geräteziel erreicht; Registerwert bleibt stehen"
        elif automatic_limit_held[key]:
            plan["status_venus_" + name] = "Sollwert gehalten"
            plan["grund_venus_" + name] = automatic_limit_reason[key]
        else:
            plan["status_venus_" + name] = automatic_status
            plan["grund_venus_" + name] = automatic_reason

    pending_items = []
    next_key = session["b"] if session["p"] == "requested" else ""
    next_day = session["n"] if next_key else None
    for key in BATTERY_KEYS:
        if key in queue:
            item = queue[key]
            pending_items.append({"batterie": key, "fruehestens_ts": item["n"],
                                  "nach_erfolg_von": item["d"], "laden_gesperrt": held[key]})
            if not next_key:
                next_key = key
                next_day = item["n"]
        current_request = next((s for s in (session, secondary) if s["b"] == key and s["p"] in ACTIVE_PHASES), None)
        active_request = current_request is not None
        calibration[key.lower() + "_vorgemerkt"] = key in queue or active_request
        calibration[key.lower() + "_fruehestens_ts"] = queue[key]["n"] if key in queue else (current_request["n"] if active_request else None)
        calibration[key.lower() + "_laden_gesperrt"] = held[key]
    jobs = []
    for current in (session, secondary):
        if current["p"] not in ACTIVE_PHASES or current["b"] not in BATTERY_KEYS:
            continue
        key = current["b"]
        rest_end = (current["t"] + EMPTY_REST_SECONDS if current["p"] == "empty_rest"
                    else current["f"] + FULL_REST_SECONDS if current["p"] == "full_rest" and current["f"] else None)
        preview = previews_tomorrow[key] if current["n"] >= DAY1 else previews_today[key]
        charge_start = None  # Live-Einspeisung, nicht die Prognose, bestimmt den Start.
        jobs.append({"batterie": key, "name": SLOT_NAMES[key], "phase": current["p"],
                     "phase_label": PHASE_LABELS.get(current["p"], current["p"]),
                     "grund": reasons.get(current["r"], current["r"]),
                     "energie_ac_kwh": round(current["w"] / 1000, 3),
                     "start_ts": current["s"] or None, "ende_ts": current["x"] or None,
                     "fruehestens_ts": current["n"] or None,
                     "unter_400_seit_ts": current["l"] or None if current["p"] == "charge" and current["h"] else None,
                     "ruhe_ende_ts": rest_end, "ruhe_verbleibend_s": max(0, rest_end - NOW) if rest_end else None,
                     "ladebeginn_voraussichtlich_ts": charge_start})
    calibration["laufende_laeufe"] = jobs.copy()
    for item in pending_items:
        key = item["batterie"]
        if any(job["batterie"] == key for job in jobs):
            continue
        dependency = SLOT_NAMES.get(item["nach_erfolg_von"])
        jobs.append({**item, "name": SLOT_NAMES[key], "phase": "queued", "phase_label": "Vorgemerkt",
                     "grund": "Wartet auf " + dependency if dependency else "Wartet auf Freigabe und 600 W gemessene Einspeisung"})
    calibration["auftraege"] = jobs
    plan["kalibrierauftraege"] = jobs
    if len(jobs) > 1:
        plan["status"] = "Kalibrierung: " + " / ".join(job["name"] for job in jobs)
    calibration["vormerkungen"] = pending_items
    calibration["naechste_batterie"] = next_key
    calibration["naechster_termin_ts"] = next_day
    calibration["fruehestens_ts"] = session["n"] or None
    calibration["lauf_unterbrochen"] = bool(session["i"])
    calibration["pausiert"] = session["p"] == "paused"
    calibration["fortsetzungsphase"] = session["u"]
    calibration["als_naechstes"] = "Als Nächstes: " + SLOT_NAMES.get(next_key, next_key) if next_key else "Kein Folgeauftrag"
    prior_calibration = hass.states.get("sensor.speicher_ladelogik_ae_kalibrierung")
    calibration["letzte_pause_grund"] = prior_calibration.attributes.get("letzte_pause_grund", "") if prior_calibration is not None else ""
    calibration["letzte_pause_ts"] = number(prior_calibration.attributes.get("letzte_pause_ts")) if prior_calibration is not None else None
    if session["p"] == "paused" and original_phase != "paused":
        calibration["letzte_pause_grund"] = cal_reason
        calibration["letzte_pause_ts"] = NOW
    for key in BATTERY_KEYS:
        suffix = key.lower()
        observed = learning["last_precharge_rest"].get(key, {})
        calibration[f"letzte_ruhe_vor_laden_s_{suffix}"] = observed.get("seconds")
        calibration[f"letzte_ruhe_vor_laden_ts_{suffix}"] = observed.get("timestamp")
    output["queue"] = encode_queue(queue) if records_ok else queue_value
    output["write_order"] = order
    output["failure_counts"] = failure_counts
    output["reaction_newly_blocked"] = reaction_newly_blocked
    output["reaction_resolved"] = reaction_resolved

    drifts = {}
    for key in BATTERY_KEYS:
        name = key.lower()
        drifts[key] = [
            calibration.get(
                "drift_" + name
                + ("_p" + str(index) if len(DRIFTS[key]) > 1 else "")
                + "_mv"
            )
            for index in range(1, len(DRIFTS[key]) + 1)
        ]
    journal_event = False
    for current, previous, outcome in ((session, original_phase, cal),
                                       (secondary, secondary_original_phase, secondary_cal)):
        if outcome is None or current["b"] not in BATTERY_KEYS:
            continue
        key = current["b"]
        active = learning["active_runs"].get(key, {})
        if current["p"] == "charge" and previous in ["wait", "requested", "empty_rest"]:
            active = {"battery": key, "start": NOW, "soc": bats[key]["soc"],
                      "usable_reference": bats[key]["usable"], "eta": eta, "drift": drifts[key]}
            learning["active_runs"][key] = active
        if current["p"] == "full_rest" and previous == "charge" and active.get("battery") == key:
            # Two samples at full SoC; their difference is a voltage trend,
            # never a claim that passive top balancing has succeeded.
            active["drift_top_start_mv"] = drifts[key]
        event = ((current["p"] == "paused" and previous != "paused") or
                 (current["p"] in ["done", "incomplete", "cancelled", "error"]
                  and previous in ACTIVE_PHASES))
        if not event:
            continue
        journal_event = True
        has_start = active.get("battery") == key and number(active.get("start")) is not None
        start_stamp = active["start"] if has_start else None
        sample = current["w"] / 1000
        start_soc = number(active.get("soc")) if has_start else None
        reference = number(active.get("usable_reference"), 0)
        sample_eta = number(active.get("eta"), eta)
        sample_ok = (outcome["finish"] and not current["i"] and has_start
                     and start_soc is not None and 0 <= start_soc <= 15
                     and abs(reference - bats[key]["usable"]) < 0.01
                     and 0.6 * reference <= sample * sample_eta <= 1.4 * reference)
        record = {"battery": key, "start": start_stamp, "end": NOW,
                  "duration_h": round((NOW - start_stamp) / 3600, 3) if has_start else None,
                  "result": current["p"], "reason": current["r"], "ac_kwh": round(sample, 4),
                  "drift_before_mv": active.get("drift", []) if has_start else [],
                  "drift_top_start_mv": active.get("drift_top_start_mv", []) if has_start else [],
                  "drift_after_mv": drifts[key], "learning_valid": sample_ok}
        learning["history"] = (learning["history"] + [record])[-20:]
        if sample_ok:
            old = learning["models"][key]
            old_count = int(number(old.get("count"), 0))
            if abs(number(old.get("usable_reference"), 0) - reference) >= 0.01:
                old_count = 0
            average = (0.75 * number(old.get("ac_kwh"), sample) + 0.25 * sample
                       if old_count else sample)
            learning["models"][key] = {"count": min(10000, old_count + 1), "ac_kwh": round(average, 4),
                "usable_estimate_kwh": round(average * sample_eta, 4), "eta_assumed": sample_eta,
                "usable_reference": reference, "updated_ts": NOW}
        if current["p"] != "paused":
            learning["active_runs"].pop(key, None)
    learning["active"] = learning["active_runs"].get(session["b"], {})
    output["learning"] = learning
    output["journal_event"] = journal_event
    output["proposed_commands"] = list(output.get("commands", []))
    output["commands"] = []
    output["execute"] = False
    return output


# Kept for compatibility with RC8 imports.  The integration itself uses the
# neutral function name above; this alias can be removed after the stable v1.
calculate_shadow_plan = calculate_plan
