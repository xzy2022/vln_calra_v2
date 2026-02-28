"""App-layer gateway implementing CLI workflow outbound port."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from vln_carla2.app.wiring.exp import ExpRunSettings, run_exp_workflow
from vln_carla2.app.wiring.operator import (
    OperatorContainer,
    OperatorWorkflowSettings,
    build_operator_container,
    run_operator_workflow,
)
from vln_carla2.app.wiring.scene import SceneEditorSettings, run_scene_editor
from vln_carla2.infrastructure.carla.session_runtime import CarlaSessionConfig, managed_carla_session
from vln_carla2.usecases.cli.dto import (
    ExpRunRequest,
    ExpWorkflowExecution,
    OperatorRunRequest,
    OperatorWorkflowExecution,
    SceneRunRequest,
    SpawnVehicleRequest,
    SpectatorFollowRequest,
    VehicleListRequest,
    VehicleRefInput,
    VehicleSpawnRequest,
)
from vln_carla2.usecases.cli.ports.workflows import CliWorkflowPort
from vln_carla2.usecases.shared.vehicle_ref import VehicleRefInput as OperatorVehicleRefInput
from vln_carla2.usecases.runtime.ports.vehicle_dto import (
    SpawnVehicleRequest as OperatorSpawnVehicleRequest,
    VehicleDescriptor,
)

T = TypeVar("T")


@dataclass(slots=True)
class CliWorkflowGateway(CliWorkflowPort):
    """Workflow adapter backed by app.wiring composition modules."""

    def run_scene_workflow(self, request: SceneRunRequest) -> None:
        settings = SceneEditorSettings(
            host=request.host,
            port=request.port,
            timeout_seconds=request.timeout_seconds,
            map_name=request.map_name,
            synchronous_mode=request.mode == "sync",
            fixed_delta_seconds=request.fixed_delta_seconds,
            no_rendering_mode=request.no_rendering,
            offscreen_mode=request.offscreen,
            tick_sleep_seconds=request.tick_sleep_seconds,
            scene_import_path=request.scene_import,
            scene_export_path=request.scene_export_path,
            export_episode_spec=request.export_episode_spec,
            episode_spec_export_dir=os.getenv("EPISODE_SPEC_EXPORT_DIR"),
            follow_vehicle_id=None,
            start_in_follow_mode=False,
            allow_mode_toggle=True,
            allow_spawn_vehicle_hotkey=True,
        )
        run_scene_editor(settings)

    def run_operator_workflow(self, request: OperatorRunRequest) -> OperatorWorkflowExecution:
        settings = OperatorWorkflowSettings(
            host=request.host,
            port=request.port,
            timeout_seconds=request.timeout_seconds,
            map_name=request.map_name,
            synchronous_mode=request.mode == "sync",
            fixed_delta_seconds=request.fixed_delta_seconds,
            no_rendering_mode=request.no_rendering,
            offscreen_mode=request.offscreen,
            tick_sleep_seconds=request.tick_sleep_seconds,
            spectator_initial_z=request.z,
            vehicle_ref=_to_operator_vehicle_ref(request.follow),
            spawn_request=_to_operator_spawn_request(request.spawn_request),
            spawn_if_missing=request.spawn_if_missing,
            strategy=request.strategy,
            steps=request.steps,
            target_speed_mps=request.target_speed_mps,
            operator_warmup_ticks=request.operator_warmup_ticks,
        )
        result = run_operator_workflow(settings)
        return OperatorWorkflowExecution(
            strategy=result.strategy,
            vehicle_source=result.vehicle_source,
            actor_id=result.selected_vehicle.actor_id,
            operator_ticks=result.operator_ticks,
            control_steps=result.control_loop_result.executed_steps,
        )

    def run_exp_workflow(self, request: ExpRunRequest) -> ExpWorkflowExecution:
        settings = ExpRunSettings(
            episode_spec_path=request.episode_spec,
            host=request.host,
            port=request.port,
            timeout_seconds=request.timeout_seconds,
            synchronous_mode=request.mode == "sync",
            fixed_delta_seconds=request.fixed_delta_seconds,
            no_rendering_mode=request.no_rendering,
            offscreen_mode=request.offscreen,
            control_target=_to_operator_vehicle_ref(request.control_target),
            forward_distance_m=request.forward_distance_m,
            target_speed_mps=request.target_speed_mps,
            follow_z=20.0,
            max_steps=request.max_steps,
        )
        result = run_exp_workflow(settings)
        return ExpWorkflowExecution(
            control_target=VehicleRefInput(
                scheme=result.control_target.scheme,
                value=result.control_target.value,
            ),
            actor_id=result.selected_vehicle.actor_id,
            scene_map_name=result.scene_map_name,
            imported_objects=result.imported_objects,
            forward_distance_m=result.forward_distance_m,
            traveled_distance_m=result.exp_workflow_result.traveled_distance_m,
            entered_forbidden_zone=result.exp_workflow_result.entered_forbidden_zone,
            control_steps=result.exp_workflow_result.control_loop_result.executed_steps,
            start_transform=result.start_transform,
            goal_transform=result.goal_transform,
        )

    def list_vehicles(self, request: VehicleListRequest) -> list[VehicleDescriptor]:
        return self._with_operator_container(
            request,
            operation=lambda container, _world: container.list_vehicles.run(),
        )

    def spawn_vehicle(self, request: VehicleSpawnRequest) -> VehicleDescriptor:
        return self._with_operator_container(
            request,
            operation=lambda container, _world: container.spawn_vehicle.run(
                _to_operator_spawn_request(request.spawn_request)
            ),
        )

    def resolve_vehicle_ref(self, request: SpectatorFollowRequest) -> VehicleDescriptor | None:
        return self._with_operator_container(
            request,
            operation=lambda container, _world: container.resolve_vehicle_ref.run(
                _to_operator_vehicle_ref(request.follow)
            ),
            sleep_seconds=0.0,
        )

    def run_spectator_follow_workflow(
        self,
        request: SpectatorFollowRequest,
        *,
        follow_vehicle_id: int,
    ) -> None:
        session_config = self._build_session_config(
            host=request.host,
            port=request.port,
            timeout_seconds=request.timeout_seconds,
            map_name=request.map_name,
            mode=request.mode,
            fixed_delta_seconds=request.fixed_delta_seconds,
            no_rendering=request.no_rendering,
            offscreen=False,
        )
        settings = SceneEditorSettings(
            host=session_config.host,
            port=session_config.port,
            timeout_seconds=session_config.timeout_seconds,
            map_name=session_config.map_name,
            synchronous_mode=session_config.synchronous_mode,
            fixed_delta_seconds=session_config.fixed_delta_seconds,
            no_rendering_mode=session_config.no_rendering_mode,
            offscreen_mode=session_config.offscreen_mode,
            follow_vehicle_id=follow_vehicle_id,
            spectator_initial_z=request.z,
            start_in_follow_mode=True,
            allow_mode_toggle=False,
            allow_spawn_vehicle_hotkey=False,
        )
        run_scene_editor(settings)

    def format_vehicle_ref(self, ref: VehicleRefInput) -> str:
        if ref.scheme == "first":
            return "first"
        return f"{ref.scheme}:{ref.value}"

    def _with_operator_container(
        self,
        request: VehicleListRequest | VehicleSpawnRequest | SpectatorFollowRequest,
        *,
        operation: Callable[[OperatorContainer, Any], T],
        sleep_seconds: float = 0.0,
    ) -> T:
        session_config = self._build_session_config(
            host=request.host,
            port=request.port,
            timeout_seconds=request.timeout_seconds,
            map_name=request.map_name,
            mode=request.mode,
            fixed_delta_seconds=request.fixed_delta_seconds,
            no_rendering=request.no_rendering,
            offscreen=False,
        )
        with managed_carla_session(session_config) as session:
            container = build_operator_container(
                world=session.world,
                synchronous_mode=session_config.synchronous_mode,
                sleep_seconds=sleep_seconds,
            )
            return operation(container, session.world)

    def _build_session_config(
        self,
        *,
        host: str,
        port: int,
        timeout_seconds: float,
        map_name: str,
        mode: str,
        fixed_delta_seconds: float,
        no_rendering: bool,
        offscreen: bool,
    ) -> CarlaSessionConfig:
        return CarlaSessionConfig(
            host=host,
            port=port,
            timeout_seconds=timeout_seconds,
            map_name=map_name,
            synchronous_mode=mode == "sync",
            fixed_delta_seconds=fixed_delta_seconds,
            no_rendering_mode=no_rendering,
            offscreen_mode=offscreen,
        )


def _to_operator_vehicle_ref(ref: VehicleRefInput) -> OperatorVehicleRefInput:
    return OperatorVehicleRefInput(scheme=ref.scheme, value=ref.value)


def _to_operator_spawn_request(request: SpawnVehicleRequest) -> OperatorSpawnVehicleRequest:
    return OperatorSpawnVehicleRequest(
        blueprint_filter=request.blueprint_filter,
        spawn_x=request.spawn_x,
        spawn_y=request.spawn_y,
        spawn_z=request.spawn_z,
        spawn_yaw=request.spawn_yaw,
        role_name=request.role_name,
    )



