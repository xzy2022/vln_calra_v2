"""Spawn one vehicle at current spectator XY with fixed Z and yaw."""

from __future__ import annotations

from dataclasses import dataclass

from vln_carla2.usecases.operator.models import SpawnVehicleRequest, VehicleDescriptor
from vln_carla2.usecases.operator.spawn_vehicle import SpawnVehicle
from vln_carla2.usecases.spectator.ports.spectator_camera import SpectatorCameraPort


@dataclass(slots=True)
class SpawnVehicleAtSpectatorXY:
    """Read spectator XY and spawn one vehicle at fixed Z."""

    spectator_camera: SpectatorCameraPort
    spawn_vehicle: SpawnVehicle
    blueprint_filter: str = "vehicle.tesla.model3"
    spawn_z: float = 0.15
    spawn_yaw: float = 180.0
    role_name: str = "ego"

    def run(self) -> VehicleDescriptor:
        spectator_transform = self.spectator_camera.get_spectator_transform()
        request = SpawnVehicleRequest(
            blueprint_filter=self.blueprint_filter,
            spawn_x=float(spectator_transform.location.x),
            spawn_y=float(spectator_transform.location.y),
            spawn_z=float(self.spawn_z),
            spawn_yaw=float(self.spawn_yaw),
            role_name=self.role_name,
        )
        return self.spawn_vehicle.run(request)
