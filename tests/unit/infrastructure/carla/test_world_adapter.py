from dataclasses import dataclass

from vln_carla2.domain.model.vehicle_id import VehicleId
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


class _FakeActor:
    def __init__(self, transform: _Transform) -> None:
        self._transform = transform

    def get_transform(self) -> _Transform:
        return self._transform


class _FakeWorld:
    def __init__(
        self,
        spectator: _FakeSpectator,
        actors: dict[int, _FakeActor] | None = None,
    ) -> None:
        self._spectator = spectator
        self._actors = actors or {}

    def get_spectator(self) -> _FakeSpectator:
        return self._spectator

    def get_actor(self, actor_id: int) -> _FakeActor | None:
        return self._actors.get(actor_id)


def test_world_adapter_reads_and_writes_spectator_transform() -> None:
    spectator = _FakeSpectator(transform=_Transform(x=1.0))
    adapter = CarlaWorldAdapter(world=_FakeWorld(spectator))

    got = adapter.get_spectator_transform()
    assert got.x == 1.0

    adapter.set_spectator_transform(_Transform(x=2.5))
    assert spectator.set_calls == 1
    assert spectator.transform.x == 2.5


def test_world_adapter_reads_vehicle_transform_when_actor_exists() -> None:
    spectator = _FakeSpectator(transform=_Transform(x=1.0))
    actor_transform = _Transform(x=9.0)
    adapter = CarlaWorldAdapter(
        world=_FakeWorld(
            spectator,
            actors={42: _FakeActor(transform=actor_transform)},
        )
    )

    got = adapter.get_vehicle_transform(42)

    assert got is actor_transform


def test_world_adapter_returns_none_when_vehicle_actor_missing() -> None:
    spectator = _FakeSpectator(transform=_Transform(x=1.0))
    adapter = CarlaWorldAdapter(world=_FakeWorld(spectator, actors={}))

    got = adapter.get_vehicle_transform(VehicleId(42))

    assert got is None
