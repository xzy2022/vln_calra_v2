from dataclasses import dataclass

from vln_carla2.domain.model.vehicle_ref import VehicleRef
from vln_carla2.infrastructure.carla.vehicle_resolver_adapter import CarlaVehicleResolverAdapter


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

    def get_actor(self, actor_id: int) -> _FakeActor | None:
        for actor in self._actors:
            if actor.id == actor_id:
                return actor
        return None

    def get_actors(self) -> _FakeActorList:
        return self._actors


def test_vehicle_resolver_resolves_actor_reference() -> None:
    world = _FakeWorld(
        actors=[
            _FakeActor(4, "vehicle.tesla.model3", "ego", _Location(1.0, 2.0, 0.5)),
            _FakeActor(8, "vehicle.audi.tt", "npc", _Location(3.0, 4.0, 0.6)),
        ]
    )
    adapter = CarlaVehicleResolverAdapter(world=world)

    got = adapter.resolve(VehicleRef(scheme="actor", value="8"))

    assert got is not None
    assert got.actor_id == 8
    assert got.role_name == "npc"


def test_vehicle_resolver_resolves_role_reference_with_stable_order() -> None:
    world = _FakeWorld(
        actors=[
            _FakeActor(30, "vehicle.audi.tt", "ego", _Location(9.0, 9.0, 0.0)),
            _FakeActor(2, "vehicle.tesla.model3", "ego", _Location(1.0, 1.0, 0.0)),
        ]
    )
    adapter = CarlaVehicleResolverAdapter(world=world)

    got = adapter.resolve(VehicleRef(scheme="role", value="ego"))

    assert got is not None
    assert got.actor_id == 2
    assert got.type_id == "vehicle.tesla.model3"


def test_vehicle_resolver_resolves_first_reference_with_stable_order() -> None:
    world = _FakeWorld(
        actors=[
            _FakeActor(20, "vehicle.audi.tt", "npc", _Location(2.0, 0.0, 0.0)),
            _FakeActor(5, "vehicle.tesla.model3", "ego", _Location(3.0, 0.0, 0.0)),
        ]
    )
    adapter = CarlaVehicleResolverAdapter(world=world)

    got = adapter.resolve(VehicleRef(scheme="first", value=None))

    assert got is not None
    assert got.actor_id == 5
    assert got.type_id == "vehicle.tesla.model3"


def test_vehicle_resolver_returns_none_when_unresolvable() -> None:
    world = _FakeWorld(
        actors=[
            _FakeActor(1, "walker.pedestrian.0001", "", _Location(0.0, 0.0, 0.0)),
            _FakeActor(2, "vehicle.audi.tt", "npc", _Location(1.0, 1.0, 0.0)),
        ]
    )
    adapter = CarlaVehicleResolverAdapter(world=world)

    missing_actor = adapter.resolve(VehicleRef(scheme="actor", value="999"))
    missing_role = adapter.resolve(VehicleRef(scheme="role", value="ego"))
    actor_non_vehicle = adapter.resolve(VehicleRef(scheme="actor", value="1"))

    assert missing_actor is None
    assert missing_role is None
    assert actor_non_vehicle is None
