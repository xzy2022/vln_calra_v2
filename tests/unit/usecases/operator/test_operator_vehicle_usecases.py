from dataclasses import dataclass

from vln_carla2.domain.model.vehicle_ref import VehicleRef
from vln_carla2.usecases.operator.list_vehicles import ListVehicles
from vln_carla2.usecases.operator.models import VehicleRefInput
from vln_carla2.usecases.operator.ports.vehicle_dto import SpawnVehicleRequest, VehicleDescriptor
from vln_carla2.usecases.operator.resolve_vehicle_ref import ResolveVehicleRef
from vln_carla2.usecases.operator.spawn_vehicle import SpawnVehicle


@dataclass
class _FakeCatalog:
    vehicles: list[VehicleDescriptor]

    def list_vehicles(self) -> list[VehicleDescriptor]:
        return self.vehicles


@dataclass
class _FakeSpawner:
    created: VehicleDescriptor
    calls: list[SpawnVehicleRequest]

    def spawn(self, request: SpawnVehicleRequest) -> VehicleDescriptor:
        self.calls.append(request)
        return self.created


@dataclass
class _FakeResolver:
    resolved: VehicleDescriptor | None
    calls: list[VehicleRef]

    def resolve(self, ref: VehicleRef) -> VehicleDescriptor | None:
        self.calls.append(ref)
        return self.resolved


def test_list_vehicles_returns_catalog_output() -> None:
    expected = [
        VehicleDescriptor(
            actor_id=10,
            type_id="vehicle.tesla.model3",
            role_name="ego",
            x=1.0,
            y=2.0,
            z=3.0,
        )
    ]
    usecase = ListVehicles(catalog=_FakeCatalog(vehicles=expected))

    got = usecase.run()

    assert got == expected


def test_spawn_vehicle_calls_spawner_and_returns_descriptor() -> None:
    expected = VehicleDescriptor(
        actor_id=11,
        type_id="vehicle.mini.cooper",
        role_name="npc",
        x=4.0,
        y=5.0,
        z=6.0,
    )
    fake_spawner = _FakeSpawner(created=expected, calls=[])
    usecase = SpawnVehicle(spawner=fake_spawner)
    request = SpawnVehicleRequest(
        blueprint_filter="vehicle.mini.cooper",
        spawn_x=10.0,
        spawn_y=20.0,
        spawn_z=0.3,
        spawn_yaw=90.0,
        role_name="npc",
    )

    got = usecase.run(request)

    assert got == expected
    assert fake_spawner.calls == [request]


def test_resolve_vehicle_ref_calls_resolver_and_returns_result() -> None:
    expected = VehicleDescriptor(
        actor_id=12,
        type_id="vehicle.audi.tt",
        role_name="ego",
        x=7.0,
        y=8.0,
        z=9.0,
    )
    fake_resolver = _FakeResolver(resolved=expected, calls=[])
    usecase = ResolveVehicleRef(resolver=fake_resolver)
    reference = VehicleRefInput(scheme="role", value="ego")

    got = usecase.run(reference)

    assert got == expected
    assert fake_resolver.calls == [VehicleRef(scheme="role", value="ego")]
