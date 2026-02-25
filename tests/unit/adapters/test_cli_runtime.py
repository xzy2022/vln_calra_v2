from dataclasses import dataclass

from vln_carla2.adapters.cli.runtime import CliRuntime
from vln_carla2.usecases.input_snapshot import InputSnapshot


@dataclass
class _Snapshot:
    frame: int


@dataclass
class _FakeWorld:
    tick_calls: int = 0
    wait_for_tick_calls: int = 0

    def tick(self) -> int:
        self.tick_calls += 1
        return self.tick_calls

    def wait_for_tick(self) -> _Snapshot:
        self.wait_for_tick_calls += 1
        return _Snapshot(frame=100 + self.wait_for_tick_calls)


@dataclass
class _FakeLocation:
    x: float
    y: float
    z: float


@dataclass
class _FakeRotation:
    pitch: float
    yaw: float
    roll: float


@dataclass
class _FakeTransform:
    location: _FakeLocation
    rotation: _FakeRotation


class _FakeActor:
    def __init__(self, transform: _FakeTransform) -> None:
        self._transform = transform

    def get_transform(self) -> _FakeTransform:
        return self._transform

    def set_transform(self, transform: _FakeTransform) -> None:
        self._transform = transform


class _FakeSpectator:
    def __init__(self) -> None:
        self.transform = _FakeTransform(
            location=_FakeLocation(x=3.0, y=4.0, z=1.0),
            rotation=_FakeRotation(pitch=0.0, yaw=45.0, roll=10.0),
        )

    def get_transform(self) -> _FakeTransform:
        return self.transform

    def set_transform(self, transform: _FakeTransform) -> None:
        self.transform = transform


class _FakeWorldWithSpectator(_FakeWorld):
    def __init__(self) -> None:
        super().__init__()
        self._spectator = _FakeSpectator()
        self._actors: dict[int, _FakeActor] = {}
        self._actor_sequence: list[_FakeActor | None] | None = None

    def get_spectator(self) -> _FakeSpectator:
        return self._spectator

    def set_actor(self, actor_id: int, actor: _FakeActor | None) -> None:
        if actor is None:
            self._actors.pop(actor_id, None)
        else:
            self._actors[actor_id] = actor

    def set_actor_sequence(self, sequence: list[_FakeActor | None]) -> None:
        self._actor_sequence = list(sequence)

    def get_actor(self, actor_id: int) -> _FakeActor | None:
        if self._actor_sequence is not None and self._actor_sequence:
            return self._actor_sequence.pop(0)
        return self._actors.get(actor_id)


class _FakeKeyboardInput:
    def __init__(self, snapshots: list[InputSnapshot]) -> None:
        self._snapshots = snapshots
        self._index = 0

    def read_snapshot(self) -> InputSnapshot:
        delta = self._snapshots[self._index]
        self._index += 1
        return delta


class _FakeMoveSpectator:
    def __init__(self) -> None:
        self.calls: list[InputSnapshot] = []

    def move(self, snapshot: InputSnapshot) -> None:
        self.calls.append(snapshot)


def test_runtime_runs_sync_loop(monkeypatch) -> None:
    sleep_calls: list[float] = []
    world = _FakeWorld()
    runtime = CliRuntime(world=world, synchronous_mode=True, sleep_seconds=0.01)

    monkeypatch.setattr(
        "vln_carla2.adapters.cli.runtime.time.sleep",
        lambda seconds: sleep_calls.append(seconds),
    )

    executed = runtime.run(max_ticks=3)

    assert executed == 3
    assert world.tick_calls == 3
    assert world.wait_for_tick_calls == 0
    assert sleep_calls == [0.01, 0.01, 0.01]


def test_runtime_runs_async_loop(monkeypatch) -> None:
    sleep_calls: list[float] = []
    world = _FakeWorld()
    runtime = CliRuntime(world=world, synchronous_mode=False, sleep_seconds=0.02)

    monkeypatch.setattr(
        "vln_carla2.adapters.cli.runtime.time.sleep",
        lambda seconds: sleep_calls.append(seconds),
    )

    executed = runtime.run(max_ticks=2)

    assert executed == 2
    assert world.tick_calls == 0
    assert world.wait_for_tick_calls == 2
    assert sleep_calls == []


def test_runtime_handles_keyboard_delta_before_tick() -> None:
    world = _FakeWorldWithSpectator()
    keyboard = _FakeKeyboardInput(
        snapshots=[InputSnapshot(dx=1.0, dy=0.0, dz=0.5), InputSnapshot.zero()]
    )
    move_spectator = _FakeMoveSpectator()
    runtime = CliRuntime(
        world=world,
        synchronous_mode=False,
        sleep_seconds=0.0,
        keyboard_input=keyboard,
        move_spectator=move_spectator,
    )

    spectator_transform = world.get_spectator().get_transform()
    assert spectator_transform.location.z == 20.0
    assert spectator_transform.rotation.pitch == -90.0
    assert spectator_transform.rotation.yaw == 0.0
    assert spectator_transform.rotation.roll == 0.0

    executed = runtime.run(max_ticks=2)

    assert executed == 2
    assert world.wait_for_tick_calls == 2
    assert move_spectator.calls == [InputSnapshot(dx=1.0, dy=0.0, dz=0.5), InputSnapshot.zero()]


def test_runtime_follow_vehicle_overrides_keyboard_when_actor_exists() -> None:
    world = _FakeWorldWithSpectator()
    world.set_actor(
        42,
        _FakeActor(
            _FakeTransform(
                location=_FakeLocation(x=100.0, y=-40.0, z=1.5),
                rotation=_FakeRotation(pitch=5.0, yaw=15.0, roll=0.0),
            )
        ),
    )
    keyboard = _FakeKeyboardInput(
        snapshots=[InputSnapshot(dx=2.0, dy=3.0, dz=1.0), InputSnapshot.zero()]
    )
    runtime = CliRuntime(
        world=world,
        synchronous_mode=False,
        sleep_seconds=0.0,
        keyboard_input=keyboard,
        follow_vehicle_id=42,
    )

    executed = runtime.run(max_ticks=2)

    assert executed == 2
    spectator_transform = world.get_spectator().get_transform()
    assert spectator_transform.location.x == 100.0
    assert spectator_transform.location.y == -40.0
    assert spectator_transform.location.z == 20.0
    assert spectator_transform.rotation.pitch == -90.0
    assert spectator_transform.rotation.yaw == 0.0
    assert spectator_transform.rotation.roll == 0.0


def test_runtime_follow_vehicle_falls_back_to_keyboard_when_actor_missing() -> None:
    world = _FakeWorldWithSpectator()
    keyboard = _FakeKeyboardInput(snapshots=[InputSnapshot(dx=1.0, dy=-2.0, dz=0.5)])
    runtime = CliRuntime(
        world=world,
        synchronous_mode=False,
        sleep_seconds=0.0,
        keyboard_input=keyboard,
        follow_vehicle_id=999,
    )

    executed = runtime.run(max_ticks=1)

    assert executed == 1
    spectator_transform = world.get_spectator().get_transform()
    assert spectator_transform.location.x == 4.0
    assert spectator_transform.location.y == 2.0
    assert spectator_transform.location.z == 20.5
    assert spectator_transform.rotation.pitch == -90.0
    assert spectator_transform.rotation.yaw == 0.0
    assert spectator_transform.rotation.roll == 0.0


def test_runtime_follow_vehicle_retries_and_recovers_when_actor_reappears() -> None:
    world = _FakeWorldWithSpectator()
    actor = _FakeActor(
        _FakeTransform(
            location=_FakeLocation(x=10.0, y=20.0, z=1.0),
            rotation=_FakeRotation(pitch=0.0, yaw=0.0, roll=0.0),
        )
    )
    world.set_actor_sequence([None, actor])
    keyboard = _FakeKeyboardInput(
        snapshots=[InputSnapshot(dx=1.0, dy=1.0, dz=0.0), InputSnapshot.zero()]
    )
    runtime = CliRuntime(
        world=world,
        synchronous_mode=False,
        sleep_seconds=0.0,
        keyboard_input=keyboard,
        follow_vehicle_id=7,
    )

    executed = runtime.run(max_ticks=2)

    assert executed == 2
    spectator_transform = world.get_spectator().get_transform()
    assert spectator_transform.location.x == 10.0
    assert spectator_transform.location.y == 20.0
    assert spectator_transform.location.z == 20.0
