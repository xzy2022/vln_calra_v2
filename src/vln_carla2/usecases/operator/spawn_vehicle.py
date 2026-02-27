"""Use case for spawning one vehicle actor."""

from dataclasses import dataclass

from vln_carla2.usecases.operator.ports.vehicle_dto import SpawnVehicleRequest, VehicleDescriptor
from vln_carla2.usecases.operator.ports.vehicle_spawner import VehicleSpawnerPort


@dataclass(slots=True)
class SpawnVehicle:
    """Spawn one vehicle and return the created descriptor."""

    spawner: VehicleSpawnerPort

    def run(self, request: SpawnVehicleRequest) -> VehicleDescriptor:
        return self.spawner.spawn(request)
