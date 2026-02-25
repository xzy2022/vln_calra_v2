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
