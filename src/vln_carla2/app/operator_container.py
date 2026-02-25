"""Dependency wiring for the operator-track runtime."""

from dataclasses import dataclass
from typing import Any

from vln_carla2.adapters.cli.keyboard_input_windows import KeyboardInputWindows
from vln_carla2.adapters.cli.runtime import CliRuntime
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.infrastructure.carla.vehicle_catalog_adapter import CarlaVehicleCatalogAdapter
from vln_carla2.infrastructure.carla.vehicle_resolver_adapter import CarlaVehicleResolverAdapter
from vln_carla2.infrastructure.carla.vehicle_spawner_adapter import CarlaVehicleSpawnerAdapter
from vln_carla2.infrastructure.carla.world_adapter import CarlaWorldAdapter
from vln_carla2.usecases.spectator.follow_vehicle_topdown import FollowVehicleTopDown
from vln_carla2.usecases.spectator.move_spectator import MoveSpectator
from vln_carla2.usecases.operator.list_vehicles import ListVehicles
from vln_carla2.usecases.operator.resolve_vehicle_ref import ResolveVehicleRef
from vln_carla2.usecases.operator.spawn_vehicle import SpawnVehicle


@dataclass(slots=True)
class OperatorContainer:
    """Built runtime dependencies for operator-facing loop."""

    runtime: CliRuntime
    list_vehicles: ListVehicles
    spawn_vehicle: SpawnVehicle
    resolve_vehicle_ref: ResolveVehicleRef


def build_operator_container(
    *,
    world: Any,
    synchronous_mode: bool,
    sleep_seconds: float,
    follow_vehicle_id: int | None = None,
    spectator_initial_z: float = 20.0,
    spectator_min_z: float = -20.0,
    spectator_max_z: float = 120.0,
) -> OperatorContainer:
    """Compose operator loop dependencies and produce a runtime."""
    vehicle_catalog = CarlaVehicleCatalogAdapter(world)
    vehicle_spawner = CarlaVehicleSpawnerAdapter(world)
    vehicle_resolver = CarlaVehicleResolverAdapter(world)

    keyboard_input = None
    move_spectator = None
    follow_vehicle_topdown = None

    if hasattr(world, "get_spectator"):
        world_adapter = CarlaWorldAdapter(world)
        _initialize_spectator_top_down(
            world_adapter=world_adapter,
            initial_z=spectator_initial_z,
        )
        keyboard_input = KeyboardInputWindows()
        move_spectator = MoveSpectator(
            world=world_adapter,
            min_z=spectator_min_z,
            max_z=spectator_max_z,
        )
        if follow_vehicle_id is not None:
            follow_vehicle_topdown = FollowVehicleTopDown(
                world=world_adapter,
                vehicle_id=VehicleId(follow_vehicle_id),
                z=spectator_initial_z,
            )

    runtime = CliRuntime(
        world=world,
        synchronous_mode=synchronous_mode,
        sleep_seconds=sleep_seconds,
        keyboard_input=keyboard_input,
        move_spectator=move_spectator,
        follow_vehicle_topdown=follow_vehicle_topdown,
    )
    return OperatorContainer(
        runtime=runtime,
        list_vehicles=ListVehicles(catalog=vehicle_catalog),
        spawn_vehicle=SpawnVehicle(spawner=vehicle_spawner),
        resolve_vehicle_ref=ResolveVehicleRef(resolver=vehicle_resolver),
    )


def _initialize_spectator_top_down(*, world_adapter: CarlaWorldAdapter, initial_z: float) -> None:
    transform = world_adapter.get_spectator_transform()
    transform.location.z = initial_z
    transform.rotation.pitch = -90.0
    transform.rotation.yaw = 0.0
    transform.rotation.roll = 0.0
    world_adapter.set_spectator_transform(transform)
