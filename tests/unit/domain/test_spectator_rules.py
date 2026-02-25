import pytest

from vln_carla2.domain.services.spectator_rules import clamp_z


def test_clamp_z_returns_value_inside_range() -> None:
    assert clamp_z(10.0, min_z=-20.0, max_z=120.0) == 10.0


def test_clamp_z_limits_to_lower_bound() -> None:
    assert clamp_z(-30.0, min_z=-20.0, max_z=120.0) == -20.0


def test_clamp_z_limits_to_upper_bound() -> None:
    assert clamp_z(130.0, min_z=-20.0, max_z=120.0) == 120.0


def test_clamp_z_rejects_invalid_range() -> None:
    with pytest.raises(ValueError):
        clamp_z(0.0, min_z=10.0, max_z=5.0)

