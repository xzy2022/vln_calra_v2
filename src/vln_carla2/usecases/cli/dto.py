"""DTOs for CLI orchestration use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from vln_carla2.domain.model.episode_spec import EpisodeTransform
from vln_carla2.usecases.shared.vehicle_dto import SpawnVehicleRequest
from vln_carla2.usecases.shared.vehicle_ref import VehicleRefInput

RuntimeMode = Literal["sync", "async"]
WorkflowStrategy = Literal["serial", "parallel"]
QualityLevel = Literal["Low", "Epic"]


@dataclass(frozen=True, slots=True)
class SceneRunRequest:
    host: str
    port: int
    timeout_seconds: float
    map_name: str
    mode: RuntimeMode
    fixed_delta_seconds: float
    no_rendering: bool
    tick_sleep_seconds: float
    offscreen: bool
    launch_carla: bool
    reuse_existing_carla: bool
    carla_exe: str | None
    carla_startup_timeout_seconds: float
    quality_level: QualityLevel
    with_sound: bool
    keep_carla_server: bool
    scene_import: str | None
    scene_export_path: str | None
    export_episode_spec: bool
    manual_control_target: VehicleRefInput | None
    enable_tick_log: bool
    tick_log_path: str | None


@dataclass(frozen=True, slots=True)
class OperatorRunRequest:
    host: str
    port: int
    timeout_seconds: float
    map_name: str
    mode: RuntimeMode
    fixed_delta_seconds: float
    no_rendering: bool
    tick_sleep_seconds: float
    offscreen: bool
    launch_carla: bool
    reuse_existing_carla: bool
    carla_exe: str | None
    carla_startup_timeout_seconds: float
    quality_level: QualityLevel
    with_sound: bool
    keep_carla_server: bool
    follow: VehicleRefInput
    z: float
    spawn_request: SpawnVehicleRequest
    spawn_if_missing: bool
    strategy: WorkflowStrategy
    steps: int
    target_speed_mps: float
    operator_warmup_ticks: int


@dataclass(frozen=True, slots=True)
class ExpRunRequest:
    host: str
    port: int
    timeout_seconds: float
    map_name: str
    mode: RuntimeMode
    fixed_delta_seconds: float
    no_rendering: bool
    tick_sleep_seconds: float
    offscreen: bool
    launch_carla: bool
    reuse_existing_carla: bool
    carla_exe: str | None
    carla_startup_timeout_seconds: float
    quality_level: QualityLevel
    with_sound: bool
    keep_carla_server: bool
    episode_spec: str
    control_target: VehicleRefInput
    forward_distance_m: float
    target_speed_mps: float
    max_steps: int


@dataclass(frozen=True, slots=True)
class TrackingRunRequest:
    host: str
    port: int
    timeout_seconds: float
    map_name: str
    mode: RuntimeMode
    fixed_delta_seconds: float
    no_rendering: bool
    tick_sleep_seconds: float
    offscreen: bool
    launch_carla: bool
    reuse_existing_carla: bool
    carla_exe: str | None
    carla_startup_timeout_seconds: float
    quality_level: QualityLevel
    with_sound: bool
    keep_carla_server: bool
    episode_spec: str
    control_target: VehicleRefInput
    target_speed_mps: float
    max_steps: int | None
    route_step_m: float
    route_max_points: int
    lookahead_base_m: float
    lookahead_speed_gain: float
    lookahead_min_m: float
    lookahead_max_m: float
    wheelbase_m: float
    max_steer_angle_deg: float
    pid_kp: float
    pid_ki: float
    pid_kd: float
    max_throttle: float
    max_brake: float
    goal_distance_tolerance_m: float
    goal_yaw_tolerance_deg: float
    slowdown_distance_m: float
    min_slow_speed_mps: float
    steer_rate_limit_per_step: float
    bind_spectator: bool = False
    spectator_z: float = 20.0
    enable_trajectory_log: bool = False
    trajectory_log_path: str | None = None
    target_tick_log_path: str | None = None


@dataclass(frozen=True, slots=True)
class VehicleListRequest:
    host: str
    port: int
    timeout_seconds: float
    map_name: str
    mode: RuntimeMode
    fixed_delta_seconds: float
    no_rendering: bool
    output_format: Literal["table", "json"]


@dataclass(frozen=True, slots=True)
class VehicleSpawnRequest:
    host: str
    port: int
    timeout_seconds: float
    map_name: str
    mode: RuntimeMode
    fixed_delta_seconds: float
    no_rendering: bool
    output_format: Literal["table", "json"]
    spawn_request: SpawnVehicleRequest


@dataclass(frozen=True, slots=True)
class SpectatorFollowRequest:
    host: str
    port: int
    timeout_seconds: float
    map_name: str
    mode: RuntimeMode
    fixed_delta_seconds: float
    no_rendering: bool
    follow: VehicleRefInput
    z: float


@dataclass(frozen=True, slots=True)
class LaunchCarlaServerRequest:
    executable_path: str
    rpc_port: int
    offscreen: bool
    no_rendering: bool
    no_sound: bool
    quality_level: QualityLevel


@dataclass(frozen=True, slots=True)
class RuntimeSessionRecord:
    host: str
    port: int
    offscreen_mode: bool


@dataclass(frozen=True, slots=True)
class LaunchReport:
    reused_existing_server: bool = False
    launched_server_pid: int | None = None


@dataclass(frozen=True, slots=True)
class OperatorWorkflowExecution:
    strategy: WorkflowStrategy
    vehicle_source: str
    actor_id: int
    operator_ticks: int
    control_steps: int


@dataclass(frozen=True, slots=True)
class ExpWorkflowExecution:
    control_target: VehicleRefInput
    actor_id: int
    scene_map_name: str
    imported_objects: int
    forward_distance_m: float
    traveled_distance_m: float
    entered_forbidden_zone: bool
    control_steps: int
    start_transform: EpisodeTransform | None = None
    goal_transform: EpisodeTransform | None = None
    metrics_path: str | None = None


@dataclass(frozen=True, slots=True)
class TrackingWorkflowExecution:
    control_target: VehicleRefInput
    actor_id: int
    scene_map_name: str
    imported_objects: int
    reached_goal: bool
    termination_reason: str
    executed_steps: int
    final_distance_to_goal_m: float
    final_yaw_error_deg: float
    route_points: int
    start_transform: EpisodeTransform | None = None
    goal_transform: EpisodeTransform | None = None
    metrics_path: str | None = None


@dataclass(frozen=True, slots=True)
class SceneRunResult:
    mode: RuntimeMode
    host: str
    port: int
    interrupted: bool = False
    launch_report: LaunchReport = field(default_factory=LaunchReport)
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OperatorRunResult:
    host: str
    port: int
    execution: OperatorWorkflowExecution | None = None
    interrupted: bool = False
    launch_report: LaunchReport = field(default_factory=LaunchReport)
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExpRunResult:
    host: str
    port: int
    execution: ExpWorkflowExecution | None = None
    interrupted: bool = False
    launch_report: LaunchReport = field(default_factory=LaunchReport)
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TrackingRunResult:
    host: str
    port: int
    execution: TrackingWorkflowExecution | None = None
    interrupted: bool = False
    launch_report: LaunchReport = field(default_factory=LaunchReport)
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SpectatorFollowResult:
    mode: RuntimeMode
    host: str
    port: int
    skipped_offscreen: bool = False
    interrupted: bool = False
