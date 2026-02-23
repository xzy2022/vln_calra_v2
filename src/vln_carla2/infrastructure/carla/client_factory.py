"""CARLA client/world initialization and sync settings management."""

from dataclasses import dataclass
from typing import Any

from vln_carla2.infrastructure.carla.types import require_carla


@dataclass(slots=True)
class CarlaRuntime:
    """Runtime handle used by the application layer."""

    client: Any
    world: Any
    original_settings: Any


def create_sync_runtime(
    host: str,
    port: int,
    timeout_seconds: float,
    map_name: str,
    fixed_delta_seconds: float,
) -> CarlaRuntime:
    """Connect to CARLA, load map if needed, and switch to sync mode."""
    carla = require_carla()

    client = carla.Client(host, port)
    client.set_timeout(timeout_seconds)
    world = client.get_world()

    current_map = world.get_map().name.split("/")[-1]
    if current_map != map_name:
        world = client.load_world(map_name)

    original_settings = world.get_settings()
    sync_settings = world.get_settings()
    sync_settings.synchronous_mode = True
    sync_settings.fixed_delta_seconds = fixed_delta_seconds
    world.apply_settings(sync_settings)
    world.tick()

    return CarlaRuntime(client=client, world=world, original_settings=original_settings)


def restore_world_settings(world: Any, original_settings: Any) -> None:
    """Restore world settings changed by create_sync_runtime."""
    world.apply_settings(original_settings)

