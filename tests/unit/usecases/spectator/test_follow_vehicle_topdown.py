from dataclasses import dataclass

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.usecases.spectator.follow_vehicle_topdown import FollowVehicleTopDown


@dataclass
class _Location:
    x: float
    y: float
    z: float


@dataclass
class _Rotation:
    pitch: float
    yaw: float
    roll: float


@dataclass
class _Transform:
    location: _Location
    rotation: _Rotation


class _FakeWorld:
    def __init__(
        self,
        spectator_transform: _Transform,
        vehicle_transform: _Transform | None,
    ) -> None:
        self._spectator_transform = spectator_transform
        self._vehicle_transform = vehicle_transform
        self.set_calls = 0

    def get_spectator_transform(self) -> _Transform:
        return self._spectator_transform

    def set_spectator_transform(self, transform: _Transform) -> None:
        self._spectator_transform = transform
        self.set_calls += 1

    def get_vehicle_transform(self, vehicle_id: VehicleId) -> _Transform | None:
        return self._vehicle_transform


def test_follow_vehicle_topdown_updates_xy_and_locks_rotation() -> None:
    world = _FakeWorld(
        spectator_transform=_Transform(
            location=_Location(x=0.0, y=0.0, z=3.0),
            rotation=_Rotation(pitch=10.0, yaw=20.0, roll=30.0),
        ),
        vehicle_transform=_Transform(
            location=_Location(x=12.0, y=-8.0, z=1.5),
            rotation=_Rotation(pitch=0.0, yaw=80.0, roll=0.0),
        ),
    )
    usecase = FollowVehicleTopDown(world=world, vehicle_id=VehicleId(7), z=20.0)

    followed = usecase.follow_once()

    assert followed is True
    transform = world.get_spectator_transform()
    assert transform.location.x == 12.0
    assert transform.location.y == -8.0
    assert transform.location.z == 20.0
    assert transform.rotation.pitch == -90.0
    assert transform.rotation.yaw == 0.0
    assert transform.rotation.roll == 0.0
    assert world.set_calls == 1


def test_follow_vehicle_topdown_returns_false_when_vehicle_missing() -> None:
    world = _FakeWorld(
        spectator_transform=_Transform(
            location=_Location(x=2.0, y=4.0, z=6.0),
            rotation=_Rotation(pitch=1.0, yaw=2.0, roll=3.0),
        ),
        vehicle_transform=None,
    )
    usecase = FollowVehicleTopDown(world=world, vehicle_id=VehicleId(9), z=20.0)

    followed = usecase.follow_once()

    assert followed is False
    transform = world.get_spectator_transform()
    assert transform.location.x == 2.0
    assert transform.location.y == 4.0
    assert transform.location.z == 6.0
    assert transform.rotation.pitch == 1.0
    assert transform.rotation.yaw == 2.0
    assert transform.rotation.roll == 3.0
    assert world.set_calls == 0
