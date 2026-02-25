import pytest

from vln_carla2.domain.model.vehicle_ref import VehicleRef


def test_vehicle_ref_actor_accepts_positive_integer_text() -> None:
    ref = VehicleRef(scheme="actor", value="42")

    assert ref.scheme == "actor"
    assert ref.value == "42"


def test_vehicle_ref_role_accepts_non_empty_text() -> None:
    ref = VehicleRef(scheme="role", value="ego")

    assert ref.scheme == "role"
    assert ref.value == "ego"


def test_vehicle_ref_first_requires_none_value() -> None:
    ref = VehicleRef(scheme="first", value=None)

    assert ref.scheme == "first"
    assert ref.value is None


@pytest.mark.parametrize("value", [None, "", "abc", "0", "-1"])
def test_vehicle_ref_actor_rejects_invalid_text(value: str | None) -> None:
    with pytest.raises(ValueError, match="positive integer text"):
        VehicleRef(scheme="actor", value=value)


@pytest.mark.parametrize("value", [None, "", "   "])
def test_vehicle_ref_role_rejects_empty_text(value: str | None) -> None:
    with pytest.raises(ValueError, match="non-empty role text"):
        VehicleRef(scheme="role", value=value)


def test_vehicle_ref_first_rejects_non_none_value() -> None:
    with pytest.raises(ValueError, match="value=None"):
        VehicleRef(scheme="first", value="something")
