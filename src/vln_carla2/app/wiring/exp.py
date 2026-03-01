"""Experiment workflow composition wiring."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Literal

from vln_carla2.domain.model.forbidden_zone import ForbiddenZone
from vln_carla2.domain.model.episode_spec import EpisodeTransform
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.model.vehicle_state import VehicleState
from vln_carla2.domain.services.forbidden_zone_rules import has_entered_forbidden_zone
from vln_carla2.infrastructure.carla.actuator_raw import CarlaRawMotionActuator
from vln_carla2.infrastructure.carla.clock import CarlaClock
from vln_carla2.infrastructure.carla.navigation_agents import (
    BehaviorProfile,
    CarlaBasicNavigationAgentAdapter,
    CarlaBehaviorNavigationAgentAdapter,
)
from vln_carla2.infrastructure.carla.state_reader import CarlaVehicleStateReader
from vln_carla2.infrastructure.carla.scene_object_spawner_adapter import (
    CarlaSceneObjectSpawnerAdapter,
)
from vln_carla2.infrastructure.carla.vehicle_catalog_adapter import CarlaVehicleCatalogAdapter
from vln_carla2.infrastructure.carla.vehicle_resolver_adapter import CarlaVehicleResolverAdapter
from vln_carla2.infrastructure.carla.world_adapter import CarlaWorldAdapter
from vln_carla2.infrastructure.filesystem.episode_spec_json_store import EpisodeSpecJsonStore
from vln_carla2.infrastructure.filesystem.exp_metrics_json_store import ExpMetricsJsonStore
from vln_carla2.infrastructure.filesystem.scene_template_json_store import SceneTemplateJsonStore
from vln_carla2.usecases.exp.generate_exp_metrics_artifact import (
    ExpMetricsRequest,
    GenerateExpMetricsArtifact,
)
from vln_carla2.usecases.exp.run_exp_workflow import (
    ExpWorkflowRequest,
    ExpWorkflowResult,
    RunExpWorkflow,
)
from vln_carla2.usecases.control.run_agent_control_loop import RunAgentControlLoop
from vln_carla2.usecases.runtime.follow_vehicle_topdown import FollowVehicleTopDown
from vln_carla2.usecases.shared.vehicle_ref import VehicleRefInput
from vln_carla2.usecases.runtime.ports.vehicle_dto import VehicleDescriptor
from vln_carla2.usecases.runtime.resolve_vehicle_ref import ResolveVehicleRef
from vln_carla2.usecases.scene.andrew_monotone_chain_forbidden_zone_builder import (
    AndrewMonotoneChainForbiddenZoneBuilder,
)
from vln_carla2.usecases.scene.build_forbidden_zone_from_scene import BuildForbiddenZoneFromScene
from vln_carla2.usecases.scene.import_scene_template import ImportSceneTemplate

from .control import StdoutLogger, build_control_container
from vln_carla2.infrastructure.carla.session_runtime import (
    CarlaSessionConfig,
    managed_carla_session,
)

_CONTROL_TARGET_RESOLVE_RETRIES = 8
ExpControlMode = Literal["speed", "basic_agent", "behavior_agent"]
_EXP_CONTROL_MODES: tuple[str, ...] = ("speed", "basic_agent", "behavior_agent")
_BEHAVIOR_PROFILES: tuple[str, ...] = ("cautious", "normal", "aggressive")


def _default_control_target() -> VehicleRefInput:
    return VehicleRefInput(scheme="role", value="ego")


@dataclass(slots=True)
class ExpRunSettings:
    """Configuration for one experiment run."""

    episode_spec_path: str
    host: str = "127.0.0.1"
    port: int = 2000
    timeout_seconds: float = 10.0
    synchronous_mode: bool = True
    fixed_delta_seconds: float = 0.05
    no_rendering_mode: bool = False
    offscreen_mode: bool = False
    control_target: VehicleRefInput = field(default_factory=_default_control_target)
    forward_distance_m: float = 20.0
    target_speed_mps: float = 5.0
    follow_z: float = 20.0
    max_steps: int = 800
    control_mode: ExpControlMode = "speed"
    behavior_profile: BehaviorProfile = "normal"

    def __post_init__(self) -> None:
        if not self.episode_spec_path or not self.episode_spec_path.strip():
            raise ValueError("episode_spec_path must not be empty")
        if self.port <= 0:
            raise ValueError("port must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.fixed_delta_seconds <= 0:
            raise ValueError("fixed_delta_seconds must be positive")
        if self.forward_distance_m <= 0:
            raise ValueError("forward_distance_m must be > 0")
        if self.target_speed_mps < 0:
            raise ValueError("target_speed_mps must be >= 0")
        if self.max_steps <= 0:
            raise ValueError("max_steps must be > 0")
        if self.control_mode not in _EXP_CONTROL_MODES:
            raise ValueError(
                "control_mode must be one of: " f"{','.join(_EXP_CONTROL_MODES)}"
            )
        if self.behavior_profile not in _BEHAVIOR_PROFILES:
            raise ValueError(
                "behavior_profile must be one of: "
                f"{','.join(_BEHAVIOR_PROFILES)}"
            )


@dataclass(frozen=True, slots=True)
class ExpRunResult:
    """Summary of one completed exp run."""

    episode_spec_path: str
    scene_json_path: str
    scene_map_name: str
    control_target: VehicleRefInput
    selected_vehicle: VehicleDescriptor
    imported_objects: int
    forward_distance_m: float
    start_transform: EpisodeTransform
    goal_transform: EpisodeTransform
    exp_workflow_result: ExpWorkflowResult
    metrics_path: str
    control_mode: ExpControlMode = "speed"
    behavior_profile: BehaviorProfile | None = None


def run_exp_workflow(settings: ExpRunSettings) -> ExpRunResult:
    """Run experiment workflow in one managed CARLA session."""
    episode_store = EpisodeSpecJsonStore()
    episode_spec = episode_store.load(settings.episode_spec_path)
    scene_json_path = episode_store.resolve_scene_json_path(
        episode_spec=episode_spec,
        episode_spec_path=settings.episode_spec_path,
    )
    scene_store = SceneTemplateJsonStore()
    scene_template = scene_store.load(scene_json_path)

    session_config = CarlaSessionConfig(
        host=settings.host,
        port=settings.port,
        timeout_seconds=settings.timeout_seconds,
        map_name=scene_template.map_name,
        synchronous_mode=settings.synchronous_mode,
        fixed_delta_seconds=settings.fixed_delta_seconds,
        no_rendering_mode=settings.no_rendering_mode,
        offscreen_mode=settings.offscreen_mode,
        force_reload_map=True,
    )
    with managed_carla_session(session_config) as session:
        imported_objects = ImportSceneTemplate(
            store=scene_store,
            spawner=CarlaSceneObjectSpawnerAdapter(session.world),
            expected_map_name=scene_template.map_name,
        ).run(scene_json_path)

        selected_vehicle = _resolve_control_target_with_retry(
            world=session.world,
            control_target=settings.control_target,
            synchronous_mode=settings.synchronous_mode,
            retries=_CONTROL_TARGET_RESOLVE_RETRIES,
        )

        forbidden_zone = BuildForbiddenZoneFromScene(
            scene_loader=scene_store,
            zone_builder=AndrewMonotoneChainForbiddenZoneBuilder(),
            expected_map_name=scene_template.map_name,
        ).run(scene_json_path)

        vehicle_id = VehicleId(selected_vehicle.actor_id)
        world_adapter = CarlaWorldAdapter(session.world)
        follow_vehicle_topdown = FollowVehicleTopDown(
            spectator_camera=world_adapter,
            vehicle_pose=world_adapter,
            vehicle_id=vehicle_id,
            z=settings.follow_z,
        )
        if settings.control_mode == "speed":
            exp_result = RunExpWorkflow(
                control_loop=_build_control_loop_for_actor(
                    session.world,
                    selected_vehicle.actor_id,
                ),
                follow_vehicle_topdown=follow_vehicle_topdown,
            ).run(
                ExpWorkflowRequest(
                    vehicle_id=vehicle_id,
                    forbidden_zone=forbidden_zone,
                    target_speed_mps=settings.target_speed_mps,
                    forward_distance_m=settings.forward_distance_m,
                    max_steps=settings.max_steps,
                )
            )
            behavior_profile = None
        else:
            exp_result = _run_agent_exp_workflow(
                world=session.world,
                actor_id=selected_vehicle.actor_id,
                vehicle_id=vehicle_id,
                goal_transform=episode_spec.goal_transform,
                forbidden_zone=forbidden_zone,
                target_speed_mps=settings.target_speed_mps,
                max_steps=settings.max_steps,
                control_mode=settings.control_mode,
                behavior_profile=settings.behavior_profile,
                follow_vehicle_topdown=follow_vehicle_topdown,
            )
            behavior_profile = (
                settings.behavior_profile
                if settings.control_mode == "behavior_agent"
                else None
            )
        final_state = CarlaVehicleStateReader(session.world).read(vehicle_id)
        metrics_result = GenerateExpMetricsArtifact(store=ExpMetricsJsonStore()).run(
            ExpMetricsRequest(
                episode_spec_path=settings.episode_spec_path,
                entered_forbidden_zone=exp_result.entered_forbidden_zone,
                final_x=final_state.x,
                final_y=final_state.y,
                goal_x=episode_spec.goal_transform.x,
                goal_y=episode_spec.goal_transform.y,
            )
        )

    return ExpRunResult(
        episode_spec_path=settings.episode_spec_path,
        scene_json_path=scene_json_path,
        scene_map_name=scene_template.map_name,
        control_target=settings.control_target,
        selected_vehicle=selected_vehicle,
        imported_objects=imported_objects,
        forward_distance_m=settings.forward_distance_m,
        start_transform=episode_spec.start_transform,
        goal_transform=episode_spec.goal_transform,
        exp_workflow_result=exp_result,
        metrics_path=metrics_result.metrics_path,
        control_mode=settings.control_mode,
        behavior_profile=behavior_profile,
    )


def _run_agent_exp_workflow(
    *,
    world: Any,
    actor_id: int,
    vehicle_id: VehicleId,
    goal_transform: EpisodeTransform,
    forbidden_zone: ForbiddenZone,
    target_speed_mps: float,
    max_steps: int,
    control_mode: ExpControlMode,
    behavior_profile: BehaviorProfile,
    follow_vehicle_topdown: FollowVehicleTopDown,
) -> ExpWorkflowResult:
    motion_log: list[VehicleState] = []
    start_xy: tuple[float, float] | None = None

    def _on_state(state: VehicleState) -> None:
        nonlocal start_xy
        motion_log.append(state)
        if start_xy is None:
            start_xy = (state.x, state.y)

    def _before_step(_step: int) -> None:
        if not follow_vehicle_topdown.follow_once():
            raise RuntimeError(f"follow target actor not found: id={vehicle_id.value}")

    navigation_agent = _build_navigation_agent_for_actor(
        world=world,
        actor_id=actor_id,
        control_mode=control_mode,
        behavior_profile=behavior_profile,
    )
    control_loop_result = RunAgentControlLoop(
        state_reader=CarlaVehicleStateReader(world),
        motion_actuator=CarlaRawMotionActuator(world),
        clock=CarlaClock(world),
        logger=StdoutLogger(),
        navigation_agent=navigation_agent,
    ).run(
        vehicle_id=vehicle_id,
        target_speed_mps=target_speed_mps,
        destination_x=goal_transform.x,
        destination_y=goal_transform.y,
        destination_z=goal_transform.z,
        max_steps=max_steps,
        before_step=_before_step,
        on_state=_on_state,
    )
    if not motion_log:
        raise RuntimeError("no vehicle states were sampled during exp workflow")
    if start_xy is None:  # pragma: no cover - start_xy always set with non-empty log
        raise RuntimeError("internal error: missing start position")

    last_state = motion_log[-1]
    traveled_distance_m = _distance_xy(start_xy[0], start_xy[1], last_state.x, last_state.y)
    entered_forbidden_zone = has_entered_forbidden_zone(motion_log, forbidden_zone)
    return ExpWorkflowResult(
        control_loop_result=control_loop_result,
        sampled_states=len(motion_log),
        traveled_distance_m=traveled_distance_m,
        entered_forbidden_zone=entered_forbidden_zone,
    )


def _build_navigation_agent_for_actor(
    *,
    world: Any,
    actor_id: int,
    control_mode: ExpControlMode,
    behavior_profile: BehaviorProfile,
):
    actor = _require_vehicle_actor(world, actor_id=actor_id)
    if control_mode == "basic_agent":
        return CarlaBasicNavigationAgentAdapter(actor)
    if control_mode == "behavior_agent":
        return CarlaBehaviorNavigationAgentAdapter(
            actor,
            behavior_profile=behavior_profile,
        )
    raise ValueError(f"unsupported control_mode for navigation agent: {control_mode}")


def _build_control_loop_for_actor(world: Any, actor_id: int):
    actor = _require_vehicle_actor(world, actor_id=actor_id)
    return build_control_container(world, actor).run_control_loop


def _require_vehicle_actor(world: Any, *, actor_id: int) -> Any:
    actor = world.get_actor(actor_id)
    if actor is None:
        raise RuntimeError(f"Vehicle actor not found for exp control loop: id={actor_id}")
    return actor


def _resolve_control_target_with_retry(
    *,
    world: Any,
    control_target: VehicleRefInput,
    synchronous_mode: bool,
    retries: int,
) -> VehicleDescriptor:
    if retries < 0:
        raise ValueError("retries must be >= 0")

    resolver = ResolveVehicleRef(resolver=CarlaVehicleResolverAdapter(world))

    # CARLA actor list may lag one frame after spawn/import; tick once first.
    _tick_once_for_resolution(world=world, synchronous_mode=synchronous_mode)
    selected = resolver.run(control_target)
    if selected is not None:
        return selected

    for _ in range(retries):
        _tick_once_for_resolution(world=world, synchronous_mode=synchronous_mode)
        selected = resolver.run(control_target)
        if selected is not None:
            return selected

    raise RuntimeError(
        "control target vehicle not found after resolve retries: "
        f"scheme={control_target.scheme} value={control_target.value} "
        f"vehicles={_describe_current_vehicles(world)}"
    )


def _tick_once_for_resolution(*, world: Any, synchronous_mode: bool) -> int:
    if synchronous_mode:
        return int(world.tick())

    snapshot = world.wait_for_tick()
    return int(snapshot.frame)


def _describe_current_vehicles(world: Any) -> str:
    vehicles = CarlaVehicleCatalogAdapter(world).list_vehicles()
    if not vehicles:
        return "(no vehicles)"
    return ",".join(
        f"(actor_id={vehicle.actor_id} type_id={vehicle.type_id} role_name={vehicle.role_name})"
        for vehicle in vehicles
    )


def _distance_xy(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


