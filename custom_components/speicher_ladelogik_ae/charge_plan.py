"""One daily charging decision per storage, with a shared PV energy budget.

Forecasts determine when to release each storage. Once released, the register
stays usable for the rest of that day. AstraMeter controls the actual power.
"""

from __future__ import annotations

from math import ceil
from typing import Any

EPS_KWH = 0.002


def surplus_segments(rows, now, end, load, cloud_reserve):
    """Deduct the cloud reserve once, from the end of the remaining AC surplus."""
    segments = []
    for row in rows:
        begin, stop = max(now, row["t"]), min(end, row["t"] + 900)
        if stop > begin:
            segments.append([begin, stop, row["wh"] * 4 - load])
    reserve_wh = max(0, cloud_reserve) * 1000
    for segment in reversed(segments):
        hours = (segment[1] - segment[0]) / 3600
        removed = min(reserve_wh, max(0, segment[2]) * hours)
        segment[2] -= removed / hours
        reserve_wh -= removed
    return segments


def simulate(segments, batteries, needs, caps, starts, efficiency, end):
    """Allocate the PV once across eligible storages and model their end phase."""
    remaining = needs.copy()
    finishes = {key: None for key in needs}
    required = {key for key, value in needs.items() if value > EPS_KWH}
    peak_export = 0.0
    for begin, stop, available in segments:
        stop = min(stop, end)
        tick = begin
        while tick < stop:
            # Land exactly on a planned release, including a partial bucket.
            next_starts = [start for start in starts.values() if tick < start < stop]
            seconds = min(60, stop - tick, min(next_starts, default=stop) - tick)
            if available < 0:
                # House demand during forecast PV gaps uses stored energy even
                # before charging starts. Estimate the shared discharge within
                # each device's lower SoC and discharge-power boundaries.
                discharge = {}
                for key, bat in batteries.items():
                    usable = bat.get("target", bat["nominal"] * (bat["goal"] - bat.get("floor", 12)) / 100)
                    stored = max(0, usable - remaining[key])
                    discharge[key] = min(bat.get("discharge_maximum", bat["maximum"]),
                                         stored * 3600000 / seconds)
                factor = min(1, -available / max(1, sum(discharge.values())))
                for key, rate in discharge.items():
                    if rate * factor > 0:
                        remaining[key] += rate * factor * seconds / 3600000
                        finishes[key] = None
                        required.add(key)
                tick += seconds
                continue
            rates = {}
            for key, bat in batteries.items():
                tail_kwh = bat["nominal"] * max(0, bat["goal"] - 90) / 100
                rate = caps[key]
                if remaining[key] <= tail_kwh + EPS_KWH:
                    rate = min(rate, bat["tail"])
                rates[key] = (
                    min(rate, remaining[key] * 3600000 / seconds / efficiency)
                    if starts[key] <= tick and remaining[key] > EPS_KWH else 0
                )
            factor = min(1, available / max(1, sum(rates.values())))
            peak_export = max(peak_export, available - sum(rates.values()) * factor)
            for key, rate in rates.items():
                remaining[key] = max(0, remaining[key] - rate * factor * seconds * efficiency / 3600000)
                if remaining[key] <= EPS_KWH and key in required and finishes[key] is None:
                    finishes[key] = tick + seconds
            tick += seconds
    finish = (
        max((finishes[key] for key in required), default=None)
        if all(finishes[key] is not None for key in required) else None
    )
    return {"missing_by_key": remaining, "missing": sum(remaining.values()),
            "finish": finish, "finishes": finishes, "peak_export": peak_export}


def daily_plan(*, now: float, day: float, end: float, midday_start: float,
               midday_end: float, preferred_start: float, category: str,
               peak_enabled: bool, forecast_ok: bool, live_surplus: float,
               pv_chance: bool, rows: list, load: float, efficiency: float,
               cloud_reserve: float, reserve_factor: float, hysteresis: float,
               batteries: dict[str, dict[str, Any]], prior: dict[str, Any]) -> dict:
    """Plan each battery's release and cap; return decisions without side effects.

    `batteries` contains only automatic, valid and unreserved storages. The
    caller retains responsibility for manual limits, calibration and safety.
    """
    pv_chance = pv_chance and live_surplus >= 200
    keys = list(batteries)
    needs = {key: bat["need"] for key, bat in batteries.items()}
    caps = {key: min(bat["maximum"], bat["preferred"]) for key, bat in batteries.items()}
    released, release_ts, near_full = {}, {}, {}
    for key, bat in batteries.items():
        name = key.lower()
        near_full[key] = bat["soc"] >= bat["goal"] - 1 and bat["lowest_soc"] >= bat["goal"] - 1
        stamp = prior.get(f"ladefreigabe_venus_{name}_seit_ts")
        # Upgrade an already running pre-2.1 plan without interrupting it.
        prior_time = prior.get("berechnet_ts")
        if stamp is None and isinstance(prior_time, (int, float)) and day <= prior_time <= now:
            if prior.get(f"fahrplan_slot_aktiv_venus_{name}"):
                stamp = prior["berechnet_ts"]
        released[key] = isinstance(stamp, (float, int)) and day <= stamp <= now
        release_ts[key] = stamp if released[key] else None
        previous_cap = prior.get(f"fahrplan_ladegrenze_stabil_venus_{name}_w") or 0
        old_preferred = prior.get(f"leistungsentscheidung_venus_{name}") or {}
        preference_unchanged = old_preferred.get("bevorzugt_w", bat["preferred"]) == bat["preferred"]
        if released[key] and not near_full[key] and preference_unchanged:
            caps[key] = min(bat["maximum"], max(caps[key], previous_cap))

    segments = surplus_segments(rows, now, end, load, cloud_reserve)
    available_kwh = max(0, sum((stop - begin) * (power * efficiency if power > 0 else power) / 3600000
                               for begin, stop, power in segments))
    need_total = sum(needs.values())
    # One reserve for the shared forecast; never count the same PV for A and E.
    buffered = {key: value * reserve_factor for key, value in needs.items()}
    if prior.get("knapp") and need_total > 0:
        buffered = {key: value + hysteresis * needs[key] / need_total
                    for key, value in buffered.items()}
    scarce = need_total > EPS_KWH and available_kwh < sum(buffered.values())
    early_keys = [key for key, bat in batteries.items()
                  if bat["early_goal"] > 0 and bat["lowest_soc"] < min(bat["goal"], bat["early_goal"])]
    starts = {key: now if released[key] or key in early_keys or category == "schwach"
              or scarce or not forecast_ok else max(now, preferred_start)
              for key in keys}
    peak_possible = False
    if peak_enabled and category != "schwach" and forecast_ok and not scarce and need_total > EPS_KWH:
        noon_segments = [s for s in segments if s[1] > max(now, midday_start) and s[0] < midday_end]
        if noon_segments:
            peak_at = max(noon_segments, key=lambda s: s[2])[0] + 450
            candidate = starts.copy()
            for key, bat in batteries.items():
                if not released[key] and key not in early_keys:
                    tail = min(buffered[key], bat["nominal"] * max(0, bat["goal"] - 90) / 100)
                    hours = ((buffered[key] - tail) / max(1, caps[key])
                             + tail / max(1, min(caps[key], bat["tail"]))) * 1000 / efficiency
                    candidate[key] = max(now, midday_start, peak_at - hours * 1800)
            if simulate(segments, batteries, buffered, caps, candidate, efficiency, midday_end)["missing"] <= EPS_KWH:
                starts, peak_possible = candidate, True

    # Move only the storages that would miss their own reserved target earlier.
    # Shared surplus remains accounted for in every calculation.
    for _ in range(len(keys) + 1):
        check = simulate(segments, batteries, buffered, caps, starts, efficiency, end)
        move = [key for key in keys if check["missing_by_key"][key] > EPS_KWH and starts[key] > now]
        if not move:
            break
        for key in move:
            starts[key] = now
        peak_possible = False

    preferred_result = simulate(segments, batteries, needs, caps, starts, efficiency, end)
    result = preferred_result
    boosted = []
    # Higher caps require a real improvement to today's actual target. A cloudy
    # forecast, reserve margin or the final 1 % alone cannot request full power.
    if pv_chance and forecast_ok:
        for key in keys:
            if near_full[key] or result["missing_by_key"][key] <= EPS_KWH:
                continue
            trial_caps = {**caps, key: batteries[key]["maximum"]}
            trial = simulate(segments, batteries, needs, trial_caps, starts, efficiency, end)
            if trial["missing"] >= result["missing"] - 0.01:
                continue
            if trial["missing_by_key"][key] >= result["missing_by_key"][key] - 0.01:
                continue
            low, high = int(ceil(caps[key] / 50)), int(batteries[key]["maximum"] // 50)
            best = trial["missing"] + EPS_KWH
            while low < high:
                mid = (low + high) // 2
                test_caps = {**caps, key: mid * 50}
                test = simulate(segments, batteries, needs, test_caps, starts, efficiency, end)
                if test["missing"] <= best:
                    high = mid
                else:
                    low = mid + 1
            caps[key] = low * 50
            result = simulate(segments, batteries, needs, caps, starts, efficiency, end)
            boosted.append(key)

    decisions = {}
    for key, bat in batteries.items():
        # Actual and persisted register values both survive an HA restart.
        previous = bat["actual_limit"] or prior.get(f"fahrplan_ladegrenze_stabil_venus_{key.lower()}_w") or 0
        previous = int(max(0, min(bat["maximum"], previous)))
        due = starts[key] <= now and pv_chance
        if bat["target_met"]:
            limit, reason = previous, "Geräteziel erreicht; Registerwert bleibt stehen"
            active = False
        elif near_full[key] and (previous > 0 or due or released[key]):
            limit = min(caps[key], previous) if previous > 0 else caps[key]
            reason = "Letztes SoC-Prozent: Nachladen ohne Leistungserhöhung"
            active = True
        elif released[key] or due:
            limit = caps[key]
            if key in boosted:
                reason = "Mehr Leistung verbessert nachweislich die heutige Zielfüllung"
            elif released[key]:
                reason = "Ladefreigabe bleibt bestehen; AstraMeter regelt den Überschuss"
            elif key in early_keys:
                reason = "Eigenes vorzeitiges SoC-Ziel absichern"
            elif category == "schwach":
                reason = "Schwacher Tag: früh laden, keine Mittagsspitzenkappung"
            elif scarce:
                reason = "Knappheit: jetzt mit bevorzugter Leistung beginnen"
            else:
                reason = "Geplanter Ladebeginn erreicht"
            active = True
        elif not pv_chance and (now >= end or category == "schwach"):
            limit, reason, active = previous, "Registerwert bleibt bis zum PV-Überschuss stehen", False
        else:
            limit, reason, active = 0, "Wartet auf den ersten Ladebeginn des Tages", False
        if active and release_ts[key] is None:
            release_ts[key] = now
        decisions[key] = {"limit": limit, "active": active,
                          "released_at": release_ts[key], "start": starts[key],
                          "reason": reason, "near_full": near_full[key],
                          "boosted": key in boosted,
                          "missing": result["missing_by_key"][key],
                          "preferred_missing": preferred_result["missing_by_key"][key],
                          "finish": result["finishes"][key]}
    return {"decisions": decisions, "scarce": scarce, "early_keys": early_keys,
            "result": result, "preferred_result": preferred_result,
            "available_kwh": available_kwh, "peak_possible": peak_possible,
            "peak_export": result["peak_export"] if peak_possible else None,
            "boosted": boosted}
