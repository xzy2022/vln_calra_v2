"""Use case for listing known vehicles in current world."""

from dataclasses import dataclass

from vln_carla2.usecases.operator.ports.vehicle_dto import VehicleDescriptor
from vln_carla2.usecases.operator.ports.vehicle_catalog import VehicleCatalogPort


@dataclass(slots=True)
class ListVehicles:
    """Return all vehicle descriptors from the catalog port."""

    catalog: VehicleCatalogPort

    def run(self) -> list[VehicleDescriptor]:
        return self.catalog.list_vehicles()
