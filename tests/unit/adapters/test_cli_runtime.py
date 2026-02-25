from dataclasses import dataclass

from vln_carla2.adapters.cli.runtime import CliRuntime


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

    def get_spectator(self) -> _FakeSpectator:
        return self._spectator


class _FakeKeyboardInput:
    def __init__(self, deltas: list[tuple[float, float, float]]) -> None:
        self._deltas = deltas
        self._index = 0

    def read_delta(self) -> tuple[float, float, float]:
        delta = self._deltas[self._index]
        self._index += 1
        return delta


class _FakeMoveSpectator:
    def __init__(self) -> None:
        self.calls: list[tuple[float, float, float]] = []

    def move(self, dx: float, dy: float, dz: float) -> None:
        self.calls.append((dx, dy, dz))


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
    keyboard = _FakeKeyboardInput(deltas=[(1.0, 0.0, 0.5), (0.0, 0.0, 0.0)])
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
    assert move_spectator.calls == [(1.0, 0.0, 0.5), (0.0, 0.0, 0.0)]
