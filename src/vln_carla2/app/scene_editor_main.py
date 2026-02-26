"""Composition root for stage-1 scene editor runtime."""

from __future__ import annotations

from dataclasses import dataclass

from vln_carla2.app.carla_session import CarlaSessionConfig, managed_carla_session
from vln_carla2.app.operator_container import build_operator_container
from vln_carla2.usecases.operator.run_operator_loop import RunOperatorLoop


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
    offscreen_mode: bool = False
    tick_sleep_seconds: float = 0.05
    follow_vehicle_id: int | None = None

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
        if self.follow_vehicle_id is not None and self.follow_vehicle_id <= 0:
            raise ValueError("follow_vehicle_id must be positive when set")


@dataclass(slots=True)
class RunSceneEditorLoop:
    """Stage-1 use case: run tick loop with spectator controls."""

    runtime: RunOperatorLoop

    def run(self, *, max_ticks: int | None = None) -> int:
        return self.runtime.run(max_ticks=max_ticks)


def run(settings: SceneEditorSettings, *, max_ticks: int | None = None) -> int:
    """Create CARLA runtime, start tick loop, and restore world settings on exit."""
    session_config = CarlaSessionConfig(
        host=settings.host,
        port=settings.port,
        timeout_seconds=settings.timeout_seconds,
        map_name=settings.map_name,
        synchronous_mode=settings.synchronous_mode,
        fixed_delta_seconds=settings.fixed_delta_seconds,
        no_rendering_mode=settings.no_rendering_mode,
    )

    with managed_carla_session(session_config) as session:
        container = build_operator_container(
            world=session.world,
            synchronous_mode=settings.synchronous_mode,
            sleep_seconds=settings.tick_sleep_seconds,
            follow_vehicle_id=settings.follow_vehicle_id,
        )
        usecase = RunSceneEditorLoop(runtime=container.runtime)
        return usecase.run(max_ticks=max_ticks)
