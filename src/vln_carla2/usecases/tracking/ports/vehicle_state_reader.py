"""Vehicle state read port for tracking use case."""

from typing import Protocol

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.model.vehicle_state import VehicleState


class VehicleStateReader(Protocol):
    """Reads domain vehicle state for one tracked vehicle."""

    def read(self, vehicle_id: VehicleId) -> VehicleState:
        ...

