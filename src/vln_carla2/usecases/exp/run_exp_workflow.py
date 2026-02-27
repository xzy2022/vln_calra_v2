"""Use case for experiment workflow with forward motion and zone checks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from vln_carla2.domain.model.forbidden_zone import ForbiddenZone
from vln_carla2.domain.model.simple_command import TargetSpeedCommand
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.model.vehicle_state import VehicleState
from vln_carla2.domain.services.forbidden_zone_rules import has_entered_forbidden_zone
from vln_carla2.usecases.control.run_control_loop import LoopResult, RunControlLoop


class FollowVehicleProtocol(Protocol):
    """Protocol for one-step spectator follow operation."""

    def follow_once(self) -> bool:
        ...


@dataclass(frozen=True, slots=True)
class ExpWorkflowRequest:
    """Input payload for one experiment workflow run."""

    vehicle_id: VehicleId
    forbidden_zone: ForbiddenZone
    target_speed_mps: float = 5.0
    forward_distance_m: float = 20.0
    max_steps: int = 800

    def __post_init__(self) -> None:
        if self.target_speed_mps < 0:
            raise ValueError("target_speed_mps must be >= 0")
        if self.forward_distance_m <= 0:
            raise ValueError("forward_distance_m must be > 0")
        if self.max_steps <= 0:
            raise ValueError("max_steps must be > 0")


@dataclass(frozen=True, slots=True)
class ExpWorkflowResult:
    """Summary of one completed experiment workflow."""

    control_loop_result: LoopResult
    sampled_states: int
    traveled_distance_m: float
    entered_forbidden_zone: bool


@dataclass(slots=True)
class RunExpWorkflow:
    """Run forward-motion demo and evaluate forbidden-zone entry from motion log."""

    control_loop: RunControlLoop
    follow_vehicle_topdown: FollowVehicleProtocol

    def run(self, request: ExpWorkflowRequest) -> ExpWorkflowResult:
        target = TargetSpeedCommand(request.target_speed_mps)
        motion_log: list[VehicleState] = []
        start_xy: tuple[float, float] | None = None

        def _on_state(state: VehicleState) -> None:
            nonlocal start_xy
            motion_log.append(state)
            if start_xy is None:
                start_xy = (state.x, state.y)

        def _stop_before_apply(_step: int, state: VehicleState) -> bool:
            if start_xy is None:
                return False
            traveled = _distance_xy(start_xy[0], start_xy[1], state.x, state.y)
            return traveled >= request.forward_distance_m

        def _before_step(_step: int) -> None:
            if not self.follow_vehicle_topdown.follow_once():
                raise RuntimeError(
                    f"follow target actor not found: id={request.vehicle_id.value}"
                )

        control_loop_result = self.control_loop.run(
            vehicle_id=request.vehicle_id,
            target=target,
            max_steps=request.max_steps,
            before_step=_before_step,
            on_state=_on_state,
            stop_before_apply=_stop_before_apply,
        )
        if not motion_log:
            raise RuntimeError("no vehicle states were sampled during exp workflow")
        if start_xy is None:  # pragma: no cover - start_xy always set with non-empty log
            raise RuntimeError("internal error: missing start position")

        last_state = motion_log[-1]
        traveled_distance_m = _distance_xy(start_xy[0], start_xy[1], last_state.x, last_state.y)
        entered_forbidden_zone = has_entered_forbidden_zone(motion_log, request.forbidden_zone)
        return ExpWorkflowResult(
            control_loop_result=control_loop_result,
            sampled_states=len(motion_log),
            traveled_distance_m=traveled_distance_m,
            entered_forbidden_zone=entered_forbidden_zone,
        )


def _distance_xy(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)
