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
