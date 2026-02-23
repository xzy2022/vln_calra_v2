"""Vehicle spawning for CARLA."""

from typing import Any

from vln_carla2.infrastructure.carla.types import require_carla


def spawn_vehicle(
    world: Any,
    blueprint_filter: str,
    spawn_x: float,
    spawn_y: float,
    spawn_z: float,
    spawn_yaw: float,
    role_name: str = "ego",
) -> Any:
    """Spawn one vehicle at a fixed transform."""
    carla = require_carla()

    blueprints = world.get_blueprint_library().filter(blueprint_filter)
    if not blueprints:
        raise RuntimeError(f"No blueprint matched filter: {blueprint_filter}")

    blueprint = blueprints[0]
    if blueprint.has_attribute("role_name"):
        blueprint.set_attribute("role_name", role_name)

    transform = carla.Transform(
        carla.Location(x=float(spawn_x), y=float(spawn_y), z=float(spawn_z)),
        carla.Rotation(pitch=0.0, yaw=float(spawn_yaw), roll=0.0),
    )
    vehicle = world.try_spawn_actor(blueprint, transform)
    if vehicle is None:
        raise RuntimeError(
            "Failed to spawn vehicle at fixed point "
            f"(x={spawn_x}, y={spawn_y}, z={spawn_z}, yaw={spawn_yaw})"
        )
    return vehicle

