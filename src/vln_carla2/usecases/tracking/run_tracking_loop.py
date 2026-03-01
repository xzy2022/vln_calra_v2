"""Use case for pure-pursuit + longitudinal PID route tracking."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from vln_carla2.domain.model.simple_command import ControlCommand
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.model.vehicle_state import VehicleState
from vln_carla2.domain.services.longitudinal_pid_controller import LongitudinalPidController
from vln_carla2.domain.services.pure_pursuit_controller import PurePursuitController
from vln_carla2.usecases.tracking.models import RoutePoint, TrackingConfig, TrackingGoal
from vln_carla2.usecases.tracking.ports.clock import Clock
from vln_carla2.usecases.tracking.ports.logger import Logger
from vln_carla2.usecases.tracking.ports.motion_actuator import MotionActuator
from vln_carla2.usecases.tracking.ports.route_planner import RoutePlannerPort
from vln_carla2.usecases.tracking.ports.vehicle_state_reader import VehicleStateReader

TerminationReason = Literal[
    "goal_reached",
    "max_steps",
    "route_failed",
    "actor_missing",
    "no_progress",
]


@dataclass(frozen=True, slots=True)
class TrackingRequest:
    """Input payload for one tracking run."""

    vehicle_id: VehicleId
    goal_x: float
    goal_y: float
    goal_yaw_deg: float
    target_speed_mps: float = 5.0
    max_steps: int = 500
    dt_seconds: float = 0.05
    route_step_m: float = 2.0
    route_max_points: int = 2000
    lookahead_base_m: float = 3.0
    lookahead_speed_gain: float = 0.35
    lookahead_min_m: float = 2.5
    lookahead_max_m: float = 12.0
    wheelbase_m: float = 2.85
    max_steer_angle_deg: float = 70.0
    pid_kp: float = 1.0
    pid_ki: float = 0.05
    pid_kd: float = 0.0
    max_throttle: float = 0.75
    max_brake: float = 0.30
    goal_distance_tolerance_m: float = 1.5
    goal_yaw_tolerance_deg: float = 15.0
    slowdown_distance_m: float = 12.0
    min_slow_speed_mps: float = 0.8
    steer_rate_limit_per_step: float = 0.10
    no_progress_max_steps: int = 40
    no_progress_min_improvement_m: float = 0.1

    def __post_init__(self) -> None:
        # Reuse TrackingConfig validation as the source of truth for config fields.
        TrackingConfig(
            target_speed_mps=self.target_speed_mps,
            max_steps=self.max_steps,
            dt_seconds=self.dt_seconds,
            route_step_m=self.route_step_m,
            route_max_points=self.route_max_points,
            lookahead_base_m=self.lookahead_base_m,
            lookahead_speed_gain=self.lookahead_speed_gain,
            lookahead_min_m=self.lookahead_min_m,
            lookahead_max_m=self.lookahead_max_m,
            wheelbase_m=self.wheelbase_m,
            max_steer_angle_deg=self.max_steer_angle_deg,
            pid_kp=self.pid_kp,
            pid_ki=self.pid_ki,
            pid_kd=self.pid_kd,
            max_throttle=self.max_throttle,
            max_brake=self.max_brake,
            goal_distance_tolerance_m=self.goal_distance_tolerance_m,
            goal_yaw_tolerance_deg=self.goal_yaw_tolerance_deg,
            slowdown_distance_m=self.slowdown_distance_m,
            min_slow_speed_mps=self.min_slow_speed_mps,
            steer_rate_limit_per_step=self.steer_rate_limit_per_step,
            no_progress_max_steps=self.no_progress_max_steps,
            no_progress_min_improvement_m=self.no_progress_min_improvement_m,
        )


@dataclass(frozen=True, slots=True)
class TrackingResult:
    """Summary of one finished tracking execution."""

    executed_steps: int
    last_frame: int
    reached_goal: bool
    termination_reason: TerminationReason
    final_distance_to_goal_m: float
    final_yaw_error_deg: float
    route_points: tuple[RoutePoint, ...]


@dataclass(slots=True)
class RunTrackingLoop:
    """Closed-loop tracking: read -> plan/select -> control -> apply -> tick."""

    state_reader: VehicleStateReader
    motion_actuator: MotionActuator
    clock: Clock
    logger: Logger
    route_planner: RoutePlannerPort

    def run(self, request: TrackingRequest) -> TrackingResult:
        goal = TrackingGoal(
            x=request.goal_x,
            y=request.goal_y,
            yaw_deg=request.goal_yaw_deg,
        )
        config = _to_tracking_config(request)

        try:
            initial_state = self.state_reader.read(request.vehicle_id)
        except RuntimeError as exc:
            if _is_actor_missing_error(exc):
                return _terminal_result(
                    executed_steps=0,
                    last_frame=-1,
                    reached_goal=False,
                    reason="actor_missing",
                    state=None,
                    goal=goal,
                    route_points=(),
                )
            raise

        try:
            raw_route_points = self.route_planner.plan_route(
                start_x=initial_state.x,
                start_y=initial_state.y,
                start_yaw_deg=initial_state.yaw_deg,
                goal=goal,
                route_step_m=config.route_step_m,
                route_max_points=config.route_max_points,
            )
        except Exception as exc:  # pragma: no cover - defensive for runtime adapter failures
            self.logger.error(f"route planner failed: {exc}")
            return _terminal_result(
                executed_steps=0,
                last_frame=initial_state.frame,
                reached_goal=False,
                reason="route_failed",
                state=initial_state,
                goal=goal,
                route_points=(),
            )

        route_points = tuple(
            RoutePoint(x=float(point.x), y=float(point.y), yaw_deg=float(point.yaw_deg))
            for point in raw_route_points
        )
        if not route_points:
            self.logger.error("route planner returned empty route")
            return _terminal_result(
                executed_steps=0,
                last_frame=initial_state.frame,
                reached_goal=False,
                reason="route_failed",
                state=initial_state,
                goal=goal,
                route_points=(),
            )

        longitudinal = LongitudinalPidController(
            kp=config.pid_kp,
            ki=config.pid_ki,
            kd=config.pid_kd,
        )
        lateral = PurePursuitController(
            wheelbase_m=config.wheelbase_m,
            max_steer_angle_deg=config.max_steer_angle_deg,
        )

        executed_steps = 0
        last_frame = initial_state.frame
        last_state = initial_state
        prev_steer = 0.0
        nearest_index = 0
        best_distance_to_goal = _distance_xy(
            x1=initial_state.x,
            y1=initial_state.y,
            x2=goal.x,
            y2=goal.y,
        )
        no_progress_steps = 0

        for step in range(1, config.max_steps + 1):
            try:
                state = self.state_reader.read(request.vehicle_id)
            except RuntimeError as exc:
                if _is_actor_missing_error(exc):
                    return _terminal_result(
                        executed_steps=executed_steps,
                        last_frame=last_frame,
                        reached_goal=False,
                        reason="actor_missing",
                        state=last_state,
                        goal=goal,
                        route_points=route_points,
                    )
                raise

            last_state = state
            distance_to_goal = _distance_xy(
                x1=state.x,
                y1=state.y,
                x2=goal.x,
                y2=goal.y,
            )
            yaw_error_deg = _absolute_yaw_error_deg(
                yaw_deg=state.yaw_deg,
                target_yaw_deg=goal.yaw_deg,
            )

            if (
                distance_to_goal <= config.goal_distance_tolerance_m
                and yaw_error_deg <= config.goal_yaw_tolerance_deg
            ):
                self.logger.info(
                    "step="
                    f"{step} goal_reached=true dist_goal_m={distance_to_goal:.3f} "
                    f"yaw_error_deg={yaw_error_deg:.3f}"
                )
                return _terminal_result(
                    executed_steps=executed_steps,
                    last_frame=last_frame,
                    reached_goal=True,
                    reason="goal_reached",
                    state=state,
                    goal=goal,
                    route_points=route_points,
                )

            if best_distance_to_goal - distance_to_goal >= config.no_progress_min_improvement_m:
                best_distance_to_goal = distance_to_goal
                no_progress_steps = 0
            else:
                no_progress_steps += 1
                if no_progress_steps >= config.no_progress_max_steps:
                    self.logger.warn(
                        "step="
                        f"{step} no_progress=true dist_goal_m={distance_to_goal:.3f} "
                        f"threshold_steps={config.no_progress_max_steps}"
                    )
                    return _terminal_result(
                        executed_steps=executed_steps,
                        last_frame=last_frame,
                        reached_goal=False,
                        reason="no_progress",
                        state=state,
                        goal=goal,
                        route_points=route_points,
                    )

            nearest_index = _nearest_route_index(
                route_points=route_points,
                x=state.x,
                y=state.y,
                start_index=max(0, nearest_index - 3),
            )
            lookahead_distance_m = _compute_lookahead_distance(
                speed_mps=state.speed_mps,
                config=config,
            )
            target_point = _select_lookahead_target(
                route_points=route_points,
                nearest_index=nearest_index,
                x=state.x,
                y=state.y,
                lookahead_distance_m=lookahead_distance_m,
            )

            raw_steer = lateral.compute_steer(
                ego_x=state.x,
                ego_y=state.y,
                ego_yaw_deg=state.yaw_deg,
                target_x=target_point.x,
                target_y=target_point.y,
                lookahead_distance_m=max(lookahead_distance_m, 1e-3),
            )
            steer = _rate_limit(
                value=raw_steer,
                prev_value=prev_steer,
                max_step_delta=config.steer_rate_limit_per_step,
            )
            prev_steer = steer

            target_speed_mps = _target_speed_with_slowdown(
                target_speed_mps=config.target_speed_mps,
                min_slow_speed_mps=config.min_slow_speed_mps,
                slowdown_distance_m=config.slowdown_distance_m,
                distance_to_goal_m=distance_to_goal,
            )
            acceleration_command = longitudinal.compute(
                speed_mps=state.speed_mps,
                target_speed_mps=target_speed_mps,
                dt=config.dt_seconds,
            )
            if acceleration_command >= 0.0:
                throttle = min(config.max_throttle, acceleration_command)
                brake = 0.0
            else:
                throttle = 0.0
                brake = min(config.max_brake, abs(acceleration_command))

            command = ControlCommand(
                throttle=throttle,
                brake=brake,
                steer=steer,
            )

            try:
                self.motion_actuator.apply(request.vehicle_id, command)
            except RuntimeError as exc:
                if _is_actor_missing_error(exc):
                    return _terminal_result(
                        executed_steps=executed_steps,
                        last_frame=last_frame,
                        reached_goal=False,
                        reason="actor_missing",
                        state=state,
                        goal=goal,
                        route_points=route_points,
                    )
                raise

            last_frame = self.clock.tick()
            executed_steps += 1

            self.logger.info(
                "step="
                f"{step} frame={last_frame} speed_mps={state.speed_mps:.3f} "
                f"target_speed_mps={target_speed_mps:.3f} dist_goal_m={distance_to_goal:.3f} "
                f"lookahead_m={lookahead_distance_m:.3f} steer={steer:.3f} "
                f"throttle={throttle:.3f} brake={brake:.3f}"
            )

        return _terminal_result(
            executed_steps=executed_steps,
            last_frame=last_frame,
            reached_goal=False,
            reason="max_steps",
            state=last_state,
            goal=goal,
            route_points=route_points,
        )


def _to_tracking_config(request: TrackingRequest) -> TrackingConfig:
    return TrackingConfig(
        target_speed_mps=request.target_speed_mps,
        max_steps=request.max_steps,
        dt_seconds=request.dt_seconds,
        route_step_m=request.route_step_m,
        route_max_points=request.route_max_points,
        lookahead_base_m=request.lookahead_base_m,
        lookahead_speed_gain=request.lookahead_speed_gain,
        lookahead_min_m=request.lookahead_min_m,
        lookahead_max_m=request.lookahead_max_m,
        wheelbase_m=request.wheelbase_m,
        max_steer_angle_deg=request.max_steer_angle_deg,
        pid_kp=request.pid_kp,
        pid_ki=request.pid_ki,
        pid_kd=request.pid_kd,
        max_throttle=request.max_throttle,
        max_brake=request.max_brake,
        goal_distance_tolerance_m=request.goal_distance_tolerance_m,
        goal_yaw_tolerance_deg=request.goal_yaw_tolerance_deg,
        slowdown_distance_m=request.slowdown_distance_m,
        min_slow_speed_mps=request.min_slow_speed_mps,
        steer_rate_limit_per_step=request.steer_rate_limit_per_step,
        no_progress_max_steps=request.no_progress_max_steps,
        no_progress_min_improvement_m=request.no_progress_min_improvement_m,
    )


def _terminal_result(
    *,
    executed_steps: int,
    last_frame: int,
    reached_goal: bool,
    reason: TerminationReason,
    state: VehicleState | None,
    goal: TrackingGoal,
    route_points: tuple[RoutePoint, ...],
) -> TrackingResult:
    if state is None:
        final_distance_to_goal = float("inf")
        final_yaw_error_deg = 180.0
    else:
        final_distance_to_goal = _distance_xy(
            x1=state.x,
            y1=state.y,
            x2=goal.x,
            y2=goal.y,
        )
        final_yaw_error_deg = _absolute_yaw_error_deg(
            yaw_deg=state.yaw_deg,
            target_yaw_deg=goal.yaw_deg,
        )

    return TrackingResult(
        executed_steps=executed_steps,
        last_frame=last_frame,
        reached_goal=reached_goal,
        termination_reason=reason,
        final_distance_to_goal_m=final_distance_to_goal,
        final_yaw_error_deg=final_yaw_error_deg,
        route_points=route_points,
    )


def _compute_lookahead_distance(*, speed_mps: float, config: TrackingConfig) -> float:
    value = config.lookahead_base_m + config.lookahead_speed_gain * speed_mps
    return _clamp(value, min_value=config.lookahead_min_m, max_value=config.lookahead_max_m)


def _target_speed_with_slowdown(
    *,
    target_speed_mps: float,
    min_slow_speed_mps: float,
    slowdown_distance_m: float,
    distance_to_goal_m: float,
) -> float:
    if distance_to_goal_m >= slowdown_distance_m:
        return target_speed_mps
    ratio = _clamp(distance_to_goal_m / slowdown_distance_m, min_value=0.0, max_value=1.0)
    return min_slow_speed_mps + ratio * (target_speed_mps - min_slow_speed_mps)


def _nearest_route_index(
    *,
    route_points: tuple[RoutePoint, ...],
    x: float,
    y: float,
    start_index: int,
) -> int:
    best_index = _clamp_int(start_index, min_value=0, max_value=len(route_points) - 1)
    best_distance = float("inf")
    for idx in range(best_index, len(route_points)):
        point = route_points[idx]
        distance = _distance_xy(x1=x, y1=y, x2=point.x, y2=point.y)
        if distance < best_distance:
            best_distance = distance
            best_index = idx
    return best_index


def _select_lookahead_target(
    *,
    route_points: tuple[RoutePoint, ...],
    nearest_index: int,
    x: float,
    y: float,
    lookahead_distance_m: float,
) -> RoutePoint:
    for idx in range(nearest_index, len(route_points)):
        point = route_points[idx]
        if _distance_xy(x1=x, y1=y, x2=point.x, y2=point.y) >= lookahead_distance_m:
            return point
    return route_points[-1]


def _distance_xy(*, x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def _absolute_yaw_error_deg(*, yaw_deg: float, target_yaw_deg: float) -> float:
    delta = _normalize_angle_deg(target_yaw_deg - yaw_deg)
    return abs(delta)


def _normalize_angle_deg(angle_deg: float) -> float:
    return (angle_deg + 180.0) % 360.0 - 180.0


def _rate_limit(*, value: float, prev_value: float, max_step_delta: float) -> float:
    lower = prev_value - max_step_delta
    upper = prev_value + max_step_delta
    return _clamp(value, min_value=lower, max_value=upper)


def _clamp(value: float, *, min_value: float, max_value: float) -> float:
    return min(max_value, max(min_value, value))


def _clamp_int(value: int, *, min_value: int, max_value: int) -> int:
    return min(max_value, max(min_value, value))


def _is_actor_missing_error(exc: RuntimeError) -> bool:
    return "Vehicle actor not found" in str(exc)
