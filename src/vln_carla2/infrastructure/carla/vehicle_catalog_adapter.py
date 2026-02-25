"""CARLA adapter for listing vehicle descriptors."""

from __future__ import annotations

from typing import Any

from vln_carla2.infrastructure.carla._vehicle_mapper import (
    iter_vehicle_actors,
    to_vehicle_descriptor,
)
from vln_carla2.usecases.operator.models import VehicleDescriptor
from vln_carla2.usecases.operator.ports.vehicle_catalog import VehicleCatalogPort


class CarlaVehicleCatalogAdapter(VehicleCatalogPort):
    """Read all vehicle actors from CARLA world."""

    def __init__(self, world: Any) -> None:
        self._world = world

    def list_vehicles(self) -> list[VehicleDescriptor]:
        actors = list(iter_vehicle_actors(self._world))
        actors.sort(key=lambda actor: int(actor.id))
        return [to_vehicle_descriptor(actor) for actor in actors]
