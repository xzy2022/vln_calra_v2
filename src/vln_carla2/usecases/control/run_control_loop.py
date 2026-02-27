"""Use case for running a minimal closed-loop vehicle control."""

from dataclasses import dataclass
from typing import Callable, Protocol

from vln_carla2.domain.model.simple_command import ControlCommand, TargetSpeedCommand
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.model.vehicle_state import VehicleState
from vln_carla2.usecases.control.ports.clock import Clock
from vln_carla2.usecases.control.ports.logger import Logger
from vln_carla2.usecases.control.ports.motion_actuator import MotionActuator
from vln_carla2.usecases.control.ports.vehicle_state_reader import VehicleStateReader


class SpeedController(Protocol):
    """Protocol for speed controller implementations."""

    def compute(self, state: VehicleState, target: TargetSpeedCommand) -> ControlCommand:
        """Compute control command from state and target."""
        ...


@dataclass(frozen=True, slots=True)
class LoopResult:
    """Summary of a finished control loop execution."""

    executed_steps: int
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

    def run(
        self,
        vehicle_id: VehicleId,
        target: TargetSpeedCommand,
        max_steps: int,
        before_step: Callable[[int], None] | None = None,
        on_state: Callable[[VehicleState], None] | None = None,
        stop_before_apply: Callable[[int, VehicleState], bool] | None = None,
    ) -> LoopResult:
        if max_steps <= 0:
            raise ValueError("max_steps must be > 0")

        speed_samples: list[float] = []
        last_speed_mps = 0.0
        last_frame = -1
        executed_steps = 0

        for step in range(1, max_steps + 1):
            if before_step is not None:
                before_step(step)
            state = self.state_reader.read(vehicle_id)
            if on_state is not None:
                on_state(state)
            if stop_before_apply is not None and stop_before_apply(step, state):
                self.logger.info(
                    "step="
                    f"{step} stop_before_apply=true speed_mps={state.speed_mps:.3f} "
                    f"frame={state.frame}"
                )
                break
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
            executed_steps += 1

        avg_speed_mps = sum(speed_samples) / len(speed_samples) if speed_samples else 0.0
        return LoopResult(
            executed_steps=executed_steps,
            last_speed_mps=last_speed_mps,
            avg_speed_mps=avg_speed_mps,
            last_frame=last_frame,
        )
