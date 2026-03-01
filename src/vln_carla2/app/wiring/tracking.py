"""Tracking workflow composition wiring."""

from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from vln_carla2.domain.model.episode_spec import EpisodeTransform
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.infrastructure.carla.actuator_raw import CarlaRawMotionActuator
from vln_carla2.infrastructure.carla.clock import CarlaClock
from vln_carla2.infrastructure.carla.scene_object_spawner_adapter import (
    CarlaSceneObjectSpawnerAdapter,
)
from vln_carla2.infrastructure.carla.session_runtime import (
    CarlaSessionConfig,
    managed_carla_session,
)
from vln_carla2.infrastructure.carla.state_reader import CarlaVehicleStateReader
from vln_carla2.infrastructure.carla.vehicle_catalog_adapter import CarlaVehicleCatalogAdapter
from vln_carla2.infrastructure.carla.vehicle_resolver_adapter import CarlaVehicleResolverAdapter
from vln_carla2.infrastructure.carla.waypoint_route_planner_adapter import (
    CarlaWaypointRoutePlannerAdapter,
)
from vln_carla2.infrastructure.carla.world_adapter import CarlaWorldAdapter
from vln_carla2.infrastructure.filesystem.episode_spec_json_store import EpisodeSpecJsonStore
from vln_carla2.infrastructure.filesystem.exp_metrics_json_store import ExpMetricsJsonStore
from vln_carla2.infrastructure.filesystem.scene_template_json_store import SceneTemplateJsonStore
from vln_carla2.usecases.runtime.follow_vehicle_topdown import FollowVehicleTopDown
from vln_carla2.usecases.runtime.ports.vehicle_dto import VehicleDescriptor
from vln_carla2.usecases.runtime.resolve_vehicle_ref import ResolveVehicleRef
from vln_carla2.usecases.scene.import_scene_template import ImportSceneTemplate
from vln_carla2.usecases.shared.vehicle_ref import VehicleRefInput
from vln_carla2.usecases.tracking.api import RunTrackingLoop, TrackingRequest, TrackingResult
from vln_carla2.usecases.tracking.models import TrackingStepTrace

from .control import StdoutLogger

_CONTROL_TARGET_RESOLVE_RETRIES = 8
_TRACKING_METRICS_FILENAME = "tracking_metrics.json"


def _default_control_target() -> VehicleRefInput:
    return VehicleRefInput(scheme="role", value="ego")


@dataclass(slots=True)
class _FollowBoundClock:
    """Clock wrapper that keeps spectator follow active every tick."""

    clock: Any
    follow_once: Callable[[], bool]
    logger: StdoutLogger
    vehicle_id: VehicleId

    def tick(self) -> int:
        frame = int(self.clock.tick())
        if not self.follow_once():
            self.logger.warn(
                "spectator follow target missing during tracking run: "
                f"actor_id={self.vehicle_id.value}"
            )
        return frame


@dataclass(slots=True)
class TrackingRunSettings:
    """Configuration for one tracking run."""

    episode_spec_path: str
    host: str = "127.0.0.1"
    port: int = 2000
    timeout_seconds: float = 10.0
    synchronous_mode: bool = True
    fixed_delta_seconds: float = 0.05
    no_rendering_mode: bool = False
    offscreen_mode: bool = False
    control_target: VehicleRefInput = field(default_factory=_default_control_target)
    target_speed_mps: float = 5.0
    max_steps: int | None = None
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
    bind_spectator: bool = False
    spectator_z: float = 20.0
    enable_trajectory_log: bool = False
    trajectory_log_path: str | None = None

    def __post_init__(self) -> None:
        if not self.episode_spec_path or not self.episode_spec_path.strip():
            raise ValueError("episode_spec_path must not be empty")
        if self.port <= 0:
            raise ValueError("port must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.fixed_delta_seconds <= 0:
            raise ValueError("fixed_delta_seconds must be positive")
        if self.target_speed_mps < 0:
            raise ValueError("target_speed_mps must be >= 0")
        if self.max_steps is not None and self.max_steps <= 0:
            raise ValueError("max_steps must be > 0 when provided")
        if self.spectator_z <= 0:
            raise ValueError("spectator_z must be > 0")
        if self.trajectory_log_path is not None and not self.trajectory_log_path.strip():
            raise ValueError("trajectory_log_path must not be empty when set")


@dataclass(frozen=True, slots=True)
class TrackingRunResult:
    """Summary of one completed tracking run."""

    episode_spec_path: str
    scene_json_path: str
    scene_map_name: str
    control_target: VehicleRefInput
    selected_vehicle: VehicleDescriptor
    imported_objects: int
    start_transform: EpisodeTransform
    goal_transform: EpisodeTransform
    tracking_result: TrackingResult
    metrics_path: str | None = None


def run_tracking_workflow(settings: TrackingRunSettings) -> TrackingRunResult:
    """Run tracking workflow in one managed CARLA session."""
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
        vehicle_id = VehicleId(selected_vehicle.actor_id)
        logger = StdoutLogger()
        world_adapter = CarlaWorldAdapter(session.world)
        clock: Any = CarlaClock(session.world)
        if settings.bind_spectator:
            follower = FollowVehicleTopDown(
                spectator_camera=world_adapter,
                vehicle_pose=world_adapter,
                vehicle_id=vehicle_id,
                z=settings.spectator_z,
            )
            if not follower.follow_once():
                raise RuntimeError(
                    "failed to bind spectator to tracking target: "
                    f"actor_id={vehicle_id.value}"
                )
            clock = _FollowBoundClock(
                clock=clock,
                follow_once=follower.follow_once,
                logger=logger,
                vehicle_id=vehicle_id,
            )

        tracking_loop = RunTrackingLoop(
            state_reader=CarlaVehicleStateReader(session.world),
            motion_actuator=CarlaRawMotionActuator(session.world),
            clock=clock,
            logger=logger,
            route_planner=CarlaWaypointRoutePlannerAdapter(session.world),
        )
        effective_max_steps = settings.max_steps or episode_spec.max_steps
        tracking_result = tracking_loop.run(
            TrackingRequest(
                vehicle_id=vehicle_id,
                goal_x=episode_spec.goal_transform.x,
                goal_y=episode_spec.goal_transform.y,
                goal_yaw_deg=episode_spec.goal_transform.yaw,
                target_speed_mps=settings.target_speed_mps,
                max_steps=effective_max_steps,
                dt_seconds=settings.fixed_delta_seconds,
                route_step_m=settings.route_step_m,
                route_max_points=settings.route_max_points,
                lookahead_base_m=settings.lookahead_base_m,
                lookahead_speed_gain=settings.lookahead_speed_gain,
                lookahead_min_m=settings.lookahead_min_m,
                lookahead_max_m=settings.lookahead_max_m,
                wheelbase_m=settings.wheelbase_m,
                max_steer_angle_deg=settings.max_steer_angle_deg,
                pid_kp=settings.pid_kp,
                pid_ki=settings.pid_ki,
                pid_kd=settings.pid_kd,
                max_throttle=settings.max_throttle,
                max_brake=settings.max_brake,
                goal_distance_tolerance_m=settings.goal_distance_tolerance_m,
                goal_yaw_tolerance_deg=settings.goal_yaw_tolerance_deg,
                slowdown_distance_m=settings.slowdown_distance_m,
                min_slow_speed_mps=settings.min_slow_speed_mps,
                steer_rate_limit_per_step=settings.steer_rate_limit_per_step,
                no_progress_max_steps=settings.no_progress_max_steps,
                no_progress_min_improvement_m=settings.no_progress_min_improvement_m,
            )
        )
        metrics_path: str | None = None
        if settings.enable_trajectory_log or settings.trajectory_log_path is not None:
            output_path = settings.trajectory_log_path or str(
                _resolve_default_tracking_metrics_path(
                    episode_spec_path=settings.episode_spec_path
                )
            )
            payload = _build_tracking_metrics_payload(
                episode_spec_path=settings.episode_spec_path,
                scene_map_name=scene_template.map_name,
                control_target=settings.control_target,
                actor_id=selected_vehicle.actor_id,
                start_transform=episode_spec.start_transform,
                goal_transform=episode_spec.goal_transform,
                tracking_result=tracking_result,
            )
            metrics_path = ExpMetricsJsonStore().save(payload, output_path)

    return TrackingRunResult(
        episode_spec_path=settings.episode_spec_path,
        scene_json_path=scene_json_path,
        scene_map_name=scene_template.map_name,
        control_target=settings.control_target,
        selected_vehicle=selected_vehicle,
        imported_objects=imported_objects,
        start_transform=episode_spec.start_transform,
        goal_transform=episode_spec.goal_transform,
        tracking_result=tracking_result,
        metrics_path=metrics_path,
    )


def _build_tracking_metrics_payload(
    *,
    episode_spec_path: str,
    scene_map_name: str,
    control_target: VehicleRefInput,
    actor_id: int,
    start_transform: EpisodeTransform,
    goal_transform: EpisodeTransform,
    tracking_result: TrackingResult,
) -> dict[str, object]:
    return {
        "episode_spec_path": episode_spec_path,
        "map_name": scene_map_name,
        "actor_id": actor_id,
        "control_target": {
            "scheme": control_target.scheme,
            "value": control_target.value,
        },
        "start_transform": _transform_to_payload(start_transform),
        "goal_transform": _transform_to_payload(goal_transform),
        "summary": {
            "reached_goal": tracking_result.reached_goal,
            "termination_reason": tracking_result.termination_reason,
            "executed_steps": tracking_result.executed_steps,
            "final_distance_to_goal_m": tracking_result.final_distance_to_goal_m,
            "final_yaw_error_deg": tracking_result.final_yaw_error_deg,
        },
        "target_trajectory": [
            {"x": point.x, "y": point.y, "yaw_deg": point.yaw_deg}
            for point in tracking_result.route_points
        ],
        "tick_traces": [
            _step_trace_to_payload(trace) for trace in tracking_result.step_traces
        ],
    }


def _transform_to_payload(transform: EpisodeTransform) -> dict[str, float]:
    return {
        "x": transform.x,
        "y": transform.y,
        "z": transform.z,
        "yaw": transform.yaw,
    }


def _step_trace_to_payload(trace: TrackingStepTrace) -> dict[str, float | int]:
    return {
        "step": trace.step,
        "frame": trace.frame,
        "actual_x": trace.actual_x,
        "actual_y": trace.actual_y,
        "actual_yaw_deg": trace.actual_yaw_deg,
        "actual_speed_mps": trace.actual_speed_mps,
        "target_x": trace.target_x,
        "target_y": trace.target_y,
        "target_yaw_deg": trace.target_yaw_deg,
        "distance_to_goal_m": trace.distance_to_goal_m,
        "yaw_error_deg": trace.yaw_error_deg,
        "target_speed_mps": trace.target_speed_mps,
        "lookahead_distance_m": trace.lookahead_distance_m,
        "throttle": trace.throttle,
        "brake": trace.brake,
        "steer": trace.steer,
    }


def _resolve_default_tracking_metrics_path(*, episode_spec_path: str) -> Path:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    episode_dir = _resolve_episode_dir_name(episode_spec_path=episode_spec_path)
    return Path("runs") / run_id / "results" / episode_dir / _TRACKING_METRICS_FILENAME


def _resolve_episode_dir_name(*, episode_spec_path: str) -> str:
    episode_spec = Path(episode_spec_path)
    parent_name = episode_spec.parent.name.strip()
    if parent_name:
        return parent_name
    if episode_spec.stem:
        return episode_spec.stem
    return "episode"


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
