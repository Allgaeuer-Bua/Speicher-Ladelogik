"""Stable, JSON-compatible identities for calibration notifications."""

from .persistence import read_session

TERMINAL_PHASES = {"done", "incomplete", "cancelled", "error"}


def notification_signature(calibration):
    """Names and live countdowns do not constitute a new calibration event."""
    jobs = calibration.get("auftraege", [])
    if jobs:
        return ["jobs", sorted([
            [job.get("batterie"), job.get("phase"), job.get("grund"),
             job.get("fruehestens_ts"), job.get("ruhe_ende_ts")]
            for job in jobs
        ], key=lambda job: str(job[0]))]
    if calibration.get("phase") in TERMINAL_PHASES:
        return ["result", calibration.get("batterie"), calibration.get("phase"),
                calibration.get("phase_seit_ts"), calibration.get("start_ts"),
                calibration.get("ende_ts"), calibration.get("grund_code")]
    return ["idle"]


def restored_notification_signature(stored, control):
    """Migrate an old terminal session silently; new transitions still notify.

    Seed only from the persisted session before planning starts, so a new
    cancellation during the first calculation is not mistaken for old history.
    """
    if isinstance(stored, list):
        return stored
    session = read_session(control.get("kalibrierung_sitzung", ""))
    if session["p"] not in TERMINAL_PHASES:
        return None
    return notification_signature({
        "batterie": session["b"], "phase": session["p"],
        "phase_seit_ts": session["t"] or None,
        "start_ts": session["s"] or None, "ende_ts": session["x"] or None,
        "grund_code": session["r"],
    })
