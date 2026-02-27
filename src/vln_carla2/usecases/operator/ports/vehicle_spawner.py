"""Port for spawning a new vehicle actor."""

from typing import Protocol

from vln_carla2.usecases.operator.ports.vehicle_dto import SpawnVehicleRequest, VehicleDescriptor


class VehicleSpawnerPort(Protocol):
    """Spawn a vehicle and return its descriptor."""

    def spawn(self, request: SpawnVehicleRequest) -> VehicleDescriptor:
        ...
