"""A minimal speed controller for slice-0."""

from dataclasses import dataclass

from vln_carla2.domain.model.simple_command import ControlCommand, TargetSpeedCommand
from vln_carla2.domain.model.vehicle_state import VehicleState


@dataclass(slots=True)
class SimpleSpeedController:
    """P-style speed controller with separate gains for throttle and brake."""

    throttle_gain: float = 0.35
    brake_gain: float = 0.55
    speed_tolerance: float = 0.2

    def compute(self, state: VehicleState, target: TargetSpeedCommand) -> ControlCommand:
        error = target.target_speed_mps - state.speed_mps
        if abs(error) <= self.speed_tolerance:
            return ControlCommand(throttle=0.0, brake=0.0, steer=0.0)
        if error > 0.0:
            throttle = min(1.0, max(0.0, error * self.throttle_gain))
            return ControlCommand(throttle=throttle, brake=0.0, steer=0.0)
        brake = min(1.0, max(0.0, (-error) * self.brake_gain))
        return ControlCommand(throttle=0.0, brake=brake, steer=0.0)

