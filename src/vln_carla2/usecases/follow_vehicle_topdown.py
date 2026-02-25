"""Use case for locking spectator to top-down vehicle follow view."""

from __future__ import annotations

from dataclasses import dataclass

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.usecases.ports.spectator_world import SpectatorWorld


@dataclass(slots=True)
class FollowVehicleTopDown:
    """Follow target vehicle on XY while locking spectator at fixed top-down Z."""

    world: SpectatorWorld
    vehicle_id: VehicleId
    z: float = 20.0

    def follow_once(self) -> bool:
        vehicle_transform = self.world.get_vehicle_transform(self.vehicle_id)
        if vehicle_transform is None:
            return False

        spectator_transform = self.world.get_spectator_transform()
        spectator_transform.location.x = vehicle_transform.location.x
        spectator_transform.location.y = vehicle_transform.location.y
        spectator_transform.location.z = self.z
        spectator_transform.rotation.pitch = -90.0
        spectator_transform.rotation.yaw = 0.0
        spectator_transform.rotation.roll = 0.0
        self.world.set_spectator_transform(spectator_transform)
        return True
