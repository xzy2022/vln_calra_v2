"""Domain commands for the slice-0 control loop."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetSpeedCommand:
    """Simple intent: maintain a target speed in m/s."""

    target_speed_mps: float

    def __post_init__(self) -> None:
        if self.target_speed_mps < 0.0:
            raise ValueError("target_speed_mps must be >= 0")


@dataclass(frozen=True, slots=True)
class ControlCommand:
    """Low-level control request mapped to carla.VehicleControl."""

    throttle: float
    brake: float
    steer: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.throttle <= 1.0:
            raise ValueError("throttle must be in [0, 1]")
        if not 0.0 <= self.brake <= 1.0:
            raise ValueError("brake must be in [0, 1]")
        if not -1.0 <= self.steer <= 1.0:
            raise ValueError("steer must be in [-1, 1]")
        if self.throttle > 0.0 and self.brake > 0.0:
            raise ValueError("throttle and brake cannot both be positive")

