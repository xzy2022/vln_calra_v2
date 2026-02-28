"""CARLA world adapter for spectator transform operations."""

from __future__ import annotations

from typing import Any

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.infrastructure.carla.types import require_carla
from vln_carla2.usecases.runtime.ports.spectator_transform import SpectatorTransform


class CarlaWorldAdapter:
    """Minimal adapter exposing spectator transform read/write."""

    def __init__(self, world: Any) -> None:
        self._world = world

    def get_spectator_transform(self) -> SpectatorTransform:
        spectator = self._world.get_spectator()
        return spectator.get_transform()

    def set_spectator_transform(self, transform: SpectatorTransform) -> None:
        spectator = self._world.get_spectator()
        spectator.set_transform(transform)

    def get_vehicle_transform(self, actor_id: int | VehicleId) -> SpectatorTransform | None:
        if isinstance(actor_id, VehicleId):
            actor_id = actor_id.value
        actor = self._world.get_actor(actor_id)
        if actor is None:
            return None
        return actor.get_transform()

    def resolve_ground_z(self, x: float, y: float) -> float:
        """Resolve road-projected ground Z for the given XY."""
        carla = require_carla()
        world_map = self._world.get_map()
        location = carla.Location(x=float(x), y=float(y), z=0.0)
        waypoint = world_map.get_waypoint(location, project_to_road=True)
        if waypoint is None:
            raise RuntimeError(
                f"no road waypoint found near spectator XY (x={x:.3f}, y={y:.3f})"
            )
        return float(waypoint.transform.location.z)

