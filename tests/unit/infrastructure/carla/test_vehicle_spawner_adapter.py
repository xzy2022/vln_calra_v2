from dataclasses import dataclass
from typing import Any

from vln_carla2.infrastructure.carla.vehicle_spawner_adapter import CarlaVehicleSpawnerAdapter
from vln_carla2.usecases.runtime.ports.vehicle_dto import SpawnVehicleRequest


@dataclass
class _Location:
    x: float
    y: float
    z: float


@dataclass
class _Transform:
    location: _Location


class _FakeActor:
    id = 77
    type_id = "vehicle.mini.cooper"
    attributes = {"role_name": "npc"}

    def get_transform(self) -> _Transform:
        return _Transform(location=_Location(x=10.0, y=11.0, z=12.0))


class _FakeActorNoRole:
    id = 88
    type_id = "vehicle.lincoln.mkz_2020"
    attributes = {}

    def get_transform(self) -> _Transform:
        return _Transform(location=_Location(x=20.0, y=21.0, z=22.0))


def test_vehicle_spawner_adapter_calls_spawner_and_returns_descriptor(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    world = object()

    def fake_spawn_vehicle(**kwargs: Any) -> _FakeActor:
        captured["kwargs"] = kwargs
        return _FakeActor()

    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.vehicle_spawner_adapter.spawn_vehicle",
        fake_spawn_vehicle,
    )

    adapter = CarlaVehicleSpawnerAdapter(world=world)
    request = SpawnVehicleRequest(
        blueprint_filter="vehicle.mini.cooper",
        spawn_x=1.0,
        spawn_y=2.0,
        spawn_z=3.0,
        spawn_yaw=90.0,
        role_name="npc",
    )

    got = adapter.spawn(request)

    assert captured["kwargs"] == {
        "world": world,
        "blueprint_filter": "vehicle.mini.cooper",
        "spawn_x": 1.0,
        "spawn_y": 2.0,
        "spawn_z": 3.0,
        "spawn_yaw": 90.0,
        "role_name": "npc",
    }
    assert got.actor_id == 77
    assert got.type_id == "vehicle.mini.cooper"
    assert got.role_name == "npc"
    assert got.x == 10.0
    assert got.y == 11.0
    assert got.z == 12.0


def test_vehicle_spawner_adapter_falls_back_to_requested_role_name(monkeypatch) -> None:
    world = object()

    def fake_spawn_vehicle(**kwargs: Any) -> _FakeActorNoRole:
        return _FakeActorNoRole()

    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.vehicle_spawner_adapter.spawn_vehicle",
        fake_spawn_vehicle,
    )

    adapter = CarlaVehicleSpawnerAdapter(world=world)
    request = SpawnVehicleRequest(
        blueprint_filter="vehicle.lincoln.mkz_2020",
        spawn_x=1.0,
        spawn_y=2.0,
        spawn_z=3.0,
        spawn_yaw=180.0,
        role_name="ego",
    )

    got = adapter.spawn(request)

    assert got.actor_id == 88
    assert got.role_name == "ego"

