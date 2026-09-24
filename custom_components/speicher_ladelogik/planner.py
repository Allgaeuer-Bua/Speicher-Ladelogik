"""Planner ported from the proven V1 Beta calculation script."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import persistence
from .stability import (
    calibration_available_surplus,
    calibration_required_seconds,
    confirmed_export,
    early_soc_candidates,
    peer_discharge_release,
    peer_grid_support,
    quarter_hour_window,
    stable_charge_limit,
    target_latch,
)
from .storage import (
    MODEL_REFERENCE_AC_KWH,
    MODEL_REFERENCE_AC_PER_MODULE_KWH,
)


def calculate_plan(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Calculate a plan without performing Home Assistant service calls."""
    # Speicher-Ladelogik V1.0 Beta 1 - 2026-09-14
    # HA built-in python_script: NO imports, NO service calls, NO register writes.
    # This file only reads states and returns a proposed plan to its YAML caller.
    # Hardware/BMS limits remain authoritative. See START_HIER.md.

    output = {}

    VERSION = "1.2.1"
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
        if key in {"A", "D", "E"}
    ] or ["A", "E"]
    MANUAL_ENABLED = {
        "A": "input_boolean.speicher_ladelogik_manuell_a_aktiv",
        "D": "input_boolean.speicher_ladelogik_manuell_d_aktiv",
        "E": "input_boolean.speicher_ladelogik_manuell_e_aktiv",
    }
    MANUAL_CHARGE = {
        "A": "input_number.speicher_ladelogik_manuell_laden_a_w",
        "D": "input_number.speicher_ladelogik_manuell_laden_d_w",
        "E": "input_number.speicher_ladelogik_manuell_laden_e_w",
    }
    MANUAL_DISCHARGE = {
        "A": "input_number.speicher_ladelogik_manuell_entladen_a_w",
        "D": "input_number.speicher_ladelogik_manuell_entladen_d_w",
        "E": "input_number.speicher_ladelogik_manuell_entladen_e_w",
    }

    # The proven planner keeps three compact internal slots. Since V1.1 their
    # physical model is independent from the slot, so A/A/E or D/D/D setups
    # use the same planning and persistence paths as the former A/D/E setup.
    SLOT_ENTITIES = {
        "A": {
            "soc": "sensor.marstek_venus_a_soc_batterie",
            "power": "sensor.marstek_venus_a_ac_leistung",
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
        "D": {
            "soc": "sensor.marstek_venus_d_soc",
            "power": "sensor.marstek_venus_d_ac_leistung",
            "charge": "number.marstek_venus_d_maximale_ladeleistung",
            "discharge": "number.marstek_venus_d_maximale_entladeleistung",
            "auto": "switch.astrameter_venus_d_auto_target",
            "active": "switch.astrameter_venus_d_active",
            "override": "input_boolean.venus_d_nicht_laden",
            "top": "number.marstek_venus_d_maximaler_soc",
            "bottom": "number.marstek_venus_d_minimaler_soc",
            "vmax": "sensor.marstek_venus_d_maximale_zellenspannung",
            "tmax": "sensor.marstek_venus_d_maximale_zellentemperatur",
            "tmin": "sensor.marstek_venus_d_minimale_zellentemperatur",
            "usable": "input_number.venus_d_verfugbare_kapazitat",
        },
    }
    MODEL_SPECS = {
        # AC reference values include conversion losses. A is measured with
        # two 2.08-kWh modules; D keeps the prior empirical 5.0-kWh value for
        # two 2.56-kWh modules until its first successful calibration.
        "A": {
            "charge_sign": -1, "usable_default": 3.6608, "floor": 12,
            "maximum": 1500, "tail": 500,
            "reference_ac_per_module": MODEL_REFERENCE_AC_PER_MODULE_KWH["A"],
            "preferred": 1100, "has_packs": True, "module_kwh": 2.08,
        },
        "D": {
            "charge_sign": -1, "usable_default": 4.5056, "floor": 12,
            "maximum": 2500, "tail": 1100,
            "reference_ac_per_module": MODEL_REFERENCE_AC_PER_MODULE_KWH["D"],
            "preferred": 1300, "has_packs": True, "module_kwh": 2.56,
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
        for key in ("A", "D", "E")
    }
    SLOT_NAMES = {
        key: str(
            data.get("slot_names", {}).get(key, f"Venus {SLOT_MODELS[key]}")
        )
        for key in ("A", "D", "E")
    }
    BATTERIES = {
        key: {**SLOT_ENTITIES[key], **MODEL_SPECS[SLOT_MODELS[key]], "model": SLOT_MODELS[key]}
        for key in ("A", "D", "E")
    }

    PACKS = {
        "A": [
            "sensor.marstek_venus_a_soc_batteriepack_1",
            "sensor.marstek_venus_a_soc_batteriepack_2",
        ],
        "D": [
            "sensor.marstek_venus_d_soc_batteriepack_1",
            "sensor.marstek_venus_d_soc_batteriepack_2",
        ],
        "E": [],
    }
    DRIFTS = {
        "A": ["sensor.venus_a_pack_1_zelldrift", "sensor.venus_a_pack_2_zelldrift"],
        "D": ["sensor.venus_d_pack_1_zelldrift", "sensor.venus_d_pack_2_zelldrift"],
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
    LEARNING_ID = "sensor.speicher_ladelogik_lernspeicher"
    SUN = "sun.sun"
    LOAD = "sensor.hausleistung_gesamt_30_min"
    LIVE_LOAD = "sensor.hausleistung_gesamt"
    DAILY = "sensor.pv_produktion_tag"
    SESSION_ID = "input_text.speicher_ladelogik_kalibrierung_sitzung"
    BACKUP_ID = "input_text.speicher_ladelogik_sicherung"
    CAL_BACKUP_ID = "input_text.speicher_ladelogik_kalibrierung_sicherung"
    QUEUE_ID = "input_text.speicher_ladelogik_kalibrierung_vormerkungen"
    EMPTY_REST_SECONDS = 90 * 60
    FULL_REST_SECONDS = 90 * 60
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
        "drain": "Entladen auf 13 %",
        "empty_rest": "Untere Ruhephase",
        "wait": "Wartet auf PV-Fenster",
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
        value = number(raw("input_number.speicher_ladelogik_" + name), default)
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


    def split_power(total, needs, caps, previous):
        total = int(max(0, total) // 50 * 50)
        caps = {key: int(max(0, caps[key]) // 50 * 50) for key in BATTERY_KEYS}
        limits = {key: 0 for key in BATTERY_KEYS}
        eligible = [key for key in BATTERY_KEYS if needs[key] > 0 and caps[key] >= 50]
        if not eligible or total < 50:
            return limits
        first = eligible[0]
        for key in eligible:
            if previous.get(key, 0) > 0 and total <= caps[key]:
                first = key
                break
            if needs[key] > needs[first]:
                first = key
        if total < 1600 and total <= caps[first]:
            limits[first] = total
            return limits
        remaining = total
        denominator = sum([needs[key] for key in eligible])
        for key in eligible:
            value = min(caps[key], int(total * needs[key] / denominator // 50) * 50)
            limits[key] = value
            remaining = remaining - value
        for key in eligible:
            extra = min(caps[key] - limits[key], remaining)
            limits[key] = limits[key] + extra
            remaining = remaining - extra
        return limits


    def simulate(rows, start, end, battery_data, caps, load, factor, eta, charge_after=None, export_target=0):
        remaining = {key: battery_data[key]["need"] for key in BATTERY_KEYS}
        finish = None
        for row in rows:
            begin = max(start, row["t"])
            stop = min(end, row["t"] + 900)
            if stop <= begin:
                continue
            surplus = row["wh"] * 4 * factor - load
            available = max(0, surplus - export_target)
            tick = begin
            while tick < stop:
                seconds = min(60, stop - tick)
                if surplus >= 0 and (charge_after is None or tick >= charge_after):
                    instantaneous = {}
                    for key in BATTERY_KEYS:
                        bat = battery_data[key]
                        tail_kwh = bat["nominal"] * max(0, bat["goal"] - 90) / 100
                        rate = caps[key]
                        if remaining[key] <= tail_kwh + 0.000001:
                            rate = min(rate, BATTERIES[key]["tail"])
                        instantaneous[key] = rate if remaining[key] > 0.00001 else 0
                    allocated = split_power(min(available, sum(instantaneous.values())), remaining, instantaneous, {})
                    for key in BATTERY_KEYS:
                        remaining[key] = max(0, remaining[key] - allocated[key] * seconds / 3600000 * eta)
                elif surplus < 0:
                    active = [key for key in BATTERY_KEYS if caps[key] > 0]
                    for key in active:
                        remaining[key] = min(battery_data[key]["target"], remaining[key] + (-surplus) * seconds / 3600000 / max(1, len(active)))
                tick = tick + seconds
                if sum(remaining.values()) <= 0.002:
                    finish = tick
                    break
            if finish is not None:
                break
        return {"finish": finish, "missing": sum(remaining.values())}


    def minimum_working_caps(rows, start, end, battery_data, preferred_caps,
                             hard_caps, load, eta, charge_after):
        """Find the lowest 50-W cap blend that still reaches the target."""
        preferred_result = simulate(
            rows, start, end, battery_data, preferred_caps, load, 1, eta,
            charge_after,
        )
        if preferred_result["finish"] is not None:
            return preferred_caps.copy(), preferred_result

        hard_result = simulate(
            rows, start, end, battery_data, hard_caps, load, 1, eta,
            charge_after,
        )
        if hard_result["finish"] is None:
            return hard_caps.copy(), hard_result

        low = 0.0
        high = 1.0
        best_caps = hard_caps.copy()
        best_result = hard_result
        for _iteration in range(7):
            fraction = (low + high) / 2
            candidate = {}
            for key in BATTERY_KEYS:
                span = max(0, hard_caps[key] - preferred_caps[key])
                value = preferred_caps[key] + span * fraction
                candidate[key] = min(
                    hard_caps[key],
                    int((value + 49) // 50) * 50,
                )
            result = simulate(
                rows, start, end, battery_data, candidate, load, 1, eta,
                charge_after,
            )
            if result["finish"] is not None:
                high = fraction
                best_caps = candidate
                best_result = result
            else:
                low = fraction
        return best_caps, best_result


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
        if session["p"] == "charge":
            session["i"] = 1
        transition(session, "paused", reason)


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
        # A running calibration lowers the measured live surplus by its own
        # own draw.  Judging the calibration from that already reduced value
        # caused the observed on/off feedback loop. Reconstruct the surplus
        # before the calibration load from its actual charging power.  The
        # waiting phase deliberately keeps using the unmodified value so a
        # calibration cannot start on energy supplied by the peer storage.
        running_charge = key in BATTERY_KEYS and (
            p == "charge" or (p == "paused" and s.get("u") == "charge")
        )
        actual_draw = (
            context["batteries"][key].get("charge_power")
            if key in BATTERY_KEYS else None
        )
        calibration_surplus = (
            context["shared_surplus"] if context.get("parallel")
            else calibration_available_surplus(
                context["live_surplus"], actual_draw, running=running_charge,
            )
        )
        required_start = calibration_power * context.get("parallel_factor", 1) + 100 * context.get("parallel_factor", 1)
        required_running = calibration_min_power * context.get("running_factor", 1)
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
            if resume == "charge" and s["x"] + 1800 <= NOW:
                transition(s, "restore", "retry_window")
            elif resume != "charge" or calibration_surplus >= required_start:
                transition(s, resume, "resumed")
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
            elif s["n"] <= DAY0 and not preview["ok"]:
                transition(s, "restore", "retry_window")
        elif p == "empty_rest":
            bat = context["batteries"][key]
            if not bat["cal_empty_ready"]:
                transition(s, "drain", "natural_discharge")
            elif NOW - s["t"] >= EMPTY_REST_SECONDS:
                preview = (
                    context["today"][key]
                    if s["n"] <= DAY0
                    else context["tomorrow"][key]
                )
                if preview["ok"] and preview["start"] >= s["n"]:
                    s["s"] = int(preview["start"])
                    s["x"] = int(preview["end"])
                    transition(s, "wait", "waiting_pv")
                else:
                    transition(s, "restore", "retry_window")
        elif p == "wait":
            preview = (
                context["today"][key]
                if s["n"] <= DAY0
                else context["tomorrow"][key]
            )
            if preview["ok"] and preview["start"] >= s["n"]:
                s["s"] = int(preview["start"])
                s["x"] = int(preview["end"])
            elif s["n"] <= DAY0:
                transition(s, "restore", "retry_window")
            if (
                s["p"] == "wait"
                and s["s"] <= NOW
                and s["n"] <= DAY0
                and preview["ok"]
                and calibration_surplus >= required_start
            ):
                if context["batteries"][key]["cal_empty_ready"]:
                    transition(s, "charge", "charging")
                    s["s"] = int(preview["start"])
                    s["x"] = int(preview["end"])
                    s["q"] = int(NOW)
                    s["v"] = 0
                    s["w"] = 0
                    s["h"] = 0
                    s["i"] = 0
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
                    if calibration_surplus < required_running:
                        pause_session(s, "pv_pause")
                    elif s["h"] and power is not None and power < calibration_min_power and not bat["all_full"]:
                        s["l"] = s["l"] or int(NOW)
                        if NOW - s["l"] >= 300:
                            if bat["lowest_soc"] >= 99:
                                transition(s, "restore", "full_unconfirmed")
                            else:
                                pause_session(s, "under_400w")
                    else:
                        s["l"] = 0
                if s["p"] == "charge" and s["x"] + 1800 <= NOW:
                    # The forecast window starts a calibration. It must not
                    # stop a nearly full battery while measured PV surplus is
                    # still sufficient, so extend it in quarter-hour steps.
                    if calibration_surplus >= required_running:
                        s["x"] = int(NOW + 900)
                        s["r"] = "window_extended_live_surplus"
                    else:
                        transition(s, "restore", "retry_window")
                if s["p"] == "charge" and NOW - s["t"] > 64800:
                    transition(s, "restore", "retry_window")
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
                result["retry"] = s["r"] in ["retry_empty", "retry_window", "restart", "interrupted_full"]
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


    def peak_plan(rows, end, battery_data, caps, load, eta, after):
        feasible = simulate(rows, NOW, end, battery_data, caps, load, 1, eta, after)
        if feasible["finish"] is None:
            return {"ok": False, "target": 0, "start": None, "end": None, "finish": None}
        lower = 0
        upper = max([max(0, row["wh"] * 4 - load) for row in rows] + [0])
        finish = feasible["finish"]
        for attempt in range(16):
            threshold = (lower + upper) / 2
            test = simulate(rows, NOW, end, battery_data, caps, load, 1, eta, after, threshold)
            if test["finish"] is not None:
                lower = threshold
                finish = test["finish"]
            else:
                upper = threshold
        threshold = int(lower // 50 * 50)
        active_rows = [row for row in rows if row["t"] + 900 > max(NOW, after)
                       and row["t"] < end and row["wh"] * 4 - load - threshold >= 50]
        return {"ok": True, "target": threshold, "start": max(NOW, after, active_rows[0]["t"]) if active_rows else None,
                "end": min(end, active_rows[-1]["t"] + 900) if active_rows else None, "finish": finish}


    def read_learning():
        state = hass.states.get(LEARNING_ID)
        saved = state.attributes if state is not None else {}
        result = {"active": {}, "active_runs": {}, "history": [], "models": {key: {} for key in BATTERY_KEYS}}
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
                model = saved.get("models", {}).get(key, {})
                if (0 < number(model.get("count"), 0) <= 10000 and 0 < number(model.get("ac_kwh"), 0) <= 30
                        and 0 < number(model.get("usable_reference"), 0) < 20):
                    result["models"][key] = model.copy()
        except (AttributeError, TypeError):
            return {"active": {}, "active_runs": {}, "history": [], "models": {key: {} for key in BATTERY_KEYS}}
        return result


    learning = read_learning()
    eta = setting("ladewirkungsgrad", 90, 75, 100) / 100
    safety = setting("prognose_sicherheit", 90, 50, 100) / 100
    extra = setting("unplanbare_reserve", 1, 0, 4)
    early_soc_goals = {
        key: setting("fruehes_ladeziel_" + key.lower() + "_soc", 0, 0, 100)
        for key in BATTERY_KEYS
    }
    weak = setting("schwacher_tag", 25, 5, 50)
    middle = max(weak + 1, setting("mittlerer_tag", 50, 20, 100))
    strong = max(middle + 1, setting("starker_tag", 85, 50, 200))
    pack_counts = {
        key: int(setting("venus_" + key.lower() + "_packs", 2, 1, 6))
        for key in BATTERY_KEYS if BATTERIES[key]["has_packs"]
    }
    mode = raw("input_select.speicher_ladelogik_betriebsart")
    automatic = mode == "Automatik" and raw("input_boolean.speicher_ladelogik_aktiv") == "on"

    supplied_prior_plan = data.get("prior_plan")
    prior_plan_state = hass.states.get("sensor.speicher_ladelogik_planung")
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
        failure_counts[key] = number(raw("input_number.speicher_ladelogik_schreibfehler_" + key.lower()),
                                     number(raw("input_number.speicher_ladelogik_schreibfehler"), 0))
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
            errors.append(key + ": Gerätegrenzen ungültig")
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
            errors.append(key + ": Kapazität ungültig")
            nominal = model_nominal
            usable = nominal * (1 - floor / 100)
        pack_count = pack_counts.get(key, 1)
        packs = []
        if cfg["has_packs"]:
            for entity in PACKS[key][:pack_count]:
                value = measurement(entity, "soc")
                if value is None:
                    warnings.append(entity + ": erwarteter Pack-Sensor fehlt")
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

        cal_empty_ready = (soc is not None and soc <= 13 and higher_soc is not None
                           and higher_soc <= 13.5)
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

        usable_data = (soc is not None and packs_ok and capacity_ok and limits_ok
                       and writable(cfg["charge"], 0) and writable(cfg["charge"], cap))
        if not usable_data:
            errors.append(key + ": Gesamt-/Pack-SoC oder Ladegrenze fehlt/ist ungueltig")
        values.update({"soc": soc, "power": power, "power_live": power_usable,
                       "power_display": power_display,
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
    day_factor = max(0.2, min(1, actual_today * 1000 / past_wh)) if daily_ok and past_wh >= 750 else 1
    short_factor = max(0.2, min(1, pv_estimate / now_forecast)) if pv_estimate is not None and now_forecast >= 1000 else 1

    rows = []
    for row in today["rows"]:
        horizon = max(0, min(1, (row["t"] - NOW) / 7200))
        factor = (short_factor * (1 - horizon) + day_factor * horizon) * safety
        rows.append({"t": row["t"], "wh": row["wh"] * factor})
    raw_total = sum([row["wh"] for row in today["rows"]]) / 1000
    raw_rest = max(0, raw_total - past_wh / 1000)
    expected_total = (actual_today if daily_ok else past_wh / 1000) + raw_rest * day_factor
    expected_rest = raw_rest * day_factor
    if expected_total <= weak:
        category = "schwach"
        preferred = DAY0
    elif expected_total < middle:
        category = "wechselhaft"
        preferred = NINE - 7200 * (middle - expected_total) / (middle - weak)
    elif expected_total < strong:
        category = "mittel"
        preferred = NINE + (ELEVEN - NINE) * (expected_total - middle) / (strong - middle)
    else:
        category = "stark"
        preferred = ELEVEN

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
        previews_today[key] = continuous_window(today["rows"], NOW, hours, load, min(day_factor, short_factor) * safety)
        previews_tomorrow[key] = continuous_window(tomorrow["rows"], DAY1, hours, load, safety)
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
        cal_armed[key] = raw("input_boolean.speicher_ladelogik_kalibrierung_" + key.lower() + "_freigegeben") == "on"

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

    if queue_value in ["unknown", "unavailable"] and raw("input_boolean.speicher_ladelogik_v1_beta_1_initialisiert") != "on":
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
            if current["p"] == "requested":
                current["n"] = not_before
                current["s"] = 0
                current["x"] = 0
                queue_notify = "Termin für " + SLOT_NAMES[key] + " aktualisiert."
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
    other_running = [s for s in (session, secondary) if s["p"] in {"charge", "paused"}
                     and (s["p"] == "charge" or s.get("u") == "charge")]
    shared_surplus = live_surplus + sum(max(0, bats[s["b"]]["charge_power"] or 0)
                                        for s in other_running if s["b"] in BATTERY_KEYS)
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
                entity = BATTERIES[key]["discharge" if field.startswith("D") else "charge"]
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
        held[key] = pending and raw("input_boolean.speicher_ladelogik_kalibrierung_" + key.lower() + "_laden_sperren") == "on"
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
    caps = {key: bats[key]["cap"] if bats[key]["owns"] and bats[key]["usable_data"] and failure_counts[key] < 3
            and not reaction_blocked_prior[key] and not bats[key]["target_met"]
            and key not in cal_active_keys and not held[key] else 0 for key in BATTERY_KEYS}
    needs = {key: bats[key]["need"] if caps[key] > 0 else 0 for key in BATTERY_KEYS}
    stored = sum([bats[key]["stored"] for key in BATTERY_KEYS])
    target_energy = sum([bats[key]["target"] for key in BATTERY_KEYS])
    normal_stored = sum([bats[key]["stored"] for key in BATTERY_KEYS if caps[key] > 0])
    normal_target = sum([bats[key]["target"] for key in BATTERY_KEYS if caps[key] > 0])
    early_soc_keys = early_soc_candidates(caps, bats, early_soc_goals)
    need = sum(needs.values())
    max_total = sum(caps.values())

    normal_rows = []
    for row in rows:
        cal_reservation = 0
        for current in (session, secondary):
            if current["b"] in cal_active_keys and current["p"] in ["wait", "charge", "paused"]:
                overlap = max(0, min(row["t"] + 900, current["x"] + 1800) - max(row["t"], current["s"]))
                cal_reservation += calibration_power * overlap / 3600
        normal_rows.append({"t": row["t"], "wh": max(0, row["wh"] - cal_reservation)})
    solar_rows = [row for row in rows if row["wh"] * 4 > load]
    solar_start = solar_rows[0]["t"] if solar_rows else None
    solar_end = solar_rows[-1]["t"] + 900 if solar_rows else None
    end = min(MIDDAY_END, solar_end) if solar_end is not None else MIDDAY_END
    if end <= NOW:
        end = solar_end if solar_end is not None else DAY1
    preferred = max(
        preferred,
        MIDDAY_START,
        solar_start if solar_start is not None else preferred,
    )
    simulation_bats = {}
    for key in BATTERY_KEYS:
        simulation_bats[key] = bats[key].copy()
        simulation_bats[key]["need"] = needs[key]
    simulation_end = max(NOW, end - 1800)
    preferred_sim = simulate(
        normal_rows, NOW, simulation_end, simulation_bats, caps, load, 1, eta,
        preferred,
    )
    start = preferred
    early = need > 0 and preferred_sim["finish"] is None
    if early:
        start = min(NOW, preferred)
    hard_caps = caps.copy()
    efficient_caps = {key: min(caps[key], BATTERIES[key]["preferred"]) for key in BATTERY_KEYS}
    caps, efficiency_sim = minimum_working_caps(
        normal_rows,
        NOW,
        simulation_end,
        simulation_bats,
        efficient_caps,
        hard_caps,
        load,
        eta,
        start,
    )
    if need <= 0 or caps == efficient_caps:
        efficiency_mode = (
            "Früher beginnen mit bevorzugter Leistung"
            if early else "Bevorzugte Leistung reicht aus"
        )
    elif efficiency_sim["finish"] is not None:
        efficiency_mode = "Dynamisch erforderliche Leistung"
    else:
        efficiency_mode = "Automatische Maximalleistung erforderlich"
    planned_caps = caps.copy()
    max_total = sum(caps.values())
    safe_rest = 0
    window_wh = 0
    current_opportunity = 0
    current_normal_surplus = 0
    morning = 0
    afternoon = 0
    for row in normal_rows:
        seconds = max(0, row["t"] + 900 - max(NOW, row["t"]))
        surplus = max(0, row["wh"] * 4 - load)
        opportunity = min(surplus, max_total)
        safe_rest = safe_rest + opportunity * seconds / 3600000 * eta
        win_seconds = max(0, min(end, row["t"] + 900) - max(NOW, start, row["t"]))
        window_wh = window_wh + opportunity * win_seconds / 3600
        if row["t"] <= NOW < row["t"] + 900:
            current_opportunity = opportunity
            current_normal_surplus = surplus
    for row in rows:
        if row["t"] < NINE + 10800:
            morning = morning + row["wh"] / 1000
        else:
            afternoon = afternoon + row["wh"] / 1000
    safe_rest = max(0, safe_rest - extra)
    was_scarce = prior_attributes.get("knapp") is True
    scarce_threshold = need * setting("knappheitsreserve", 125, 100, 200) / 100
    if was_scarce:
        scarce_threshold = scarce_threshold + setting("hysterese", 0.2, 0.05, 1)
    scarce = pv_chance and (expected_total <= weak or safe_rest < scarce_threshold)

    if caps != hard_caps and scarce and expected_total > weak:
        hard_safe = max(0, sum([min(max(0, row["wh"] * 4 - load), sum(hard_caps.values()))
                        * max(0, row["t"] + 900 - max(NOW, row["t"])) / 3600000 * eta
                        for row in normal_rows]) - extra)
        scarce = hard_safe < scarce_threshold
    reason = "Kein aktueller PV-Überschuss"
    status = "Keine PV-Ladechance"
    total = 0
    peak = {"ok": False, "target": 0, "start": None, "end": None, "finish": None}
    peak_enabled = raw("input_boolean.speicher_ladelogik_mittagsspitzen") != "off"
    cal_draw = calibration_power * sum(s["p"] == "charge" for s in (session, secondary))
    normal_live = max(0, live_surplus - cal_draw)
    export_confirmed, export_since = confirmed_export(
        now_ts=NOW, grid_power_w=grid, live_surplus_w=normal_live,
        prior_since_ts=number(prior_attributes.get("netzeinspeisung_seit_ts")),
    )
    # Prefer actual morning energy over a predicted afternoon on uncertain
    # days. Leave capacity above the early target for the noon peak. Without
    # a configured target, stop this automatic rescue at 80 % per device.
    rescue_keys = [
        key for key in BATTERY_KEYS
        if caps[key] > 0 and bats[key]["lowest_soc"] is not None
        and bats[key]["lowest_soc"] < min(
            bats[key]["goal"], early_soc_goals[key] or 80,
        )
    ]
    rescue_morning = (
        export_confirmed and NOW < MIDDAY_END and bool(rescue_keys)
        and (category != "stark" or short_factor < 0.7)
    )
    if not live_valid:
        reason = "Keine verlässliche Live-Überschusserkennung"
        status = "Datenfehler"
    elif need <= 0:
        status = "Ziel erreicht" if all([bats[key]["target_met"] for key in BATTERY_KEYS]) else "Speicher einzeln gesperrt / vorgemerkt"
        reason = "Kein Restbedarf in den aktuell für den Fahrplan freigegebenen Speichern"
    elif pv_chance:
        if early_soc_keys:
            # Charge batteries below their own early goal before deferring
            # energy to the noon window. Other batteries resume the ordinary
            # schedule as soon as every early goal is reached.
            caps = {
                key: hard_caps[key] if key in early_soc_keys else 0
                for key in BATTERY_KEYS
            }
            max_total = sum(caps.values())
            start = min(start, NOW)
            total = max_total
            status = "Frühes SoC-Ziel"
            reason = "PV-Überschuss zuerst für Venus " + "/".join(early_soc_keys)
            efficiency_mode = "Frühes SoC-Ziel je Speicher"
        elif not today["ok"]:
            caps = hard_caps
            max_total = sum(caps.values())
            efficiency_mode = "Prognose-Fallback"
            total = max_total
            status = "PV-Fallback"
            reason = "Prognose ungültig; AstraMeter darf realen Überschuss aufnehmen"
        elif rescue_morning:
            caps = {key: hard_caps[key] if key in rescue_keys else 0 for key in BATTERY_KEYS}
            max_total = sum(caps.values())
            start = min(start, NOW)
            efficiency_mode = "Gemessenen Morgenüberschuss nutzen"
            total = max_total
            status = "Morgenüberschuss nutzen"
            reason = "Netzeinspeisung seit mindestens 3 Minuten; reale Ladung hat Vorrang vor späterer PV-Prognose"
        elif scarce:
            caps = hard_caps
            max_total = sum(caps.values())
            start = min(start, NOW)
            efficiency_mode = "Reserve sichern; Ladeziel hat Vorrang"
            total = max_total
            status = "Sichern"
            reason = "Knappheit; vorhandenen Überschuss mit Vorrang sichern"
        else:
            if peak_enabled and not early and end - 1800 > NOW:
                peak = peak_plan(normal_rows, end - 1800, simulation_bats, caps, load, eta, preferred)
            if peak["ok"]:
                total = min(max(0, normal_live - peak["target"]), max(0, current_normal_surplus - peak["target"])) if preferred <= NOW else 0
                start = peak["start"] if peak["start"] is not None else preferred
                status = "Mittagsspitzen reduzieren" if total >= 50 else "Platz für Mittagsspitze halten"
                reason = "Ladung auf die höchsten prognostizierten Überschüsse konzentriert; Ladeziel und Endphase eingeplant"
            elif start <= NOW:
                quota_wh = need / eta * 1000
                total = current_opportunity * min(1, quota_wh / max(1, window_wh))
                if early:
                    total = max(total, min(max_total, need / eta * 1000 / max(0.25, (end - NOW) / 3600)))
                if NOW >= end:
                    total = max_total
                if total > 25:
                    total = max(total, min(max_total, setting("min_effiziente_leistung", 800, 0, 1500)))
                status = "Vorladen" if early and preferred > NOW else "Fahrplanladen"
                if efficiency_mode == "Dynamisch erforderliche Leistung":
                    reason = "Bevorzugte Leistung reicht zeitlich nicht; dynamisch geplant: " + ", ".join(
                        SLOT_NAMES[key] + " " + str(caps[key]) + " W"
                        for key in BATTERY_KEYS if caps[key] > 0
                    )
                elif efficiency_mode == "Automatische Maximalleistung erforderlich":
                    reason = "Ladeziel ist selbst mit den automatischen Maximalgrenzen knapp"
                elif early and preferred > NOW:
                    reason = "Spätere Ertragsfenster reichen nicht; Ladebeginn vorgezogen"
                else:
                    reason = "Bevorzugte Ladeleistung reicht bis zum dynamischen Fensterende"
            else:
                status = "Zurückhalten"
                reason = "Spätere PV-Fenster decken Restbedarf einschließlich Lade-Endphase"

    # ── Stabile Fahrplan-Grenzen und manuelle Grenzen je Speicher ───────────────
    # Die Prognose entscheidet weiterhin ueber Start, Ende und Leistungsstufe.
    # Waehrend einer normalen Ladephase wird je Speicher aber ein fester Grenzwert
    # gesetzt und gehalten; die Feinregelung am Netzanschlusspunkt macht AstraMeter.
    automatic_status = status
    automatic_reason = reason
    # Oberhalb von 90 % reduziert das Gerät seine reale Aufnahme selbst. Die
    # Planung modelliert diese Endphase, schreibt deswegen aber keinen kleineren
    # Registerwert und erzeugt so keine unnötigen Schreibzyklen.
    dispatch_caps = caps.copy()
    if cal_draw:
        total = min(total, max(0, live_surplus - cal_draw - 100))
        if any(
            bats[s["b"]]["charge_power"] < calibration_min_power
            and not bats[s["b"]]["all_full"]
            for s in (session, secondary) if s["p"] == "charge"
        ):
            total = 0
            automatic_reason = (
                "Kalibrierladung erhält zuerst "
                + str(calibration_power)
                + " W; danach gilt der normale Fahrplan für den Rest"
            )

    if total >= 50:
        if cal_draw:
            # Nur waehrend einer Kalibrierung wird der Rest dynamisch begrenzt,
            # damit deren eingestellte Leistung sicher Vorrang behält.
            limits = split_power(min(max_total, total), needs, dispatch_caps, {})
        else:
            limits = {key: dispatch_caps[key] if needs[key] > 0 else 0
                      for key in BATTERY_KEYS}
    else:
        limits = {key: 0 for key in BATTERY_KEYS}
    automatic_limits_raw = limits.copy()
    automatic_limits = {}
    automatic_limit_held = {}
    automatic_limit_reason = {}
    slot_start_ts, slot_end_ts = quarter_hour_window(NOW)
    prior_slot_start_ts = number(prior_attributes.get("fahrplan_slot_start_ts"))
    prior_automatic = (
        prior_attributes.get("betriebsart") == "Automatik"
        and flag(prior_attributes.get("regelung_aktiv", False))
    )
    prior_peak_enabled = prior_attributes.get("mittagsspitzen_aktiv")
    peak_setting_unchanged = (
        prior_peak_enabled is None or flag(prior_peak_enabled) == peak_enabled
    )
    prior_early_goals = prior_attributes.get("fruehe_soc_ziele_prozent")
    prior_early_keys = prior_attributes.get("fruehes_soc_ziel_offen")
    early_goals_unchanged = (
        not isinstance(prior_early_goals, dict)
        or all(number(prior_early_goals.get(key), 0) == goal
               for key, goal in early_soc_goals.items())
    )
    midday_window_unchanged = (
        number(prior_attributes.get("sonnenhoechststand_ts"), SOLAR_NOON)
        == SOLAR_NOON
        and number(prior_attributes.get("mittagsfenster_start_ts"), MIDDAY_START)
        == MIDDAY_START
        and number(prior_attributes.get("mittagsfenster_ende_ts"), MIDDAY_END)
        == MIDDAY_END
    )
    decision_slot_locked = (
        prior_slot_start_ts is not None
        and int(prior_slot_start_ts) == slot_start_ts
        and prior_automatic
        and peak_setting_unchanged
        and early_goals_unchanged
        and not rescue_morning
        and midday_window_unchanged
        and (not isinstance(prior_early_keys, list) or prior_early_keys == early_soc_keys)
    )
    within_charge_window = start <= NOW < end
    for key in BATTERY_KEYS:
        name = key.lower()
        previous_limit = number(
            prior_attributes.get(
                "fahrplan_ladegrenze_stabil_venus_" + name + "_w"
            ),
            0,
        )
        eligible = caps[key] > 0 and key not in cal_active_keys and not held[key]
        safety_stop = (
            not automatic
            or not records_ok
            or not live_valid
            or not bats[key]["usable_data"]
            or not bats[key]["owns"]
            or failure_counts[key] >= 3
        )
        stable_limit, limit_held, limit_reason = stable_charge_limit(
            raw_limit=automatic_limits_raw[key],
            previous_limit=previous_limit,
            current_cap=BATTERIES[key]["maximum"],
            eligible=eligible,
            target_reached=bats[key]["target_met"],
            within_window=within_charge_window,
            planner_status=automatic_status,
            safety_stop=safety_stop,
            decision_locked=decision_slot_locked,
            slot_was_active=flag(
                prior_attributes.get(
                    "fahrplan_slot_aktiv_venus_" + name,
                    False,
                )
            ),
        )
        automatic_limits[key] = stable_limit
        automatic_limit_held[key] = limit_held
        automatic_limit_reason[key] = limit_reason
    limits = automatic_limits.copy()
    automatic_slot_active = {
        key: automatic_limits[key] > 0
        for key in BATTERY_KEYS
    }

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
        if sum(automatic_limits_raw.values()) == 0 and sum(automatic_limits.values()) > 0:
            status = "Sollwert wird gehalten"
            reason = "Grenzwert bleibt gesetzt; AstraMeter begrenzt die reale Leistung am Netzanschlusspunkt"

    reaction = {}
    reaction_newly_blocked = []
    for key in BATTERY_KEYS:
        name = key.lower()
        prior_limit = number(prior_attributes.get("soll_ladegrenze_venus_" + name + "_w"), 0)
        prior_since = number(prior_attributes.get("ladeanforderung_venus_" + name + "_seit_ts"))
        prior_confirmed = flag(prior_attributes.get("ladeleistung_venus_" + name + "_bestaetigt", False))
        blocked = reaction_blocked_prior[key]
        requested = (
            limits[key] > 0
            and key not in cal["charge"]
            and (
                manual_active_by_key[key]
                or automatic_limits_raw[key] > 0
            )
        )
        since = None
        confirmed = False
        status_text = "aus"
        if blocked:
            limits[key] = 0
            status_text = "gesperrt; Fehler quittieren"
        elif requested:
            continuing = prior_limit > 0 and prior_since is not None
            since = prior_since if continuing else NOW
            confirmed = (prior_confirmed if continuing else False) or (
                bats[key]["power_fresh"] and bats[key]["charge_power"] is not None
                and bats[key]["charge_power"] >= 25)
            if confirmed:
                status_text = "bestätigt"
            elif NOW - since >= 180:
                status_text = "nicht bestätigt – Hinweis (AstraMeter aktiv)"
                reaction_newly_blocked.append(key)
            else:
                status_text = "wartet auf frische Ladeleistung"
        reaction[key] = {"requested_since": since, "confirmed": confirmed,
                         "blocked": blocked, "status": status_text}
        if key in reaction_newly_blocked:
            message = SLOT_NAMES[key] + ": Ladeleistung nach Freigabe nicht bestätigt (Hinweis)"
            if message not in warnings:
                warnings.append(message)

    reaction_blocked_keys = [key for key in BATTERY_KEYS if reaction[key]["blocked"]]

    if data_errors:
        last_data_errors = data_errors
        last_data_error_ts = NOW
    normal_limits = automatic_limits.copy()
    normal_status = automatic_status
    normal_reason = automatic_reason
    normal_sim = simulate(normal_rows, NOW, end, simulation_bats, caps, load, 1, eta, start)

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
            entity = BATTERIES[key]["discharge" if field.startswith("D") else "charge"]
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
                        and write_needed(current_caps[key], limits[key])) or (key_restoring and all([field.startswith("D") for field in restoring_fields])
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

    reasons = {"requested": "Auftrag gespeichert; geeignetes PV-Fenster wird gesucht",
        "scheduled": "Termin vorgemerkt; Vorbereitung beginnt abends bei geringer PV",
        "no_window": "Auftrag bleibt vorgemerkt; heute/morgen kein ausreichend langes PV-Fenster",
        "waiting_data": "Auftrag bleibt vorgemerkt; erforderliche eigene Daten fehlen",
        "waiting_pv": "Leer vorbereitet; wartet auf vorgesehenes PV-Fenster",
        "natural_discharge": "Vorbereitung durch Hausverbrauch; keine erzwungene Einspeisung",
        "charging": str(calibration_power) + "-W-Limit; tatsächliche Ladeleistung wird überwacht",
        "empty_resting": "13 % erreicht; 90 Minuten untere Ruhephase",
        "resting": "Alle erwarteten SoCs bei 100 %; obere Ruhephase",
        "full_resting": "100 % bestätigt; 90 Minuten obere Ruhephase für das BMS",
        "success": "100 % und 90 Minuten obere Ruhephase bestätigt; eigene Grenzwerte zurückgegeben",
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
        status = "Kalibrierung " + session["b"] + ": " + session["p"]
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
        "prognose_bis_jetzt_kwh": round(past_wh / 1000, 3), "pv_real_bis_jetzt_kwh": actual_today if daily_ok else None,
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
        "sollwertstrategie": "Zustandsbasierte Grenzwerte; schreiben nur bei wirklicher Änderung",
        "bevorzugte_ladeleistung_a_w": BATTERIES["A"]["preferred"],
        "bevorzugte_ladeleistung_d_w": BATTERIES["D"]["preferred"],
        "bevorzugte_ladeleistung_e_w": BATTERIES["E"]["preferred"],
        "maximale_ladeleistung_a_w": BATTERIES["A"]["maximum"],
        "maximale_ladeleistung_d_w": BATTERIES["D"]["maximum"],
        "maximale_ladeleistung_e_w": BATTERIES["E"]["maximum"],
        "maximale_entladeleistung_a_w": BATTERIES["A"].get("discharge_maximum", BATTERIES["A"]["maximum"]),
        "maximale_entladeleistung_d_w": BATTERIES["D"].get("discharge_maximum", BATTERIES["D"]["maximum"]),
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
        "soll_laden": sum(limits.values()) > 0, "soll_ladeleistung_gesamt_w": sum(limits.values()),
        "soll_ladegrenze_venus_a_w": limits.get("A", 0),
        "soll_ladegrenze_venus_d_w": limits.get("D", 0),
        "soll_ladegrenze_venus_e_w": limits.get("E", 0),
        "verteilungsmodus": (
            "geteilt" if sum(value > 0 for value in limits.values()) > 1
            else next(("nur " + key for key, value in limits.items() if value > 0), "aus")
        ),
        "manuell_aktiv": manual_active,
        "manuell_a_aktiv": manual_active_by_key.get("A", False),
        "manuell_d_aktiv": manual_active_by_key.get("D", False),
        "manuell_e_aktiv": manual_active_by_key.get("E", False),
        "manuell_laden_a_w": manual_charge.get("A", 0),
        "manuell_entladen_a_w": manual_discharge.get("A", 0),
        "manuell_laden_d_w": manual_charge.get("D", 0),
        "manuell_entladen_d_w": manual_discharge.get("D", 0),
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
        "packs_d_erwartet": pack_counts.get("D", 0),
        "packs_d_gueltig": len(bats.get("D", {}).get("packs", [])),
        "packs_d_soc": bats.get("D", {}).get("packs", []),
        "netto_ueberschuss_w": round(live_surplus),
    }
    plan["fahrplan_slot_start_ts"] = slot_start_ts
    plan["fahrplan_slot_ende_ts"] = slot_end_ts
    plan["fahrplan_entscheidung_fixiert_bis_ts"] = (
        slot_end_ts if automatic else None
    )
    plan["fahrplan_slot_verriegelt"] = automatic and decision_slot_locked
    plan["fahrplan_slot_aktiv"] = any(automatic_slot_active.values())
    plan["fahrplan_slot_status"] = (
        "Beobachten"
        if not automatic
        else ("Laden" if any(automatic_slot_active.values()) else "Pause")
    )
    for key in BATTERY_KEYS:
        name = key.lower()
        plan["fahrplan_slot_aktiv_venus_" + name] = automatic_slot_active[key]
        plan["fahrplan_slot_grund_venus_" + name] = automatic_limit_reason[key]
    for key in BATTERY_KEYS:
        name = key.lower()
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
        elif lw > 0:
            lade_str = "Laden " + str(lw) + " W"
        elif b.get("target_met"):
            lade_str = "Ziel erreicht"
        else:
            lade_str = "Wartet"
        react = reaction.get(key, {})
        conf_str = " v" if react.get("confirmed") else (" !" if key in [r for r in reaction if not reaction[r].get("confirmed") and reaction[r].get("requested_since")] else "")
        need_kwh = b.get("need", 0)
        need_str = (" - noch " + str(round(need_kwh, 2)) + " kWh") if need_kwh > 0.05 else ""
        return soc_str + " - " + lade_str + conf_str + need_str


    calibration = {"phase": session["p"], "batterie": session["b"],
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
            "input_boolean.speicher_ladelogik_kalibrierung_" + key_cal + "_freigegeben",
            "input_boolean.speicher_ladelogik_kalibrierung_" + key_cal + "_laden_sperren",
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
    plan["mittagsspitzen_aktiv"] = peak_enabled
    plan["mittagsspitzen_planbar"] = peak["ok"]
    plan["einspeiseziel_w"] = peak["target"] if peak["ok"] else None
    plan["spitzenfenster_start_ts"] = peak["start"]
    plan["spitzenfenster_ende_ts"] = peak["end"]
    plan["spitzenplan_voll_ts"] = peak["finish"]
    plan["kalibrier_reserviert_w"] = cal_draw
    plan["normaler_restbedarf_kwh"] = round(need, 4)
    plan["fruehe_soc_ziele_prozent"] = early_soc_goals
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
    calibration["laufende_laeufe"] = [
        {"batterie": s["b"], "phase": s["p"], "energie_ac_kwh": round(s["w"] / 1000, 3),
         "start_ts": s["s"] or None, "ende_ts": s["x"] or None}
        for s in (session, secondary) if s["p"] in ACTIVE_PHASES
    ]
    calibration["vormerkungen"] = pending_items
    calibration["naechste_batterie"] = next_key
    calibration["naechster_termin_ts"] = next_day
    calibration["fruehestens_ts"] = session["n"] or None
    calibration["lauf_unterbrochen"] = bool(session["i"])
    calibration["pausiert"] = session["p"] == "paused"
    calibration["fortsetzungsphase"] = session["u"]
    calibration["als_naechstes"] = "Als Nächstes: Venus " + next_key if next_key else "Kein Folgeauftrag"
    prior_calibration = hass.states.get("sensor.speicher_ladelogik_kalibrierung_planung")
    calibration["letzte_pause_grund"] = prior_calibration.attributes.get("letzte_pause_grund", "") if prior_calibration is not None else ""
    calibration["letzte_pause_ts"] = number(prior_calibration.attributes.get("letzte_pause_ts")) if prior_calibration is not None else None
    if session["p"] == "paused" and original_phase != "paused":
        calibration["letzte_pause_grund"] = cal_reason
        calibration["letzte_pause_ts"] = NOW
    output["queue"] = encode_queue(queue) if records_ok else queue_value
    output["write_order"] = order
    output["failure_counts"] = failure_counts
    output["reaction_newly_blocked"] = reaction_newly_blocked

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
        if current["p"] == "charge" and previous in ["wait", "requested"]:
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
