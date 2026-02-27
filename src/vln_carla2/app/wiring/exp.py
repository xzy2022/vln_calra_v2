"""Experiment workflow composition wiring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.infrastructure.carla.scene_object_spawner_adapter import (
    CarlaSceneObjectSpawnerAdapter,
)
from vln_carla2.infrastructure.carla.vehicle_catalog_adapter import CarlaVehicleCatalogAdapter
from vln_carla2.infrastructure.carla.vehicle_resolver_adapter import CarlaVehicleResolverAdapter
from vln_carla2.infrastructure.carla.world_adapter import CarlaWorldAdapter
from vln_carla2.infrastructure.filesystem.scene_template_json_store import SceneTemplateJsonStore
from vln_carla2.usecases.exp.run_exp_workflow import (
    ExpWorkflowRequest,
    ExpWorkflowResult,
    RunExpWorkflow,
)
from vln_carla2.usecases.operator.follow_vehicle_topdown import FollowVehicleTopDown
from vln_carla2.usecases.operator.models import VehicleRefInput
from vln_carla2.usecases.operator.ports.vehicle_dto import VehicleDescriptor
from vln_carla2.usecases.operator.resolve_vehicle_ref import ResolveVehicleRef
from vln_carla2.usecases.safety.andrew_monotone_chain_forbidden_zone_builder import (
    AndrewMonotoneChainForbiddenZoneBuilder,
)
from vln_carla2.usecases.safety.build_forbidden_zone_from_scene import BuildForbiddenZoneFromScene
from vln_carla2.usecases.scene_editor.import_scene_template import ImportSceneTemplate

from .control import build_control_container
from .session import CarlaSessionConfig, managed_carla_session

_CONTROL_TARGET_RESOLVE_RETRIES = 8


def _default_control_target() -> VehicleRefInput:
    return VehicleRefInput(scheme="role", value="ego")


@dataclass(slots=True)
class ExpRunSettings:
    """Configuration for one experiment run."""

    scene_json_path: str
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

    def __post_init__(self) -> None:
        if not self.scene_json_path or not self.scene_json_path.strip():
            raise ValueError("scene_json_path must not be empty")
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


@dataclass(frozen=True, slots=True)
class ExpRunResult:
    """Summary of one completed exp run."""

    scene_json_path: str
    scene_map_name: str
    control_target: VehicleRefInput
    selected_vehicle: VehicleDescriptor
    imported_objects: int
    forward_distance_m: float
    exp_workflow_result: ExpWorkflowResult


def run_exp_workflow(settings: ExpRunSettings) -> ExpRunResult:
    """Run experiment workflow in one managed CARLA session."""
    scene_store = SceneTemplateJsonStore()
    scene_template = scene_store.load(settings.scene_json_path)

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
        ).run(settings.scene_json_path)

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
        ).run(settings.scene_json_path)

        vehicle_id = VehicleId(selected_vehicle.actor_id)
        world_adapter = CarlaWorldAdapter(session.world)
        exp_result = RunExpWorkflow(
            control_loop=_build_control_loop_for_actor(session.world, selected_vehicle.actor_id),
            follow_vehicle_topdown=FollowVehicleTopDown(
                spectator_camera=world_adapter,
                vehicle_pose=world_adapter,
                vehicle_id=vehicle_id,
                z=settings.follow_z,
            ),
        ).run(
            ExpWorkflowRequest(
                vehicle_id=vehicle_id,
                forbidden_zone=forbidden_zone,
                target_speed_mps=settings.target_speed_mps,
                forward_distance_m=settings.forward_distance_m,
                max_steps=settings.max_steps,
            )
        )

    return ExpRunResult(
        scene_json_path=settings.scene_json_path,
        scene_map_name=scene_template.map_name,
        control_target=settings.control_target,
        selected_vehicle=selected_vehicle,
        imported_objects=imported_objects,
        forward_distance_m=settings.forward_distance_m,
        exp_workflow_result=exp_result,
    )


def _build_control_loop_for_actor(world: Any, actor_id: int):
    actor = world.get_actor(actor_id)
    if actor is None:
        raise RuntimeError(f"Vehicle actor not found for exp control loop: id={actor_id}")
    return build_control_container(world, actor).run_control_loop


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

