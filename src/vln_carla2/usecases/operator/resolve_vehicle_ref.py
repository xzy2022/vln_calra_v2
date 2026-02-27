"""Use case for resolving VehicleRef into one vehicle."""

from dataclasses import dataclass

from vln_carla2.domain.model.vehicle_ref import VehicleRef
from vln_carla2.usecases.operator.ports.vehicle_dto import VehicleDescriptor
from vln_carla2.usecases.operator.ports.vehicle_resolver import VehicleResolverPort


@dataclass(slots=True)
class ResolveVehicleRef:
    """Resolve one generic vehicle reference."""

    resolver: VehicleResolverPort

    def run(self, ref: VehicleRef) -> VehicleDescriptor | None:
        return self.resolver.resolve(ref)
