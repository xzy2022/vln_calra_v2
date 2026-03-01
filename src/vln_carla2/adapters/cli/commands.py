"""Normalized CLI command DTOs."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Literal

from .dto import SpawnVehicleRequest, VehicleRefInput
from .vehicle_ref_parser import parse_vehicle_ref

RuntimeMode = Literal["sync", "async"]
WorkflowStrategy = Literal["serial", "parallel"]

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 2000
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAP_NAME = "Town10HD_Opt"
DEFAULT_FIXED_DELTA_SECONDS = 0.05
DEFAULT_TICK_SLEEP_SECONDS = 0.05
DEFAULT_SPECTATOR_Z = 20.0
DEFAULT_BLUEPRINT_FILTER = "vehicle.tesla.model3"
DEFAULT_SPAWN_X = 0.038
DEFAULT_SPAWN_Y = 15.320
DEFAULT_SPAWN_Z = 0.15
DEFAULT_SPAWN_YAW = 180.0
DEFAULT_ROLE_NAME = "ego"


@dataclass(frozen=True, slots=True)
class SceneRunCommand:
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
    quality_level: Literal["Low", "Epic"]
    with_sound: bool
    keep_carla_server: bool
    scene_import: str | None
    scene_export_path: str | None
    export_episode_spec: bool


@dataclass(frozen=True, slots=True)
class OperatorRunCommand:
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
    quality_level: Literal["Low", "Epic"]
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
class ExpRunCommand:
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
    quality_level: Literal["Low", "Epic"]
    with_sound: bool
    keep_carla_server: bool
    episode_spec: str
    control_target: VehicleRefInput
    forward_distance_m: float
    target_speed_mps: float
    max_steps: int


@dataclass(frozen=True, slots=True)
class TrackingRunCommand:
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
    quality_level: Literal["Low", "Epic"]
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


@dataclass(frozen=True, slots=True)
class VehicleListCommand:
    host: str
    port: int
    timeout_seconds: float
    map_name: str
    mode: RuntimeMode
    fixed_delta_seconds: float
    no_rendering: bool
    output_format: Literal["table", "json"]


@dataclass(frozen=True, slots=True)
class VehicleSpawnCommand:
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
class SpectatorFollowCommand:
    host: str
    port: int
    timeout_seconds: float
    map_name: str
    mode: RuntimeMode
    fixed_delta_seconds: float
    no_rendering: bool
    follow: VehicleRefInput
    z: float


def to_scene_run_command(args: argparse.Namespace) -> SceneRunCommand:
    return SceneRunCommand(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout_seconds,
        map_name=args.map_name,
        mode=args.mode,
        fixed_delta_seconds=args.fixed_delta_seconds,
        no_rendering=args.no_rendering,
        tick_sleep_seconds=args.tick_sleep_seconds,
        offscreen=args.offscreen,
        launch_carla=args.launch_carla,
        reuse_existing_carla=args.reuse_existing_carla,
        carla_exe=args.carla_exe,
        carla_startup_timeout_seconds=args.carla_startup_timeout_seconds,
        quality_level=args.quality_level,
        with_sound=args.with_sound,
        keep_carla_server=args.keep_carla_server,
        scene_import=args.scene_import,
        scene_export_path=args.scene_export_path,
        export_episode_spec=args.export_episode_spec,
    )


def to_operator_run_command(args: argparse.Namespace) -> OperatorRunCommand:
    return OperatorRunCommand(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout_seconds,
        map_name=args.map_name,
        mode=args.mode,
        fixed_delta_seconds=args.fixed_delta_seconds,
        no_rendering=args.no_rendering,
        tick_sleep_seconds=args.tick_sleep_seconds,
        offscreen=args.offscreen,
        launch_carla=args.launch_carla,
        reuse_existing_carla=args.reuse_existing_carla,
        carla_exe=args.carla_exe,
        carla_startup_timeout_seconds=args.carla_startup_timeout_seconds,
        quality_level=args.quality_level,
        with_sound=args.with_sound,
        keep_carla_server=args.keep_carla_server,
        follow=parse_vehicle_ref(args.follow),
        z=args.z,
        spawn_request=_to_spawn_vehicle_request(args),
        spawn_if_missing=args.spawn_if_missing,
        strategy=args.strategy,
        steps=args.steps,
        target_speed_mps=args.target_speed_mps,
        operator_warmup_ticks=args.operator_warmup_ticks,
    )


def to_exp_run_command(args: argparse.Namespace) -> ExpRunCommand:
    return ExpRunCommand(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout_seconds,
        map_name=args.map_name,
        mode=args.mode,
        fixed_delta_seconds=args.fixed_delta_seconds,
        no_rendering=args.no_rendering,
        tick_sleep_seconds=args.tick_sleep_seconds,
        offscreen=args.offscreen,
        launch_carla=args.launch_carla,
        reuse_existing_carla=args.reuse_existing_carla,
        carla_exe=args.carla_exe,
        carla_startup_timeout_seconds=args.carla_startup_timeout_seconds,
        quality_level=args.quality_level,
        with_sound=args.with_sound,
        keep_carla_server=args.keep_carla_server,
        episode_spec=args.episode_spec,
        control_target=parse_vehicle_ref(args.control_target),
        forward_distance_m=args.forward_distance_m,
        target_speed_mps=args.target_speed_mps,
        max_steps=args.max_steps,
    )


def to_tracking_run_command(args: argparse.Namespace) -> TrackingRunCommand:
    return TrackingRunCommand(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout_seconds,
        map_name=args.map_name,
        mode=args.mode,
        fixed_delta_seconds=args.fixed_delta_seconds,
        no_rendering=args.no_rendering,
        tick_sleep_seconds=args.tick_sleep_seconds,
        offscreen=args.offscreen,
        launch_carla=args.launch_carla,
        reuse_existing_carla=args.reuse_existing_carla,
        carla_exe=args.carla_exe,
        carla_startup_timeout_seconds=args.carla_startup_timeout_seconds,
        quality_level=args.quality_level,
        with_sound=args.with_sound,
        keep_carla_server=args.keep_carla_server,
        episode_spec=args.episode_spec,
        control_target=parse_vehicle_ref(args.control_target),
        target_speed_mps=args.target_speed_mps,
        max_steps=args.max_steps,
        route_step_m=args.route_step_m,
        route_max_points=args.route_max_points,
        lookahead_base_m=args.lookahead_base_m,
        lookahead_speed_gain=args.lookahead_speed_gain,
        lookahead_min_m=args.lookahead_min_m,
        lookahead_max_m=args.lookahead_max_m,
        wheelbase_m=args.wheelbase_m,
        max_steer_angle_deg=args.max_steer_angle_deg,
        pid_kp=args.pid_kp,
        pid_ki=args.pid_ki,
        pid_kd=args.pid_kd,
        max_throttle=args.max_throttle,
        max_brake=args.max_brake,
        goal_distance_tolerance_m=args.goal_distance_tolerance_m,
        goal_yaw_tolerance_deg=args.goal_yaw_tolerance_deg,
        slowdown_distance_m=args.slowdown_distance_m,
        min_slow_speed_mps=args.min_slow_speed_mps,
        steer_rate_limit_per_step=args.steer_rate_limit_per_step,
        bind_spectator=args.bind_spectator,
        spectator_z=args.spectator_z,
        enable_trajectory_log=args.enable_trajectory_log,
        trajectory_log_path=args.trajectory_log_path,
    )


def to_vehicle_list_command(args: argparse.Namespace) -> VehicleListCommand:
    return VehicleListCommand(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout_seconds,
        map_name=args.map_name,
        mode=args.mode,
        fixed_delta_seconds=args.fixed_delta_seconds,
        no_rendering=args.no_rendering,
        output_format=args.format,
    )


def to_vehicle_spawn_command(args: argparse.Namespace) -> VehicleSpawnCommand:
    return VehicleSpawnCommand(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout_seconds,
        map_name=args.map_name,
        mode=args.mode,
        fixed_delta_seconds=args.fixed_delta_seconds,
        no_rendering=args.no_rendering,
        output_format=args.output,
        spawn_request=_to_spawn_vehicle_request(args),
    )


def to_spectator_follow_command(args: argparse.Namespace) -> SpectatorFollowCommand:
    return SpectatorFollowCommand(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout_seconds,
        map_name=args.map_name,
        mode=args.mode,
        fixed_delta_seconds=args.fixed_delta_seconds,
        no_rendering=args.no_rendering,
        follow=parse_vehicle_ref(args.follow),
        z=args.z,
    )


def _to_spawn_vehicle_request(args: argparse.Namespace) -> SpawnVehicleRequest:
    return SpawnVehicleRequest(
        blueprint_filter=args.blueprint_filter,
        spawn_x=args.spawn_x,
        spawn_y=args.spawn_y,
        spawn_z=args.spawn_z,
        spawn_yaw=args.spawn_yaw,
        role_name=args.role_name,
    )
