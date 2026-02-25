"""Use case for locking spectator to top-down vehicle follow view."""

from __future__ import annotations

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.usecases.operator.ports.spectator_camera import SpectatorCameraPort
from vln_carla2.usecases.operator.ports.vehicle_pose import VehiclePosePort


class FollowVehicleTopDown:
    """Follow target vehicle on XY while locking spectator at fixed top-down Z."""

    __slots__ = ("spectator_camera", "vehicle_pose", "vehicle_id", "z")

    def __init__(
        self,
        *,
        spectator_camera: SpectatorCameraPort,
        vehicle_pose: VehiclePosePort,
        vehicle_id: VehicleId,
        z: float = 20.0,
    ) -> None:
        self.spectator_camera = spectator_camera
        self.vehicle_pose = vehicle_pose
        self.vehicle_id = vehicle_id
        self.z = z

    def follow_once(self) -> bool:
        vehicle_transform = self.vehicle_pose.get_vehicle_transform(self.vehicle_id.value)
        if vehicle_transform is None:
            return False

        spectator_transform = self.spectator_camera.get_spectator_transform()
        spectator_transform.location.x = vehicle_transform.location.x
        spectator_transform.location.y = vehicle_transform.location.y
        spectator_transform.location.z = self.z
        spectator_transform.rotation.pitch = -90.0
        spectator_transform.rotation.yaw = 0.0
        spectator_transform.rotation.roll = 0.0
        self.spectator_camera.set_spectator_transform(spectator_transform)
        return True
