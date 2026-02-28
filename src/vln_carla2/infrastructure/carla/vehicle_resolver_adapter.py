"""CARLA adapter for resolving VehicleRef values."""

from __future__ import annotations

from typing import Any

from vln_carla2.domain.model.vehicle_ref import VehicleRef
from vln_carla2.infrastructure.carla._vehicle_mapper import (
    is_vehicle_actor,
    iter_vehicle_actors,
    role_name,
    to_vehicle_descriptor,
)
from vln_carla2.usecases.runtime.ports.vehicle_dto import VehicleDescriptor
from vln_carla2.usecases.runtime.ports.vehicle_resolver import VehicleResolverPort


class CarlaVehicleResolverAdapter(VehicleResolverPort):
    """Resolve actor/role/first reference against current world actors."""

    def __init__(self, world: Any) -> None:
        self._world = world

    def resolve(self, ref: VehicleRef) -> VehicleDescriptor | None:
        if ref.scheme == "actor":
            actor = self._world.get_actor(int(ref.value or "0"))
            if actor is None or not is_vehicle_actor(actor):
                return None
            return to_vehicle_descriptor(actor)

        vehicles = list(iter_vehicle_actors(self._world))
        if ref.scheme == "role":
            candidates = [actor for actor in vehicles if role_name(actor) == (ref.value or "")]
            if not candidates:
                return None
            candidates.sort(key=lambda actor: int(actor.id))
            return to_vehicle_descriptor(candidates[0])

        if ref.scheme == "first":
            if not vehicles:
                return None
            vehicles.sort(key=lambda actor: int(actor.id))
            return to_vehicle_descriptor(vehicles[0])

        return None

