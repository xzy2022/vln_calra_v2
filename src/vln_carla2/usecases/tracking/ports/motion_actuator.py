"""Motion actuator port for tracking use case."""

from typing import Protocol

from vln_carla2.domain.model.simple_command import ControlCommand
from vln_carla2.domain.model.vehicle_id import VehicleId


class MotionActuator(Protocol):
    """Applies one control command to tracked vehicle."""

    def apply(self, vehicle_id: VehicleId, command: ControlCommand) -> None:
        ...

