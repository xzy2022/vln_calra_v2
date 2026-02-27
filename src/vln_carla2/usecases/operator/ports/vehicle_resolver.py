"""Port for resolving generic vehicle references."""

from typing import Protocol

from vln_carla2.domain.model.vehicle_ref import VehicleRef
from vln_carla2.usecases.operator.ports.vehicle_dto import VehicleDescriptor


class VehicleResolverPort(Protocol):
    """Resolve a VehicleRef to one concrete vehicle descriptor."""

    def resolve(self, ref: VehicleRef) -> VehicleDescriptor | None:
        ...
