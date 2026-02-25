"""CARLA adapter for spawning vehicles through operator port."""

from __future__ import annotations

from typing import Any

from vln_carla2.infrastructure.carla._vehicle_mapper import to_vehicle_descriptor
from vln_carla2.infrastructure.carla.spawner import spawn_vehicle
from vln_carla2.usecases.operator.models import SpawnVehicleRequest, VehicleDescriptor
from vln_carla2.usecases.operator.ports.vehicle_spawner import VehicleSpawnerPort


class CarlaVehicleSpawnerAdapter(VehicleSpawnerPort):
    """Spawn vehicle actor and map to VehicleDescriptor."""

    def __init__(self, world: Any) -> None:
        self._world = world

    def spawn(self, request: SpawnVehicleRequest) -> VehicleDescriptor:
        actor = spawn_vehicle(
            world=self._world,
            blueprint_filter=request.blueprint_filter,
            spawn_x=request.spawn_x,
            spawn_y=request.spawn_y,
            spawn_z=request.spawn_z,
            spawn_yaw=request.spawn_yaw,
            role_name=request.role_name,
        )
        return to_vehicle_descriptor(
            actor,
            default_role_name=request.role_name,
        )
