"""Shared CARLA session lifecycle for app composition roots."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from vln_carla2.infrastructure.carla.client_factory import restore_world_settings
from vln_carla2.infrastructure.carla.types import require_carla


@dataclass(slots=True)
class CarlaSessionConfig:
    """Configuration for one CARLA world session."""

    host: str
    port: int
    timeout_seconds: float
    map_name: str
    synchronous_mode: bool
    fixed_delta_seconds: float
    no_rendering_mode: bool = False
    offscreen_mode: bool = False


@dataclass(slots=True)
class CarlaSession:
    """Opened CARLA session with world and original settings handle."""

    client: Any
    world: Any
    original_settings: Any

    def restore(self) -> None:
        """Restore world settings captured when the session was opened."""
        restore_world_settings(self.world, self.original_settings)


def open_carla_session(config: CarlaSessionConfig) -> CarlaSession:
    """Connect, ensure map, apply runtime settings, and return session handle."""
    carla = require_carla()

    client = carla.Client(config.host, config.port)
    client.set_timeout(config.timeout_seconds)
    world = client.get_world()

    current_map = world.get_map().name.split("/")[-1]
    if current_map != config.map_name:
        world = client.load_world(config.map_name)

    original_settings = world.get_settings()
    runtime_settings = world.get_settings()
    runtime_settings.synchronous_mode = config.synchronous_mode
    runtime_settings.no_rendering_mode = config.no_rendering_mode
    runtime_settings.fixed_delta_seconds = (
        config.fixed_delta_seconds if config.synchronous_mode else None
    )
    world.apply_settings(runtime_settings)
    if config.synchronous_mode:
        world.tick()

    return CarlaSession(client=client, world=world, original_settings=original_settings)


@contextmanager
def managed_carla_session(config: CarlaSessionConfig) -> Iterator[CarlaSession]:
    """Context manager that always restores world settings on exit."""
    session = open_carla_session(config)
    try:
        yield session
    finally:
        session.restore()
