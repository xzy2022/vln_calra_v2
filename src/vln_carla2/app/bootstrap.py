"""Bootstrap for the slice-0 runnable control loop."""

from typing import Any

from vln_carla2.app.carla_session import CarlaSessionConfig, managed_carla_session
from vln_carla2.app.control_container import build_control_container
from vln_carla2.app.settings import Settings
from vln_carla2.domain.model.simple_command import TargetSpeedCommand
from vln_carla2.infrastructure.carla.spawner import spawn_vehicle
from vln_carla2.usecases.control.run_control_loop import LoopResult


def run(settings: Settings) -> LoopResult:
    """Create runtime, execute closed-loop control, and cleanup resources."""
    ego_vehicle: Any | None = None
    session_config = CarlaSessionConfig(
        host=settings.host,
        port=settings.port,
        timeout_seconds=settings.timeout_seconds,
        map_name=settings.map_name,
        synchronous_mode=True,
        fixed_delta_seconds=settings.fixed_delta_seconds,
        no_rendering_mode=settings.no_rendering_mode,
        offscreen_mode=settings.offscreen_mode,
    )

    with managed_carla_session(session_config) as session:
        ego_vehicle = spawn_vehicle(
            world=session.world,
            blueprint_filter=settings.vehicle_blueprint,
            spawn_x=settings.spawn.x,
            spawn_y=settings.spawn.y,
            spawn_z=settings.spawn.z,
            spawn_yaw=settings.spawn.yaw,
            role_name="ego",
        )
        try:
            container = build_control_container(session.world, ego_vehicle)
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
