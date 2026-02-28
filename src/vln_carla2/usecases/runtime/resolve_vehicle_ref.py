"""Use case for resolving VehicleRef into one vehicle."""

from dataclasses import dataclass

from vln_carla2.domain.model.vehicle_ref import VehicleRef
from vln_carla2.usecases.shared.vehicle_ref import VehicleRefInput
from vln_carla2.usecases.runtime.ports.vehicle_dto import VehicleDescriptor
from vln_carla2.usecases.runtime.ports.vehicle_resolver import VehicleResolverPort


@dataclass(slots=True)
class ResolveVehicleRef:
    """Resolve one generic vehicle reference."""

    resolver: VehicleResolverPort

    def run(self, ref: VehicleRefInput) -> VehicleDescriptor | None:
        return self.resolver.resolve(VehicleRef(scheme=ref.scheme, value=ref.value))


