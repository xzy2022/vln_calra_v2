"""CARLA adapter that reads state into domain objects."""

import math
from typing import Any

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.model.vehicle_state import VehicleState
from vln_carla2.usecases.control.ports.vehicle_state_reader import VehicleStateReader


class CarlaVehicleStateReader(VehicleStateReader):
    """Read actor transform and velocity from CARLA."""

    def __init__(self, world: Any) -> None:
        self._world = world

    def read(self, vehicle_id: VehicleId) -> VehicleState:
        vehicle = self._require_vehicle(vehicle_id)

        transform = vehicle.get_transform()
        probe_points = self._forbidden_zone_probe_points(vehicle=vehicle, transform=transform)
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
            forbidden_zone_probe_points_xy=probe_points,
        )

    def _require_vehicle(self, vehicle_id: VehicleId) -> Any:
        actor = self._world.get_actor(vehicle_id.value)
        if actor is None:
            raise RuntimeError(f"Vehicle actor not found: id={vehicle_id.value}")
        return actor

    def _forbidden_zone_probe_points(
        self,
        *,
        vehicle: Any,
        transform: Any,
    ) -> tuple[tuple[float, float], ...]:
        bounding_box = getattr(vehicle, "bounding_box", None)
        if bounding_box is None:
            raise RuntimeError(f"Vehicle bounding_box is missing: id={int(vehicle.id)}")

        try:
            vertices = list(bounding_box.get_world_vertices(transform))
        except Exception as exc:  # pragma: no cover - defensive against CARLA runtime errors
            raise RuntimeError(
                f"Failed to get world bbox vertices for vehicle: id={int(vehicle.id)}"
            ) from exc

        if len(vertices) < 4:
            raise RuntimeError(
                "Vehicle bounding_box has fewer than 4 vertices: "
                f"id={int(vehicle.id)} count={len(vertices)}"
            )

        center_x = sum(float(vertex.x) for vertex in vertices) / len(vertices)
        center_y = sum(float(vertex.y) for vertex in vertices) / len(vertices)
        bottom_vertices = sorted(vertices, key=lambda vertex: float(vertex.z))[:4]
        bottom_points = tuple((float(vertex.x), float(vertex.y)) for vertex in bottom_vertices)
        return ((center_x, center_y),) + bottom_points
