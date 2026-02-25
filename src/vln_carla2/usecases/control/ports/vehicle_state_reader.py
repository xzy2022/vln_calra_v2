"""Vehicle state read port."""

from typing import Protocol

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.model.vehicle_state import VehicleState


class VehicleStateReader(Protocol):
    """Reads domain vehicle state for a specific vehicle."""

    def read(self, vehicle_id: VehicleId) -> VehicleState:
        """Read latest state from the runtime."""
        ...

