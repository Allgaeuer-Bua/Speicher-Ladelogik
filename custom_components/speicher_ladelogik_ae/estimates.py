"""Remaining-time estimates from measured AC power, independent of register caps."""

from __future__ import annotations

import math


class RemainingTimeEstimator:
    """Smooth actual power and bridge brief pack handovers, never stale readings."""

    def __init__(self) -> None:
        self.samples: dict[str, dict] = {}

    def estimate(self, key, *, now, power, fresh, soc, nominal, floor, goal,
                 need, efficiency, calibration_ac_remaining=None):
        result = {"modus": "unbekannt", "restzeit_s": None, "ziel_ts": None,
                  "ziel_soc": None, "leistung_geglaettet_w": None,
                  "hinweis": "Schätzung bei derzeitiger Leistung"}
        if not fresh or not all(isinstance(v, (float, int)) and math.isfinite(v)
                                for v in (power, soc, nominal, floor, goal, need, efficiency)):
            self.samples.pop(key, None)
            return result
        previous = self.samples.get(key)
        if previous and not 0 <= now - previous["at"] <= 90:
            previous = None
        direction = -1 if power < -25 else 1 if power > 25 else 0
        if not direction:
            if not previous or now - previous["nonzero"] > 30:
                self.samples.pop(key, None)
                return {**result, "modus": "pausiert"}
            sample = previous
        elif not previous or direction != previous["direction"]:
            sample = {"at": now, "since": now, "nonzero": now,
                      "mean": abs(power), "direction": direction}
        else:
            weight = 1 - math.exp(-(now - previous["at"]) / 120)
            sample = {**previous, "at": now, "nonzero": now,
                      "mean": previous["mean"] + weight * (abs(power) - previous["mean"])}
        self.samples[key] = sample
        if now - sample["since"] < 15:
            return {**result, "modus": "messen"}
        charging = sample["direction"] < 0
        eta = min(1.0, max(0.5, efficiency))
        energy = max(0, need) / eta if charging else nominal * max(0, soc - floor) / 100 * eta
        # Learned calibration energy is already AC energy, including losses.
        if charging and need > 0 and calibration_ac_remaining is not None and calibration_ac_remaining > 0:
            energy = calibration_ac_remaining
        seconds = energy * 3_600_000 / max(25, sample["mean"])
        return {**result, "modus": "laden" if charging else "entladen",
                "restzeit_s": round(seconds), "ziel_ts": now + seconds,
                "ziel_soc": goal if charging else floor,
                "leistung_geglaettet_w": round(sample["mean"])}
