from dataclasses import dataclass

import pytest

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.infrastructure.carla.state_reader import CarlaVehicleStateReader


@dataclass
class _Location:
    x: float
    y: float
    z: float


@dataclass
class _Rotation:
    yaw: float


@dataclass
class _Transform:
    location: _Location
    rotation: _Rotation


@dataclass
class _Velocity:
    x: float
    y: float
    z: float


@dataclass
class _Snapshot:
    frame: int


class _BoundingBox:
    def __init__(self, vertices: list[_Location]) -> None:
        self._vertices = vertices

    def get_world_vertices(self, _transform: _Transform) -> list[_Location]:
        return list(self._vertices)


class _Actor:
    def __init__(
        self,
        *,
        actor_id: int,
        transform: _Transform,
        velocity: _Velocity,
        vertices: list[_Location],
    ) -> None:
        self.id = actor_id
        self._transform = transform
        self._velocity = velocity
        self.bounding_box = _BoundingBox(vertices=vertices)

    def get_transform(self) -> _Transform:
        return self._transform

    def get_velocity(self) -> _Velocity:
        return self._velocity


class _World:
    def __init__(self, actor: _Actor | None) -> None:
        self._actor = actor

    def get_actor(self, _actor_id: int) -> _Actor | None:
        return self._actor

    def get_snapshot(self) -> _Snapshot:
        return _Snapshot(frame=123)


def test_state_reader_reads_actor_origin_and_bbox_probe_points() -> None:
    vertices = [
        _Location(x=2.0, y=1.0, z=0.2),
        _Location(x=2.0, y=-1.0, z=0.2),
        _Location(x=0.0, y=1.0, z=0.2),
        _Location(x=0.0, y=-1.0, z=0.2),
        _Location(x=2.0, y=1.0, z=1.2),
        _Location(x=2.0, y=-1.0, z=1.2),
        _Location(x=0.0, y=1.0, z=1.2),
        _Location(x=0.0, y=-1.0, z=1.2),
    ]
    actor = _Actor(
        actor_id=7,
        transform=_Transform(location=_Location(x=10.0, y=20.0, z=0.5), rotation=_Rotation(yaw=30.0)),
        velocity=_Velocity(x=3.0, y=4.0, z=0.0),
        vertices=vertices,
    )
    reader = CarlaVehicleStateReader(world=_World(actor))

    state = reader.read(VehicleId(7))

    assert state.frame == 123
    assert state.x == 10.0
    assert state.y == 20.0
    assert state.z == 0.5
    assert state.yaw_deg == 30.0
    assert state.speed_mps == pytest.approx(5.0)
    # Probe points = (bbox center) + (bottom 4 world corners).
    assert state.forbidden_zone_probe_points_xy[0] == pytest.approx((1.0, 0.0))
    assert set(state.forbidden_zone_probe_points_xy[1:]) == {
        (2.0, 1.0),
        (2.0, -1.0),
        (0.0, 1.0),
        (0.0, -1.0),
    }


def test_state_reader_raises_when_actor_missing() -> None:
    reader = CarlaVehicleStateReader(world=_World(actor=None))

    with pytest.raises(RuntimeError, match="Vehicle actor not found"):
        reader.read(VehicleId(7))
