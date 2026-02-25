"""Domain value objects for vehicle control."""

from .simple_command import ControlCommand, TargetSpeedCommand
from .vehicle_id import VehicleId
from .vehicle_ref import VehicleRef
from .vehicle_state import VehicleState

__all__ = ["VehicleId", "VehicleRef", "VehicleState", "TargetSpeedCommand", "ControlCommand"]
