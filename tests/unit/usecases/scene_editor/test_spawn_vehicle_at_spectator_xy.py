from dataclasses import dataclass

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


class _FakeSpawnVehicle:
    def __init__(self, created: VehicleDescriptor) -> None:
        self.created = created
        self.calls: list[SpawnVehicleRequest] = []

    def run(self, request: SpawnVehicleRequest) -> VehicleDescriptor:
        self.calls.append(request)
        return self.created


def test_spawn_vehicle_at_spectator_xy_reads_xy_and_uses_fixed_z() -> None:
    created = VehicleDescriptor(
        actor_id=101,
        type_id="vehicle.tesla.model3",
        role_name="ego",
        x=0.0,
        y=0.0,
        z=0.15,
    )
    spawn_vehicle = _FakeSpawnVehicle(created=created)
    camera = _FakeSpectatorCamera(
        _FakeTransform(
            location=_FakeLocation(x=12.5, y=-7.25, z=45.0),
            rotation=_FakeRotation(),
        )
    )
    usecase = SpawnVehicleAtSpectatorXY(
        spectator_camera=camera,
        spawn_vehicle=spawn_vehicle,
        spawn_z=0.25,
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
    assert request.spawn_z == 0.25
    assert request.spawn_yaw == 135.0
    assert request.role_name == "ego"
