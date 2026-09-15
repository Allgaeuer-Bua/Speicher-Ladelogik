"""Tests for persistent state compatibility."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

PERSISTENCE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "speicher_ladelogik"
    / "persistence.py"
)
SPEC = spec_from_file_location("speicher_ladelogik_persistence", PERSISTENCE_PATH)
assert SPEC is not None and SPEC.loader is not None
PERSISTENCE = module_from_spec(SPEC)
SPEC.loader.exec_module(PERSISTENCE)


def test_reads_legacy_v3_session() -> None:
    value = "v3|requested|E|1|2|3|0|0|0|0|0|0|requested|2|4||0"
    session = PERSISTENCE.read_session(value)
    assert session["p"] == "requested"
    assert session["b"] == "E"
    assert session["n"] == 4


def test_reads_legacy_v2_session() -> None:
    value = "v2|requested|A|1|2|3|0|0|0|0|0|0|requested|2"
    session = PERSISTENCE.read_session(value)
    assert session["p"] == "requested"
    assert session["b"] == "A"
    assert session["n"] == 0


def test_reads_current_session() -> None:
    value = "state1|drain|E|1|2|3|0|0|0|0|0|0|natural|2|4||0"
    session = PERSISTENCE.read_session(value)
    assert session["p"] == "drain"
    assert session["r"] == "natural"


def test_rejects_corrupt_session() -> None:
    session = PERSISTENCE.read_session("v3|broken")
    assert session["p"] == "error"
    assert session["r"] == "state_corrupt"


def test_reads_legacy_and_current_backups() -> None:
    expected = {"A": 1100.0, "E": 1300.0, "DA": 1500.0, "DE": 2500.0}
    assert PERSISTENCE.read_backup("v2|1100|1300|1500|2500") == expected
    assert PERSISTENCE.read_backup("backup1|1100|1300|1500|2500") == expected


def test_reads_legacy_and_current_queues() -> None:
    expected = {
        "E": {"n": 1789450200, "t": 1789440000, "d": "-"},
    }
    assert PERSISTENCE.read_queue("q5|E,1789450200,1789440000,-") == expected
    assert PERSISTENCE.read_queue("queue1|E,1789450200,1789440000,-") == expected


def test_encoders_use_integration_formats() -> None:
    session = PERSISTENCE.read_session(
        "v3|requested|E|1|2|3|0|0|0|0|0|0|requested|2|4||0"
    )
    assert PERSISTENCE.encode_session(session).startswith("state1|")
    assert PERSISTENCE.encode_backup(
        {"A": 1100, "E": 1300, "DA": 1500, "DE": 2500}
    ).startswith("backup1|")
    assert PERSISTENCE.encode_queue(
        {"E": {"n": 1789450200, "t": 1789440000, "d": "-"}}
    ).startswith("queue1|")
