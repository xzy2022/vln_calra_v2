from dataclasses import dataclass

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.usecases.operator.follow_vehicle_topdown import FollowVehicleTopDown
from vln_carla2.usecases.operator.run_operator_loop import RunOperatorLoop
from vln_carla2.usecases.spectator.input_snapshot import InputSnapshot


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


class _FakeCameraPort:
    def __init__(self, transform: _Transform) -> None:
        self._transform = transform
        self.set_calls = 0

    def get_spectator_transform(self) -> _Transform:
        return self._transform

    def set_spectator_transform(self, transform: _Transform) -> None:
        self._transform = transform
        self.set_calls += 1


class _FakeVehiclePosePort:
    def __init__(self, transform: _Transform | None) -> None:
        self._transform = transform

    def get_vehicle_transform(self, _actor_id: int) -> _Transform | None:
        return self._transform


def test_follow_vehicle_topdown_uses_split_ports() -> None:
    camera = _FakeCameraPort(
        _Transform(
            location=_Location(x=0.0, y=0.0, z=3.0),
            rotation=_Rotation(pitch=10.0, yaw=20.0, roll=30.0),
        )
    )
    pose = _FakeVehiclePosePort(
        _Transform(
            location=_Location(x=12.0, y=-8.0, z=1.5),
            rotation=_Rotation(pitch=0.0, yaw=80.0, roll=0.0),
        )
    )
    usecase = FollowVehicleTopDown(
        spectator_camera=camera,
        vehicle_pose=pose,
        vehicle_id=VehicleId(7),
        z=20.0,
    )

    followed = usecase.follow_once()

    assert followed is True
    transform = camera.get_spectator_transform()
    assert transform.location.x == 12.0
    assert transform.location.y == -8.0
    assert transform.location.z == 20.0
    assert transform.rotation.pitch == -90.0
    assert transform.rotation.yaw == 0.0
    assert transform.rotation.roll == 0.0
    assert camera.set_calls == 1


def test_follow_vehicle_topdown_returns_false_when_vehicle_missing() -> None:
    camera = _FakeCameraPort(
        _Transform(
            location=_Location(x=2.0, y=4.0, z=6.0),
            rotation=_Rotation(pitch=1.0, yaw=2.0, roll=3.0),
        )
    )
    pose = _FakeVehiclePosePort(None)
    usecase = FollowVehicleTopDown(
        spectator_camera=camera,
        vehicle_pose=pose,
        vehicle_id=VehicleId(9),
        z=20.0,
    )

    followed = usecase.follow_once()

    assert followed is False
    transform = camera.get_spectator_transform()
    assert transform.location.x == 2.0
    assert transform.location.y == 4.0
    assert transform.location.z == 6.0
    assert transform.rotation.pitch == 1.0
    assert transform.rotation.yaw == 2.0
    assert transform.rotation.roll == 3.0
    assert camera.set_calls == 0


@dataclass
class _Snapshot:
    frame: int


class _FakeWorld:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.tick_calls = 0
        self.wait_for_tick_calls = 0

    def tick(self) -> int:
        self.tick_calls += 1
        self.events.append("tick")
        return self.tick_calls

    def wait_for_tick(self) -> _Snapshot:
        self.wait_for_tick_calls += 1
        self.events.append("tick")
        return _Snapshot(frame=100 + self.wait_for_tick_calls)


class _FakeKeyboardInput:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def read_snapshot(self) -> InputSnapshot:
        self.events.append("read")
        return InputSnapshot(dx=1.0, dy=0.0, dz=0.0)


class _FakeMoveSpectator:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def move(self, snapshot: InputSnapshot) -> None:
        assert snapshot.dx == 1.0
        self.events.append("move")


class _FakeFollowVehicle:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def follow_once(self) -> bool:
        self.events.append("follow")
        return True


def test_run_operator_loop_keeps_order_move_then_follow_then_tick() -> None:
    events: list[str] = []
    loop = RunOperatorLoop(
        world=_FakeWorld(events),
        synchronous_mode=False,
        sleep_seconds=0.0,
        keyboard_input=_FakeKeyboardInput(events),
        move_spectator=_FakeMoveSpectator(events),
        follow_vehicle_topdown=_FakeFollowVehicle(events),
    )

    executed = loop.run(max_ticks=1)

    assert executed == 1
    assert events == ["read", "move", "follow", "tick"]


def test_run_operator_loop_step_can_skip_tick() -> None:
    events: list[str] = []
    world = _FakeWorld(events)
    loop = RunOperatorLoop(
        world=world,
        synchronous_mode=True,
        sleep_seconds=0.2,
        keyboard_input=_FakeKeyboardInput(events),
        move_spectator=_FakeMoveSpectator(events),
        follow_vehicle_topdown=_FakeFollowVehicle(events),
    )

    frame = loop.step(with_tick=False, with_sleep=False)

    assert frame is None
    assert events == ["read", "move", "follow"]
    assert world.tick_calls == 0
    assert world.wait_for_tick_calls == 0


def test_legacy_follow_import_points_to_operator_usecase() -> None:
    from vln_carla2.usecases.spectator.follow_vehicle_topdown import (
        FollowVehicleTopDown as LegacyFollow,
    )

    assert LegacyFollow is FollowVehicleTopDown
