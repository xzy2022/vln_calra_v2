from dataclasses import dataclass

from vln_carla2.infrastructure.carla.world_adapter import CarlaWorldAdapter


@dataclass
class _Transform:
    x: float


class _FakeSpectator:
    def __init__(self, transform: _Transform) -> None:
        self.transform = transform
        self.set_calls = 0

    def get_transform(self) -> _Transform:
        return self.transform

    def set_transform(self, transform: _Transform) -> None:
        self.transform = transform
        self.set_calls += 1


class _FakeWorld:
    def __init__(self, spectator: _FakeSpectator) -> None:
        self._spectator = spectator

    def get_spectator(self) -> _FakeSpectator:
        return self._spectator


def test_world_adapter_reads_and_writes_spectator_transform() -> None:
    spectator = _FakeSpectator(transform=_Transform(x=1.0))
    adapter = CarlaWorldAdapter(world=_FakeWorld(spectator))

    got = adapter.get_spectator_transform()
    assert got.x == 1.0

    adapter.set_spectator_transform(_Transform(x=2.5))
    assert spectator.set_calls == 1
    assert spectator.transform.x == 2.5

