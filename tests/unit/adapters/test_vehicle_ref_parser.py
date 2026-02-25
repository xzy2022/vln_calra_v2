import pytest

from vln_carla2.adapters.cli.vehicle_ref_parser import (
    VehicleRefParseError,
    parse_vehicle_ref,
)


def test_parse_vehicle_ref_accepts_actor_scheme() -> None:
    ref = parse_vehicle_ref("actor:42")

    assert ref.scheme == "actor"
    assert ref.value == "42"


def test_parse_vehicle_ref_accepts_plain_actor_id() -> None:
    ref = parse_vehicle_ref("7")

    assert ref.scheme == "actor"
    assert ref.value == "7"


def test_parse_vehicle_ref_accepts_role_scheme() -> None:
    ref = parse_vehicle_ref("role:ego")

    assert ref.scheme == "role"
    assert ref.value == "ego"


def test_parse_vehicle_ref_accepts_first() -> None:
    ref = parse_vehicle_ref("first")

    assert ref.scheme == "first"
    assert ref.value is None


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("", "empty input"),
        ("role:", "missing role name"),
        ("actor:abc", "positive integer text"),
        ("first:1", "does not accept a value"),
        ("unknown:1", "unsupported scheme"),
    ],
)
def test_parse_vehicle_ref_reports_diagnostic_error(raw: str, message: str) -> None:
    with pytest.raises(VehicleRefParseError, match=message):
        parse_vehicle_ref(raw)
