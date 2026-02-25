from dataclasses import dataclass

from vln_carla2.infrastructure.carla.vehicle_catalog_adapter import CarlaVehicleCatalogAdapter


@dataclass
class _Location:
    x: float
    y: float
    z: float


@dataclass
class _Transform:
    location: _Location


class _FakeActor:
    def __init__(
        self,
        actor_id: int,
        type_id: str,
        role_name: str,
        location: _Location,
    ) -> None:
        self.id = actor_id
        self.type_id = type_id
        self.attributes = {"role_name": role_name}
        self._transform = _Transform(location=location)

    def get_transform(self) -> _Transform:
        return self._transform


class _FakeActorList(list):
    def filter(self, pattern: str):  # noqa: ANN204 - CARLA-like API
        if pattern != "vehicle.*":
            return []
        return [actor for actor in self if str(actor.type_id).startswith("vehicle.")]


class _FakeWorld:
    def __init__(self, actors: list[_FakeActor]) -> None:
        self._actors = _FakeActorList(actors)

    def get_actors(self) -> _FakeActorList:
        return self._actors


def test_vehicle_catalog_adapter_lists_sorted_vehicle_descriptors() -> None:
    world = _FakeWorld(
        actors=[
            _FakeActor(20, "walker.pedestrian.0001", "", _Location(9.0, 9.0, 9.0)),
            _FakeActor(8, "vehicle.audi.tt", "npc", _Location(1.0, 2.0, 0.1)),
            _FakeActor(3, "vehicle.tesla.model3", "ego", _Location(3.0, 4.0, 0.2)),
        ]
    )
    adapter = CarlaVehicleCatalogAdapter(world=world)

    got = adapter.list_vehicles()

    assert [item.actor_id for item in got] == [3, 8]
    assert got[0].type_id == "vehicle.tesla.model3"
    assert got[0].role_name == "ego"
    assert got[0].x == 3.0
    assert got[0].y == 4.0
    assert got[0].z == 0.2
