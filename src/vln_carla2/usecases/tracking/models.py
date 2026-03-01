"""Models for the tracking use case."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoutePoint:
    """Primitive route point used by tracking loop."""

    x: float
    y: float
    yaw_deg: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", float(self.x))
        object.__setattr__(self, "y", float(self.y))
        object.__setattr__(self, "yaw_deg", float(self.yaw_deg))


@dataclass(frozen=True, slots=True)
class TrackingGoal:
    """Tracking goal pose in world coordinates."""

    x: float
    y: float
    yaw_deg: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", float(self.x))
        object.__setattr__(self, "y", float(self.y))
        object.__setattr__(self, "yaw_deg", float(self.yaw_deg))


@dataclass(frozen=True, slots=True)
class TrackingConfig:
    """Configuration for pure pursuit + longitudinal PID tracking."""

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
        if self.target_speed_mps < 0.0:
            raise ValueError("target_speed_mps must be >= 0")
        if self.max_steps <= 0:
            raise ValueError("max_steps must be > 0")
        if self.dt_seconds <= 0.0:
            raise ValueError("dt_seconds must be > 0")
        if self.route_step_m <= 0.0:
            raise ValueError("route_step_m must be > 0")
        if self.route_max_points <= 0:
            raise ValueError("route_max_points must be > 0")
        if self.lookahead_min_m <= 0.0:
            raise ValueError("lookahead_min_m must be > 0")
        if self.lookahead_max_m < self.lookahead_min_m:
            raise ValueError("lookahead_max_m must be >= lookahead_min_m")
        if self.lookahead_base_m < 0.0:
            raise ValueError("lookahead_base_m must be >= 0")
        if self.wheelbase_m <= 0.0:
            raise ValueError("wheelbase_m must be > 0")
        if self.max_steer_angle_deg <= 0.0:
            raise ValueError("max_steer_angle_deg must be > 0")
        if not 0.0 <= self.max_throttle <= 1.0:
            raise ValueError("max_throttle must be in [0, 1]")
        if not 0.0 <= self.max_brake <= 1.0:
            raise ValueError("max_brake must be in [0, 1]")
        if self.goal_distance_tolerance_m <= 0.0:
            raise ValueError("goal_distance_tolerance_m must be > 0")
        if not 0.0 <= self.goal_yaw_tolerance_deg <= 180.0:
            raise ValueError("goal_yaw_tolerance_deg must be in [0, 180]")
        if self.slowdown_distance_m <= 0.0:
            raise ValueError("slowdown_distance_m must be > 0")
        if not 0.0 <= self.min_slow_speed_mps <= self.target_speed_mps:
            raise ValueError("min_slow_speed_mps must be in [0, target_speed_mps]")
        if self.steer_rate_limit_per_step <= 0.0:
            raise ValueError("steer_rate_limit_per_step must be > 0")
        if self.no_progress_max_steps <= 0:
            raise ValueError("no_progress_max_steps must be > 0")
        if self.no_progress_min_improvement_m <= 0.0:
            raise ValueError("no_progress_min_improvement_m must be > 0")


@dataclass(frozen=True, slots=True)
class TrackingStepTrace:
    """One control-step trace used for trajectory evaluation."""

    step: int
    frame: int
    actual_x: float
    actual_y: float
    actual_yaw_deg: float
    actual_speed_mps: float
    target_x: float
    target_y: float
    target_yaw_deg: float
    distance_to_goal_m: float
    yaw_error_deg: float
    target_speed_mps: float
    lookahead_distance_m: float
    throttle: float
    brake: float
    steer: float

    def __post_init__(self) -> None:
        if self.step <= 0:
            raise ValueError("step must be > 0")
        object.__setattr__(self, "frame", int(self.frame))
        object.__setattr__(self, "actual_x", float(self.actual_x))
        object.__setattr__(self, "actual_y", float(self.actual_y))
        object.__setattr__(self, "actual_yaw_deg", float(self.actual_yaw_deg))
        object.__setattr__(self, "actual_speed_mps", float(self.actual_speed_mps))
        object.__setattr__(self, "target_x", float(self.target_x))
        object.__setattr__(self, "target_y", float(self.target_y))
        object.__setattr__(self, "target_yaw_deg", float(self.target_yaw_deg))
        object.__setattr__(self, "distance_to_goal_m", float(self.distance_to_goal_m))
        object.__setattr__(self, "yaw_error_deg", float(self.yaw_error_deg))
        object.__setattr__(self, "target_speed_mps", float(self.target_speed_mps))
        object.__setattr__(self, "lookahead_distance_m", float(self.lookahead_distance_m))
        object.__setattr__(self, "throttle", float(self.throttle))
        object.__setattr__(self, "brake", float(self.brake))
        object.__setattr__(self, "steer", float(self.steer))
