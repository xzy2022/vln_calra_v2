"""Operator runtime wiring and workflow composition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vln_carla2.adapters.cli.keyboard_input_windows import KeyboardInputWindows
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.usecases.control.run_control_loop import RunControlLoop
from vln_carla2.infrastructure.carla.vehicle_catalog_adapter import CarlaVehicleCatalogAdapter
from vln_carla2.infrastructure.carla.vehicle_resolver_adapter import CarlaVehicleResolverAdapter
from vln_carla2.infrastructure.carla.vehicle_spawner_adapter import CarlaVehicleSpawnerAdapter
from vln_carla2.infrastructure.carla.world_adapter import CarlaWorldAdapter
from vln_carla2.usecases.operator.follow_vehicle_topdown import FollowVehicleTopDown
from vln_carla2.usecases.operator.list_vehicles import ListVehicles
from vln_carla2.usecases.operator.models import VehicleRefInput
from vln_carla2.usecases.operator.resolve_vehicle_ref import ResolveVehicleRef
from vln_carla2.usecases.operator.run_operator_loop import RunOperatorLoop
from vln_carla2.usecases.operator.run_operator_workflow import (
    OperatorWorkflowRequest,
    OperatorWorkflowResult,
    OperatorWorkflowStrategy,
    RunOperatorWorkflow,
)
from vln_carla2.usecases.operator.spawn_vehicle import SpawnVehicle
from vln_carla2.usecases.operator.ports.vehicle_dto import SpawnVehicleRequest
from vln_carla2.usecases.spectator.move_spectator import MoveSpectator

from .control import build_control_container
from .session import CarlaSessionConfig, managed_carla_session


@dataclass(slots=True)
class OperatorContainer:
    """Built runtime dependencies for operator-facing loop."""

    runtime: RunOperatorLoop
    list_vehicles: ListVehicles
    spawn_vehicle: SpawnVehicle
    resolve_vehicle_ref: ResolveVehicleRef


def build_operator_container(
    *,
    world: Any,
    synchronous_mode: bool,
    sleep_seconds: float,
    follow_vehicle_id: int | None = None,
    spectator_initial_z: float = 20.0,
    spectator_min_z: float = -20.0,
    spectator_max_z: float = 120.0,
) -> OperatorContainer:
    """Compose operator loop dependencies and produce a runtime."""
    vehicle_catalog = CarlaVehicleCatalogAdapter(world)
    vehicle_spawner = CarlaVehicleSpawnerAdapter(world)
    vehicle_resolver = CarlaVehicleResolverAdapter(world)

    keyboard_input = None
    move_spectator = None
    follow_vehicle_topdown = None

    if hasattr(world, "get_spectator"):
        world_adapter = CarlaWorldAdapter(world)
        _initialize_spectator_top_down(
            world_adapter=world_adapter,
            initial_z=spectator_initial_z,
        )
        keyboard_input = KeyboardInputWindows()
        move_spectator = MoveSpectator(
            world=world_adapter,
            min_z=spectator_min_z,
            max_z=spectator_max_z,
        )
        if follow_vehicle_id is not None:
            follow_vehicle_topdown = FollowVehicleTopDown(
                spectator_camera=world_adapter,
                vehicle_pose=world_adapter,
                vehicle_id=VehicleId(follow_vehicle_id),
                z=spectator_initial_z,
            )

    runtime = RunOperatorLoop(
        world=world,
        synchronous_mode=synchronous_mode,
        sleep_seconds=sleep_seconds,
        keyboard_input=keyboard_input,
        move_spectator=move_spectator,
        follow_vehicle_topdown=follow_vehicle_topdown,
    )
    return OperatorContainer(
        runtime=runtime,
        list_vehicles=ListVehicles(catalog=vehicle_catalog),
        spawn_vehicle=SpawnVehicle(spawner=vehicle_spawner),
        resolve_vehicle_ref=ResolveVehicleRef(resolver=vehicle_resolver),
    )


def _default_vehicle_ref() -> VehicleRefInput:
    return VehicleRefInput(scheme="role", value="ego")


def _default_spawn_request() -> SpawnVehicleRequest:
    return SpawnVehicleRequest(
        blueprint_filter="vehicle.tesla.model3",
        spawn_x=0.038,
        spawn_y=15.320,
        spawn_z=0.15,
        spawn_yaw=180.0,
        role_name="ego",
    )


@dataclass(slots=True)
class OperatorWorkflowSettings:
    """Configuration for one operator workflow run."""

    host: str = "127.0.0.1"
    port: int = 2000
    timeout_seconds: float = 10.0
    map_name: str = "Town10HD_Opt"
    synchronous_mode: bool = True
    fixed_delta_seconds: float = 0.05
    no_rendering_mode: bool = False
    offscreen_mode: bool = False
    tick_sleep_seconds: float = 0.05
    spectator_initial_z: float = 20.0
    spectator_min_z: float = -20.0
    spectator_max_z: float = 120.0
    vehicle_ref: VehicleRefInput = field(default_factory=_default_vehicle_ref)
    spawn_request: SpawnVehicleRequest = field(default_factory=_default_spawn_request)
    spawn_if_missing: bool = True
    strategy: OperatorWorkflowStrategy = "parallel"
    steps: int = 80
    target_speed_mps: float = 5.0
    operator_warmup_ticks: int = 1

    def __post_init__(self) -> None:
        if self.port <= 0:
            raise ValueError("port must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.fixed_delta_seconds <= 0:
            raise ValueError("fixed_delta_seconds must be positive")
        if self.tick_sleep_seconds < 0:
            raise ValueError("tick_sleep_seconds must be >= 0")
        if not self.map_name:
            raise ValueError("map_name must not be empty")
        if self.strategy not in {"serial", "parallel"}:
            raise ValueError("strategy must be 'serial' or 'parallel'")
        if self.steps <= 0:
            raise ValueError("steps must be > 0")
        if self.target_speed_mps < 0:
            raise ValueError("target_speed_mps must be >= 0")
        if self.operator_warmup_ticks < 0:
            raise ValueError("operator_warmup_ticks must be >= 0")


def run_operator_workflow(settings: OperatorWorkflowSettings) -> OperatorWorkflowResult:
    """Run full operator workflow in one managed CARLA session."""
    session_config = CarlaSessionConfig(
        host=settings.host,
        port=settings.port,
        timeout_seconds=settings.timeout_seconds,
        map_name=settings.map_name,
        synchronous_mode=settings.synchronous_mode,
        fixed_delta_seconds=settings.fixed_delta_seconds,
        no_rendering_mode=settings.no_rendering_mode,
        offscreen_mode=settings.offscreen_mode,
    )

    with managed_carla_session(session_config) as session:
        base_container = build_operator_container(
            world=session.world,
            synchronous_mode=settings.synchronous_mode,
            sleep_seconds=settings.tick_sleep_seconds,
            follow_vehicle_id=None,
            spectator_initial_z=settings.spectator_initial_z,
            spectator_min_z=settings.spectator_min_z,
            spectator_max_z=settings.spectator_max_z,
        )

        def _make_operator_runtime(follow_vehicle_id: int):
            return build_operator_container(
                world=session.world,
                synchronous_mode=settings.synchronous_mode,
                sleep_seconds=settings.tick_sleep_seconds,
                follow_vehicle_id=follow_vehicle_id,
                spectator_initial_z=settings.spectator_initial_z,
                spectator_min_z=settings.spectator_min_z,
                spectator_max_z=settings.spectator_max_z,
            ).runtime

        def _make_control_loop(actor_id: int) -> RunControlLoop:
            return _build_control_loop_for_actor(session.world, actor_id)

        workflow = RunOperatorWorkflow(
            resolve_vehicle_ref=base_container.resolve_vehicle_ref,
            spawn_vehicle=base_container.spawn_vehicle,
            operator_runtime_factory=_make_operator_runtime,
            control_loop_factory=_make_control_loop,
        )
        request = OperatorWorkflowRequest(
            vehicle_ref=settings.vehicle_ref,
            spawn_request=settings.spawn_request,
            spawn_if_missing=settings.spawn_if_missing,
            strategy=settings.strategy,
            target_speed_mps=settings.target_speed_mps,
            steps=settings.steps,
            operator_warmup_ticks=settings.operator_warmup_ticks,
        )
        return workflow.run(request)


def _build_control_loop_for_actor(world: Any, actor_id: int) -> RunControlLoop:
    actor = world.get_actor(actor_id)
    if actor is None:
        raise RuntimeError(f"Vehicle actor not found for control loop: id={actor_id}")
    container = build_control_container(world, actor)
    return container.run_control_loop


def _initialize_spectator_top_down(*, world_adapter: CarlaWorldAdapter, initial_z: float) -> None:
    transform = world_adapter.get_spectator_transform()
    transform.location.z = initial_z
    transform.rotation.pitch = -90.0
    transform.rotation.yaw = 0.0
    transform.rotation.roll = 0.0
    world_adapter.set_spectator_transform(transform)

