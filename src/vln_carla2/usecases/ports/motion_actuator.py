"""Motion actuator port."""

from typing import Protocol

from vln_carla2.domain.model.simple_command import ControlCommand
from vln_carla2.domain.model.vehicle_id import VehicleId


class MotionActuator(Protocol):
    """Applies control command for a specific vehicle."""

    def apply(self, vehicle_id: VehicleId, command: ControlCommand) -> None:
        """Apply control command to runtime."""

