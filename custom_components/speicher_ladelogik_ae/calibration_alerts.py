"""Advisory calibration warnings; forecasts and PV dips do not stop a run."""

from __future__ import annotations

from typing import Any


def active_alerts(calibration: dict[str, Any], power_by_slot: dict[str, float | None], now_ts: float) -> dict[tuple[str, int, str], str]:
    """Return warnings keyed by storage, charge start and warning type."""
    alerts = {}
    grid = calibration.get("netzleistung_w")
    for job in calibration.get("laufende_laeufe", []):
        if job.get("phase") != "charge" or not job.get("start_ts"):
            continue
        slot = job["batterie"]
        start = int(job["start_ts"])
        prefix = (slot, start)
        name = job.get("name", f"Venus {slot}").strip()
        rest = calibration.get(f"letzte_ruhe_vor_laden_s_{slot.lower()}")
        rest_at = calibration.get(f"letzte_ruhe_vor_laden_ts_{slot.lower()}")
        preferred = calibration.get("ruhedauer_unten_min", 0) * 60
        if (rest is not None and rest_at is not None and
                abs(rest_at - start) <= 120 and rest < preferred):
            alerts[(*prefix, "short_rest")] = (
                f"{name}: Die Ruhezeit vor dem Laden betrug {round(rest / 60)} statt "
                f"{round(preferred / 60)} Minuten. Die Kalibrierung läuft weiter."
            )
        preview = calibration.get(f"heute_{slot.lower()}", {})
        remaining_hours = max(
            0, (preview.get("energy_kwh", 0) - job.get("energie_ac_kwh", 0))
            / max(0.1, calibration.get("leistung_w", 500) / 1000)
        )
        if preview and preview.get("longest_h", 0) + 0.05 < remaining_hours:
            alerts[(*prefix, "short_window")] = (
                f"{name}: Das prognostizierte PV-Fenster ist kürzer als die "
                "voraussichtlich verbleibende Ladezeit. Die Kalibrierung läuft weiter."
            )
        if grid is not None and grid > -400:
            alerts[(*prefix, "low_export")] = (
                f"{name}: Am Stromzähler werden derzeit weniger als 400 W "
                f"eingespeist ({-grid:g} W; negative Werte bedeuten Netzbezug). "
                "Die Kalibrierung läuft weiter; Netzbezug ist möglich."
            )
        power = power_by_slot.get(slot)
        low_since = job.get("unter_400_seit_ts")
        if (power is not None and -power <= 400 and low_since is not None
                and now_ts - low_since >= 300):
            alerts[(*prefix, "low_charge")] = (
                f"{name}: Die gemessene Ladeleistung liegt bei höchstens 400 W "
                f"({max(0, -power):g} W). Die Kalibrierung läuft weiter."
            )
    return alerts
