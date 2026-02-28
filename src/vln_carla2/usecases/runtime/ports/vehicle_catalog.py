"""Port for reading currently available vehicle actors."""

from typing import Protocol

from vln_carla2.usecases.runtime.ports.vehicle_dto import VehicleDescriptor


class VehicleCatalogPort(Protocol):
    """List vehicles visible in the current runtime context."""

    def list_vehicles(self) -> list[VehicleDescriptor]:
        ...

