from dataclasses import dataclass

import pytest

from vln_carla2.usecases.operator.models import SpawnVehicleRequest, VehicleDescriptor
from vln_carla2.usecases.scene_editor.spawn_vehicle_at_spectator_xy import (
    SpawnVehicleAtSpectatorXY,
)


@dataclass
class _FakeLocation:
    x: float
    y: float
    z: float


@dataclass
class _FakeRotation:
    pitch: float = -90.0
    yaw: float = 0.0
    roll: float = 0.0


@dataclass
class _FakeTransform:
    location: _FakeLocation
    rotation: _FakeRotation


class _FakeSpectatorCamera:
    def __init__(self, transform: _FakeTransform) -> None:
        self.transform = transform

    def get_spectator_transform(self) -> _FakeTransform:
        return self.transform


class _FakeGroundResolver:
    def __init__(self, *, ground_z: float | None = None, error: Exception | None = None) -> None:
        self.ground_z = ground_z
        self.error = error
        self.calls: list[tuple[float, float]] = []

    def resolve_ground_z(self, x: float, y: float) -> float:
        self.calls.append((x, y))
        if self.error is not None:
            raise self.error
        if self.ground_z is None:
            raise RuntimeError("no road waypoint found")
        return self.ground_z


class _FakeSpawnVehicle:
    def __init__(self, created: VehicleDescriptor) -> None:
        self.created = created
        self.calls: list[SpawnVehicleRequest] = []

    def run(self, request: SpawnVehicleRequest) -> VehicleDescriptor:
        self.calls.append(request)
        return self.created


def test_spawn_vehicle_at_spectator_xy_reads_xy_and_uses_ground_z_plus_offset() -> None:
    created = VehicleDescriptor(
        actor_id=101,
        type_id="vehicle.tesla.model3",
        role_name="ego",
        x=0.0,
        y=0.0,
        z=0.15,
    )
    spawn_vehicle = _FakeSpawnVehicle(created=created)
    ground_resolver = _FakeGroundResolver(ground_z=3.0)
    camera = _FakeSpectatorCamera(
        _FakeTransform(
            location=_FakeLocation(x=12.5, y=-7.25, z=45.0),
            rotation=_FakeRotation(),
        )
    )
    usecase = SpawnVehicleAtSpectatorXY(
        spectator_camera=camera,
        ground_z_resolver=ground_resolver,
        spawn_vehicle=spawn_vehicle,
        vehicle_z_offset=0.25,
        spawn_yaw=135.0,
        role_name="ego",
    )

    got = usecase.run()

    assert got == created
    assert len(spawn_vehicle.calls) == 1
    request = spawn_vehicle.calls[0]
    assert request.blueprint_filter == "vehicle.tesla.model3"
    assert request.spawn_x == 12.5
    assert request.spawn_y == -7.25
    assert request.spawn_z == 3.25
    assert request.spawn_yaw == 135.0
    assert request.role_name == "ego"
    assert ground_resolver.calls == [(12.5, -7.25)]


def test_spawn_vehicle_at_spectator_xy_fails_when_no_waypoint() -> None:
    spawn_vehicle = _FakeSpawnVehicle(
        created=VehicleDescriptor(
            actor_id=101,
            type_id="vehicle.tesla.model3",
            role_name="ego",
            x=0.0,
            y=0.0,
            z=0.15,
        )
    )
    ground_resolver = _FakeGroundResolver(
        error=RuntimeError("no road waypoint found near spectator XY (x=12.500, y=-7.250)")
    )
    camera = _FakeSpectatorCamera(
        _FakeTransform(
            location=_FakeLocation(x=12.5, y=-7.25, z=45.0),
            rotation=_FakeRotation(),
        )
    )
    usecase = SpawnVehicleAtSpectatorXY(
        spectator_camera=camera,
        ground_z_resolver=ground_resolver,
        spawn_vehicle=spawn_vehicle,
    )

    with pytest.raises(RuntimeError, match="no road waypoint found"):
        usecase.run()

    assert len(spawn_vehicle.calls) == 0
