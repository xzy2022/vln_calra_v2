from vln_carla2.domain.model.forbidden_zone import ForbiddenZone
from vln_carla2.domain.model.point2d import Point2D
from vln_carla2.domain.model.vehicle_state import VehicleState
from vln_carla2.domain.services.forbidden_zone_rules import (
    has_entered_forbidden_zone,
    is_point_in_forbidden_zone,
    is_vehicle_state_in_forbidden_zone,
)


def _zone() -> ForbiddenZone:
    return ForbiddenZone(
        vertices=(
            Point2D(x=0.0, y=0.0),
            Point2D(x=4.0, y=0.0),
            Point2D(x=4.0, y=4.0),
            Point2D(x=0.0, y=4.0),
        )
    )


def _state(*, frame: int, x: float, y: float, yaw_deg: float = 0.0) -> VehicleState:
    return VehicleState(
        frame=frame,
        x=x,
        y=y,
        z=0.0,
        yaw_deg=yaw_deg,
        vx=0.0,
        vy=0.0,
        vz=0.0,
        speed_mps=0.0,
    )


def test_is_point_in_forbidden_zone_inside_and_outside() -> None:
    zone = _zone()

    assert is_point_in_forbidden_zone(Point2D(x=2.0, y=2.0), zone) is True
    assert is_point_in_forbidden_zone(Point2D(x=5.0, y=2.0), zone) is False


def test_is_point_in_forbidden_zone_boundary_and_vertex_count_as_inside() -> None:
    zone = _zone()

    assert is_point_in_forbidden_zone(Point2D(x=4.0, y=2.0), zone) is True
    assert is_point_in_forbidden_zone(Point2D(x=0.0, y=0.0), zone) is True


def test_is_vehicle_state_in_forbidden_zone_uses_xy_only() -> None:
    zone = _zone()
    state = _state(frame=1, x=2.0, y=1.0, yaw_deg=77.0)

    assert is_vehicle_state_in_forbidden_zone(state, zone) is True


def test_has_entered_forbidden_zone_returns_true_when_any_state_hits() -> None:
    zone = _zone()
    states = [
        _state(frame=1, x=-1.0, y=0.0),
        _state(frame=2, x=1.0, y=1.0),
        _state(frame=3, x=6.0, y=2.0),
    ]

    assert has_entered_forbidden_zone(states, zone) is True


def test_has_entered_forbidden_zone_returns_false_when_no_state_hits() -> None:
    zone = _zone()
    states = [
        _state(frame=1, x=-1.0, y=0.0),
        _state(frame=2, x=6.0, y=1.0),
    ]

    assert has_entered_forbidden_zone(states, zone) is False
