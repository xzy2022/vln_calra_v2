"""Mappings from adapter command DTOs to CLI use-case DTOs.

CLI 代码（commands）把参数解析成 ExpRunCommand / SceneRunCommand ...
mappers.py 把 *Command 转成 *Request（usecases.cli.dto 里的）
"""
from __future__ import annotations

from vln_carla2.adapters.cli.commands import (
    ExpRunCommand,
    OperatorRunCommand,
    SceneRunCommand,
    SpectatorFollowCommand,
    VehicleListCommand,
    VehicleSpawnCommand,
)
from vln_carla2.adapters.cli.dto import SpawnVehicleRequest as AdapterSpawnVehicleRequest
from vln_carla2.adapters.cli.dto import VehicleRefInput as AdapterVehicleRefInput
from vln_carla2.usecases.cli.dto import (
    ExpRunRequest,
    OperatorRunRequest,
    SceneRunRequest,
    SpawnVehicleRequest,
    SpectatorFollowRequest,
    VehicleListRequest,
    VehicleRefInput,
    VehicleSpawnRequest,
)


def to_scene_run_request(command: SceneRunCommand) -> SceneRunRequest:
    return SceneRunRequest(
        host=command.host,
        port=command.port,
        timeout_seconds=command.timeout_seconds,
        map_name=command.map_name,
        mode=command.mode,
        fixed_delta_seconds=command.fixed_delta_seconds,
        no_rendering=command.no_rendering,
        tick_sleep_seconds=command.tick_sleep_seconds,
        offscreen=command.offscreen,
        launch_carla=command.launch_carla,
        reuse_existing_carla=command.reuse_existing_carla,
        carla_exe=command.carla_exe,
        carla_startup_timeout_seconds=command.carla_startup_timeout_seconds,
        quality_level=command.quality_level,
        with_sound=command.with_sound,
        keep_carla_server=command.keep_carla_server,
        scene_import=command.scene_import,
        scene_export_path=command.scene_export_path,
        export_episode_spec=command.export_episode_spec,
    )


def to_operator_run_request(command: OperatorRunCommand) -> OperatorRunRequest:
    return OperatorRunRequest(
        host=command.host,
        port=command.port,
        timeout_seconds=command.timeout_seconds,
        map_name=command.map_name,
        mode=command.mode,
        fixed_delta_seconds=command.fixed_delta_seconds,
        no_rendering=command.no_rendering,
        tick_sleep_seconds=command.tick_sleep_seconds,
        offscreen=command.offscreen,
        launch_carla=command.launch_carla,
        reuse_existing_carla=command.reuse_existing_carla,
        carla_exe=command.carla_exe,
        carla_startup_timeout_seconds=command.carla_startup_timeout_seconds,
        quality_level=command.quality_level,
        with_sound=command.with_sound,
        keep_carla_server=command.keep_carla_server,
        follow=_to_vehicle_ref(command.follow),
        z=command.z,
        spawn_request=_to_spawn_request(command.spawn_request),
        spawn_if_missing=command.spawn_if_missing,
        strategy=command.strategy,
        steps=command.steps,
        target_speed_mps=command.target_speed_mps,
        operator_warmup_ticks=command.operator_warmup_ticks,
    )


def to_exp_run_request(command: ExpRunCommand) -> ExpRunRequest:
    return ExpRunRequest(
        host=command.host,
        port=command.port,
        timeout_seconds=command.timeout_seconds,
        map_name=command.map_name,
        mode=command.mode,
        fixed_delta_seconds=command.fixed_delta_seconds,
        no_rendering=command.no_rendering,
        tick_sleep_seconds=command.tick_sleep_seconds,
        offscreen=command.offscreen,
        launch_carla=command.launch_carla,
        reuse_existing_carla=command.reuse_existing_carla,
        carla_exe=command.carla_exe,
        carla_startup_timeout_seconds=command.carla_startup_timeout_seconds,
        quality_level=command.quality_level,
        with_sound=command.with_sound,
        keep_carla_server=command.keep_carla_server,
        episode_spec=command.episode_spec,
        control_target=_to_vehicle_ref(command.control_target),
        forward_distance_m=command.forward_distance_m,
        target_speed_mps=command.target_speed_mps,
        max_steps=command.max_steps,
    )


def to_vehicle_list_request(command: VehicleListCommand) -> VehicleListRequest:
    return VehicleListRequest(
        host=command.host,
        port=command.port,
        timeout_seconds=command.timeout_seconds,
        map_name=command.map_name,
        mode=command.mode,
        fixed_delta_seconds=command.fixed_delta_seconds,
        no_rendering=command.no_rendering,
        output_format=command.output_format,
    )


def to_vehicle_spawn_request(command: VehicleSpawnCommand) -> VehicleSpawnRequest:
    return VehicleSpawnRequest(
        host=command.host,
        port=command.port,
        timeout_seconds=command.timeout_seconds,
        map_name=command.map_name,
        mode=command.mode,
        fixed_delta_seconds=command.fixed_delta_seconds,
        no_rendering=command.no_rendering,
        output_format=command.output_format,
        spawn_request=_to_spawn_request(command.spawn_request),
    )


def to_spectator_follow_request(command: SpectatorFollowCommand) -> SpectatorFollowRequest:
    return SpectatorFollowRequest(
        host=command.host,
        port=command.port,
        timeout_seconds=command.timeout_seconds,
        map_name=command.map_name,
        mode=command.mode,
        fixed_delta_seconds=command.fixed_delta_seconds,
        no_rendering=command.no_rendering,
        follow=_to_vehicle_ref(command.follow),
        z=command.z,
    )


def _to_vehicle_ref(ref: AdapterVehicleRefInput) -> VehicleRefInput:
    return VehicleRefInput(scheme=ref.scheme, value=ref.value)


def _to_spawn_request(request: AdapterSpawnVehicleRequest) -> SpawnVehicleRequest:
    return SpawnVehicleRequest(
        blueprint_filter=request.blueprint_filter,
        spawn_x=request.spawn_x,
        spawn_y=request.spawn_y,
        spawn_z=request.spawn_z,
        spawn_yaw=request.spawn_yaw,
        role_name=request.role_name,
    )
