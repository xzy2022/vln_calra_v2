"""Composition root for stage-1 scene editor runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vln_carla2.adapters.cli.runtime import CliRuntime
from vln_carla2.infrastructure.carla.client_factory import restore_world_settings
from vln_carla2.infrastructure.carla.types import require_carla


@dataclass(slots=True)
class SceneEditorSettings:
    """Runtime configuration for free spectator movement baseline."""

    host: str = "127.0.0.1"
    port: int = 2000
    timeout_seconds: float = 10.0
    map_name: str = "Town10HD_Opt"
    synchronous_mode: bool = True
    fixed_delta_seconds: float = 0.05
    no_rendering_mode: bool = False
    tick_sleep_seconds: float = 0.05

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


@dataclass(slots=True)
class _RuntimeContext:
    client: Any
    world: Any
    original_settings: Any


@dataclass(slots=True)
class RunSceneEditorLoop:
    """Stage-1 use case: run tick loop with spectator controls."""

    runtime: CliRuntime

    def run(self, *, max_ticks: int | None = None) -> int:
        return self.runtime.run(max_ticks=max_ticks)


def run(settings: SceneEditorSettings, *, max_ticks: int | None = None) -> int:
    """Create CARLA runtime, start tick loop, and restore world settings on exit."""
    context = _create_runtime_context(settings)
    runtime = CliRuntime(
        world=context.world,
        synchronous_mode=settings.synchronous_mode,
        sleep_seconds=settings.tick_sleep_seconds,
    )
    usecase = RunSceneEditorLoop(runtime=runtime)

    try:
        return usecase.run(max_ticks=max_ticks)
    finally:
        restore_world_settings(context.world, context.original_settings)


def _create_runtime_context(settings: SceneEditorSettings) -> _RuntimeContext:
    carla = require_carla()

    client = carla.Client(settings.host, settings.port)
    client.set_timeout(settings.timeout_seconds)
    world = client.get_world()

    current_map = world.get_map().name.split("/")[-1]
    if current_map != settings.map_name:
        world = client.load_world(settings.map_name)

    original_settings = world.get_settings()
    runtime_settings = world.get_settings()
    runtime_settings.synchronous_mode = settings.synchronous_mode
    runtime_settings.no_rendering_mode = settings.no_rendering_mode
    runtime_settings.fixed_delta_seconds = (
        settings.fixed_delta_seconds if settings.synchronous_mode else None
    )
    world.apply_settings(runtime_settings)
    if settings.synchronous_mode:
        world.tick()

    return _RuntimeContext(
        client=client,
        world=world,
        original_settings=original_settings,
    )
