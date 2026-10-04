"""Monitor AC message freshness independently of a battery's charging power."""

from __future__ import annotations


def ac_feedback(*, now, requested, fresh, inverter_status, inverter_fresh, prior):
    """Warn once per continuous missing-data episode, never change a limit.

    A fresh zero or discharge reading is a successful AC report. An inverter
    status only adds context: even a fresh Standby cannot validate stale AC data.
    Persist the episode in the plan so a restart does not repeat the warning.
    """
    previous_issue = bool(prior.get("issue"))
    since = prior.get("requested_since")
    if not isinstance(since, (int, float)) or since > now:
        since = now
    problem_since = prior.get("problem_since")
    if not isinstance(problem_since, (int, float)) or problem_since > now:
        problem_since = now
    if not requested or fresh:
        problem_since = None
    issue = requested and not fresh and now - problem_since >= 180
    status = "aus"
    if requested:
        status = "AC-Rückmeldung aktuell" if fresh else "wartet auf aktuellen AC-Messwert"
        if inverter_fresh:
            status += "; Wechselrichter " + inverter_status
        if issue:
            status = "AC-Messwert länger veraltet (Hinweis)"
    message = "Seit mindestens drei Minuten liegt kein frischer AC-Messwert vor."
    if inverter_fresh:
        message += f" Wechselrichter meldet aktuell {inverter_status}; bitte AC-Sensor prüfen."
    else:
        message += " Auch kein aktueller Wechselrichterstatus verfügbar; bitte Datenverbindung prüfen."
    return {
        "requested_since": since if requested else None,
        "problem_since": problem_since,
        "confirmed": bool(requested and fresh),
        "blocked": False,
        "status": status,
        "issue": bool(issue),
        "notify": bool(issue and not previous_issue),
        "resolved": bool(previous_issue and not issue),
        "message": message if issue else "",
    }
