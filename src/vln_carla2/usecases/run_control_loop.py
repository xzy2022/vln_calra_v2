"""Use case for running a minimal closed-loop vehicle control."""

from dataclasses import dataclass
from typing import Protocol

from vln_carla2.domain.model.simple_command import ControlCommand, TargetSpeedCommand
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.model.vehicle_state import VehicleState
from vln_carla2.usecases.ports.clock import Clock
from vln_carla2.usecases.ports.logger import Logger
from vln_carla2.usecases.ports.motion_actuator import MotionActuator
from vln_carla2.usecases.ports.vehicle_state_reader import VehicleStateReader


class SpeedController(Protocol):
    """Protocol for speed controller implementations."""

    def compute(self, state: VehicleState, target: TargetSpeedCommand) -> ControlCommand:
        """Compute control command from state and target."""


@dataclass(frozen=True, slots=True)
class LoopResult:
    """Summary of a finished control loop execution."""

    steps: int
    last_speed_mps: float
    avg_speed_mps: float
    last_frame: int


@dataclass(slots=True)
class RunControlLoop:
    """Read state -> compute command -> apply -> tick."""

    state_reader: VehicleStateReader
    motion_actuator: MotionActuator
    clock: Clock
    logger: Logger
    controller: SpeedController

    def run(self, vehicle_id: VehicleId, target: TargetSpeedCommand, max_steps: int) -> LoopResult:
        if max_steps <= 0:
            raise ValueError("max_steps must be > 0")

        speed_samples: list[float] = []
        last_speed_mps = 0.0
        last_frame = -1

        for step in range(1, max_steps + 1):
            state = self.state_reader.read(vehicle_id)
            command = self.controller.compute(state, target)
            self.motion_actuator.apply(vehicle_id, command)
            frame = self.clock.tick()

            self.logger.info(
                "step="
                f"{step} frame={frame} speed_mps={state.speed_mps:.3f} "
                f"throttle={command.throttle:.3f} brake={command.brake:.3f}"
            )

            speed_samples.append(state.speed_mps)
            last_speed_mps = state.speed_mps
            last_frame = frame

        avg_speed_mps = sum(speed_samples) / len(speed_samples)
        return LoopResult(
            steps=max_steps,
            last_speed_mps=last_speed_mps,
            avg_speed_mps=avg_speed_mps,
            last_frame=last_frame,
        )

