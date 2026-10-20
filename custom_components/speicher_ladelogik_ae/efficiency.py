"""Stable selection of one or two automatic storages on poor solar days.

Limits are permissions, not forced charging power. Never derive total available
PV from grid export alone: charging already in progress belongs to the budget.
"""

from __future__ import annotations

JOIN_SECONDS = 30
LEAVE_SECONDS = 180
JOIN_MARGIN_W = 250
LEAVE_MARGIN_W = 100
PARALLEL_W = 2000
MAX_SAMPLE_GAP_S = 45


def distribute(*, now, day, profile, enabled, batteries, decisions, surplus,
               export, prior, delay_safe):
    """Modify only eligible automatic decisions; return persistable diagnostics.

The caller excludes manual/calibration/safety reservations. A three-minute
delay must not jeopardize today's forecast target before withholding a limit.
"""
    keys = [key for key, d in decisions.items()
            if d["active"] and d["limit"] > 0 and not batteries[key]["target_met"]]
    state = {"active": False, "mode": "normal", "primary": None, "held": None,
             "day": day, "updated_at": now, "join_since": None, "leave_since": None,
             "join_seconds": JOIN_SECONDS, "leave_seconds": LEAVE_SECONDS,
             "reason": "Normaler Fahrplan"}
    if not enabled or profile not in {"schwach", "wechselhaft"} or len(keys) != 2:
        return state
    if not all(batteries[key]["power_fresh"] for key in keys):
        state["reason"] = "Effizienzauswahl wartet auf frische AC-Messwerte"
        return state

    old = prior if isinstance(prior, dict) and prior.get("day") == day else {}
    primary = old.get("primary")
    if primary not in keys:
        # Secure an unmet early target first; then the lower pack SoC. Retain
        # this choice until completion, not on every changing percentage point.
        primary = min(keys, key=lambda key: (
            batteries[key]["lowest_soc"] >= batteries[key]["early_goal"],
            batteries[key]["lowest_soc"], key))
        old = {}
    secondary = next(key for key in keys if key != primary)
    capacity = decisions[primary]["limit"]
    if batteries[primary]["lowest_soc"] >= 90:
        capacity = min(capacity, batteries[primary]["tail"])
    mode = old.get("mode", "single")
    if mode not in {"single", "parallel"}:
        mode = "single"
    # Retain the observed reduced acceptance (e.g. end-of-charge taper) while
    # parallel; an artificial 50/50 split must not look like recovery to full cap.
    if mode == "parallel" and isinstance(old.get("capacity_w"), (int, float)):
        capacity = min(capacity, max(0, old["capacity_w"]))
    continuous = isinstance(old.get("updated_at"), (int, float)) and 0 <= now - old["updated_at"] <= MAX_SAMPLE_GAP_S

    def since(field, condition):
        stamp = old.get(field)
        valid = continuous and isinstance(stamp, (int, float)) and day <= stamp <= now
        return (stamp if valid else now) if condition else None

    # Real export catches acceptance below the requested cap, but only after
    # the intended solo register values have actually reached the devices.
    solo_applied = (batteries[primary]["actual_limit"] >= decisions[primary]["limit"] - 25
                    and batteries[secondary]["actual_limit"] == 0)
    unused = max(0, surplus - capacity)
    measured_unused = min(max(0, export), max(0, surplus - batteries[primary]["charging_w"]))
    join = surplus >= PARALLEL_W or unused >= JOIN_MARGIN_W or (solo_applied and measured_unused >= JOIN_MARGIN_W)
    join_since = since("join_since", mode == "single" and join)
    leave = surplus < min(PARALLEL_W - JOIN_MARGIN_W, capacity + LEAVE_MARGIN_W) and export < LEAVE_MARGIN_W
    leave_since = since("leave_since", mode == "parallel" and leave)
    reason = "Überschuss auf einen Speicher konzentrieren"
    safe_to_wait = delay_safe(secondary)
    if not safe_to_wait:
        mode, reason = "parallel", "Beide Speicher freigegeben: heutige Zielfüllung absichern"
        join_since = leave_since = None
    elif mode == "single" and join_since is not None and now - join_since >= JOIN_SECONDS:
        mode, reason = "parallel", "Stabiler Restüberschuss: zweiten Speicher zuschalten"
        if solo_applied and measured_unused >= JOIN_MARGIN_W:
            capacity = min(capacity, batteries[primary]["charging_w"])
        join_since = None
    elif mode == "parallel" and leave_since is not None and now - leave_since >= LEAVE_SECONDS:
        mode, reason = "single", "Überschuss seit drei Minuten gering: auf einen Speicher konzentrieren"
        leave_since = None
    elif mode == "parallel":
        reason = "Beide Speicher freigegeben; kurze Leistungsschwankungen werden überbrückt"
    elif join_since is not None:
        reason = "Restüberschuss vorhanden; Zuschaltung nach 30 Sekunden stabiler Leistung"

    if mode == "single":
        decisions[secondary].update(limit=0, active=False,
                                    reason="Effizienzpause: zuerst Speicher " + primary + " laden")
        # Do not invent a first release for a storage withheld by the selector.
        if decisions[secondary]["released_at"] == now:
            decisions[secondary]["released_at"] = None
        decisions[primary]["reason"] = "Effizientes Einzelladen; " + reason
    else:
        for key in keys:
            decisions[key]["reason"] = reason
    state.update(active=True, mode=mode, primary=primary,
                 held=secondary if mode == "single" else None,
                 join_since=join_since, leave_since=leave_since,
                 capacity_w=capacity, surplus_w=round(surplus),
                 remaining_w=round(max(unused, measured_unused if solo_applied else 0)),
                 reason=reason)
    return state
