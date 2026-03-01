"""Use case for running an agent-based closed-loop vehicle control."""

from dataclasses import dataclass
from typing import Callable

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.model.vehicle_state import VehicleState
from vln_carla2.usecases.control.ports.clock import Clock
from vln_carla2.usecases.control.ports.logger import Logger
from vln_carla2.usecases.control.ports.motion_actuator import MotionActuator
from vln_carla2.usecases.control.ports.navigation_agent import NavigationAgent
from vln_carla2.usecases.control.ports.vehicle_state_reader import VehicleStateReader
from vln_carla2.usecases.control.run_control_loop import LoopResult


@dataclass(slots=True)
class RunAgentControlLoop:
    """Read state -> ask navigation agent -> apply -> tick."""

    state_reader: VehicleStateReader
    motion_actuator: MotionActuator
    clock: Clock
    logger: Logger
    navigation_agent: NavigationAgent

    def run(
        self,
        *,
        vehicle_id: VehicleId,
        target_speed_mps: float,
        destination_x: float,
        destination_y: float,
        destination_z: float,
        max_steps: int,
        before_step: Callable[[int], None] | None = None,
        on_state: Callable[[VehicleState], None] | None = None,
    ) -> LoopResult:
        if max_steps <= 0:
            raise ValueError("max_steps must be > 0")
        if target_speed_mps < 0:
            raise ValueError("target_speed_mps must be >= 0")

        self.navigation_agent.configure_target_speed_mps(target_speed_mps)
        self.navigation_agent.set_destination(
            destination_x,
            destination_y,
            destination_z,
        )

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

            if self.navigation_agent.done():
                self.logger.info(
                    "step="
                    f"{step} agent_done=true speed_mps={state.speed_mps:.3f} "
                    f"frame={state.frame}"
                )
                break

            command = self.navigation_agent.run_step()
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

