"""Bootstrap for the slice-0 runnable control loop."""

from typing import Any

from vln_carla2.app.container import build_container
from vln_carla2.app.settings import Settings
from vln_carla2.domain.model.simple_command import TargetSpeedCommand
from vln_carla2.infrastructure.carla.client_factory import (
    CarlaRuntime,
    create_sync_runtime,
    restore_world_settings,
)
from vln_carla2.infrastructure.carla.spawner import spawn_vehicle
from vln_carla2.usecases.run_control_loop import LoopResult


def run(settings: Settings) -> LoopResult:
    """Create runtime, execute closed-loop control, and cleanup resources."""
    runtime: CarlaRuntime | None = None
    ego_vehicle: Any | None = None

    try:
        runtime = create_sync_runtime(
            host=settings.host,
            port=settings.port,
            timeout_seconds=settings.timeout_seconds,
            map_name=settings.map_name,
            fixed_delta_seconds=settings.fixed_delta_seconds,
        )
        ego_vehicle = spawn_vehicle(
            world=runtime.world,
            blueprint_filter=settings.vehicle_blueprint,
            spawn_x=settings.spawn.x,
            spawn_y=settings.spawn.y,
            spawn_z=settings.spawn.z,
            spawn_yaw=settings.spawn.yaw,
            role_name="ego",
        )

        container = build_container(runtime.world, ego_vehicle)
        target = TargetSpeedCommand(target_speed_mps=settings.target_speed_mps)
        return container.run_control_loop.run(
            vehicle_id=container.vehicle_id,
            target=target,
            max_steps=settings.steps,
        )
    finally:
        if ego_vehicle is not None:
            try:
                ego_vehicle.destroy()
            except Exception as exc:  # pragma: no cover - best effort cleanup
                print(f"[WARN] failed to destroy ego vehicle: {exc}")
        if runtime is not None:
            try:
                restore_world_settings(runtime.world, runtime.original_settings)
            except Exception as exc:  # pragma: no cover - best effort cleanup
                print(f"[WARN] failed to restore CARLA world settings: {exc}")

