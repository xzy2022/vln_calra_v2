from dataclasses import dataclass

import pytest

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


@dataclass
class _FakeWaypointLocation:
    z: float


@dataclass
class _FakeWaypointTransform:
    location: _FakeWaypointLocation


class _FakeWaypoint:
    def __init__(self, *, z: float) -> None:
        self.transform = _FakeWaypointTransform(location=_FakeWaypointLocation(z=z))


class _FakeMap:
    def __init__(self, waypoint: _FakeWaypoint | None) -> None:
        self._waypoint = waypoint
        self.calls: list[dict[str, object]] = []

    def get_waypoint(self, location: object, project_to_road: bool = True) -> _FakeWaypoint | None:
        self.calls.append(
            {
                "location": location,
                "project_to_road": project_to_road,
            }
        )
        return self._waypoint


class _FakeCarla:
    class Location:
        def __init__(self, *, x: float, y: float, z: float) -> None:
            self.x = x
            self.y = y
            self.z = z


class _FakeWorld:
    def __init__(
        self,
        spectator: _FakeSpectator,
        actors: dict[int, _FakeActor] | None = None,
        map_: _FakeMap | None = None,
    ) -> None:
        self._spectator = spectator
        self._actors = actors or {}
        self._map = map_

    def get_spectator(self) -> _FakeSpectator:
        return self._spectator

    def get_actor(self, actor_id: int) -> _FakeActor | None:
        return self._actors.get(actor_id)

    def get_map(self) -> _FakeMap:
        if self._map is None:
            raise RuntimeError("map is not configured")
        return self._map


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


def test_world_adapter_resolves_ground_z_with_road_projection(monkeypatch) -> None:
    spectator = _FakeSpectator(transform=_Transform(x=1.0))
    fake_map = _FakeMap(waypoint=_FakeWaypoint(z=2.75))
    adapter = CarlaWorldAdapter(world=_FakeWorld(spectator, map_=fake_map))
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.world_adapter.require_carla",
        lambda: _FakeCarla,
    )

    got = adapter.resolve_ground_z(x=12.5, y=-7.25)

    assert got == 2.75
    assert len(fake_map.calls) == 1
    assert fake_map.calls[0]["project_to_road"] is True
    location = fake_map.calls[0]["location"]
    assert isinstance(location, _FakeCarla.Location)
    assert location.x == 12.5
    assert location.y == -7.25
    assert location.z == 0.0


def test_world_adapter_resolve_ground_z_raises_when_no_waypoint(monkeypatch) -> None:
    spectator = _FakeSpectator(transform=_Transform(x=1.0))
    adapter = CarlaWorldAdapter(world=_FakeWorld(spectator, map_=_FakeMap(waypoint=None)))
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.world_adapter.require_carla",
        lambda: _FakeCarla,
    )

    with pytest.raises(RuntimeError, match="no road waypoint found"):
        adapter.resolve_ground_z(x=5.0, y=9.0)
