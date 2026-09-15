"""Parse persistent planner state from current and previous installations."""

from __future__ import annotations

from typing import Any

SESSION_KEYS = (
    "p",
    "b",
    "t",
    "s",
    "x",
    "l",
    "f",
    "h",
    "w",
    "v",
    "q",
    "r",
    "z",
    "n",
    "u",
    "i",
)

VALID_PHASES = {
    "idle",
    "requested",
    "drain",
    "wait",
    "charge",
    "rest",
    "paused",
    "restore",
    "incomplete",
    "done",
    "cancelled",
    "error",
}

VALID_RESUME_PHASES = {"", "requested", "drain", "wait", "charge", "rest"}


def _number(value: Any, default: float | None = None) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if result != result or abs(result) > 1_000_000_000_000:
        return default
    return result


def _empty_session() -> dict[str, Any]:
    return {
        "p": "idle",
        "b": "",
        "t": 0,
        "s": 0,
        "x": 0,
        "l": 0,
        "f": 0,
        "h": 0,
        "w": 0,
        "v": 0,
        "q": 0,
        "r": "",
        "z": 0,
        "n": 0,
        "u": "",
        "i": 0,
    }


def _corrupt_session() -> dict[str, Any]:
    session = _empty_session()
    session["p"] = "error"
    session["r"] = "state_corrupt"
    return session


def read_session(value: Any) -> dict[str, Any]:
    """Read V2.2.1 (`v2`/`v3`) and integration (`state1`) sessions."""
    session = _empty_session()
    if value in {"", "unknown", "unavailable", None}:
        return session

    fields = str(value).split("|")
    legacy_v2 = len(fields) == 14 and fields[0] == "v2"
    full_session = len(fields) == 17 and fields[0] in {"v3", "state1"}
    if not (legacy_v2 or full_session):
        return _corrupt_session()

    keys = SESSION_KEYS[:13] if legacy_v2 else SESSION_KEYS
    for index, key in enumerate(keys, start=1):
        item: Any = fields[index]
        if key not in {"p", "b", "r", "u"}:
            item = _number(item)
            if item is None or item < 0:
                return _corrupt_session()
        session[key] = item

    if session["p"] not in VALID_PHASES:
        return _corrupt_session()
    if session["p"] not in {"idle", "error"} and session["b"] not in {"A", "E"}:
        return _corrupt_session()
    if session["u"] not in VALID_RESUME_PHASES:
        return _corrupt_session()
    return session


def encode_session(session: dict[str, Any]) -> str:
    """Encode the integration-owned session format."""
    fields = ["state1"]
    for key in SESSION_KEYS:
        value = session[key]
        fields.append(str(round(value, 3)) if isinstance(value, float) else str(value))
    return "|".join(fields)


def read_backup(value: Any) -> dict[str, float] | None:
    """Read V2.2.1 (`v2`) and integration (`backup1`) limit backups."""
    fields = str(value).split("|")
    if len(fields) != 5 or fields[0] not in {"v2", "backup1"}:
        return None

    values = [_number(item) for item in fields[1:]]
    # Storage slots may be mapped to another Venus model. The actual number
    # entity range is validated immediately before every write.
    maxima = (10000, 10000, 10000, 10000)
    if not all(
        value is not None
        and (value == -1 or (0 <= value <= maxima[index] and value % 50 == 0))
        for index, value in enumerate(values)
    ):
        return None
    return {
        "A": values[0],
        "E": values[1],
        "DA": values[2],
        "DE": values[3],
    }


def encode_backup(values: dict[str, Any]) -> str:
    """Encode the integration-owned limit-backup format."""
    return "backup1|" + "|".join(str(values[key]) for key in ("A", "E", "DA", "DE"))


def read_queue(value: Any) -> dict[str, dict[str, Any]] | None:
    """Read V2.2.1 (`q5`) and integration (`queue1`) calibration queues."""
    if value == "":
        return {}

    fields = str(value).split("|")
    if not fields or fields[0] not in {"q5", "queue1"} or len(fields) > 3:
        return None

    queue: dict[str, dict[str, Any]] = {}
    for field in fields[1:]:
        parts = field.split(",")
        if len(parts) != 4 or parts[0] not in {"A", "E"} or parts[0] in queue:
            return None
        day = _number(parts[1])
        stamp = _number(parts[2])
        dependency = parts[3]
        if (
            day is None
            or day < 0
            or stamp is None
            or stamp < 0
            or dependency not in {"-", "A", "E"}
            or dependency == parts[0]
        ):
            return None
        queue[parts[0]] = {
            "n": int(day),
            "t": int(stamp),
            "d": dependency,
        }
    return queue


def encode_queue(queue: dict[str, dict[str, Any]]) -> str:
    """Encode the integration-owned calibration-queue format."""
    result = ["queue1"]
    for key in ("A", "E"):
        if key in queue:
            item = queue[key]
            result.append(f"{key},{int(item['n'])},{int(item['t'])},{item['d']}")
    return "|".join(result)
