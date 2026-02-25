"""CARLA world adapter for spectator transform operations."""

from __future__ import annotations

from typing import Any

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.usecases.ports.spectator_world import SpectatorTransform


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

    def get_vehicle_transform(self, vehicle_id: VehicleId) -> SpectatorTransform | None:
        actor = self._world.get_actor(vehicle_id.value)
        if actor is None:
            return None
        return actor.get_transform()
