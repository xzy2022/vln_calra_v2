"""CARLA adapter that reads state into domain objects."""

import math
from typing import Any

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.model.vehicle_state import VehicleState
from vln_carla2.usecases.ports.vehicle_state_reader import VehicleStateReader


class CarlaVehicleStateReader(VehicleStateReader):
    """Read actor transform and velocity from CARLA."""

    def __init__(self, world: Any) -> None:
        self._world = world

    def read(self, vehicle_id: VehicleId) -> VehicleState:
        vehicle = self._require_vehicle(vehicle_id)

        transform = vehicle.get_transform()
        velocity = vehicle.get_velocity()
        speed_mps = math.sqrt(
            velocity.x * velocity.x + velocity.y * velocity.y + velocity.z * velocity.z
        )
        frame = int(self._world.get_snapshot().frame)

        return VehicleState(
            frame=frame,
            x=float(transform.location.x),
            y=float(transform.location.y),
            z=float(transform.location.z),
            yaw_deg=float(transform.rotation.yaw),
            vx=float(velocity.x),
            vy=float(velocity.y),
            vz=float(velocity.z),
            speed_mps=float(speed_mps),
        )

    def _require_vehicle(self, vehicle_id: VehicleId) -> Any:
        actor = self._world.get_actor(vehicle_id.value)
        if actor is None:
            raise RuntimeError(f"Vehicle actor not found: id={vehicle_id.value}")
        return actor

