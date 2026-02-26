"""Composition root for scene editor runtime."""

from __future__ import annotations

from dataclasses import dataclass

from vln_carla2.app.carla_session import CarlaSessionConfig, managed_carla_session
from vln_carla2.app.scene_editor_container import build_scene_editor_container


@dataclass(slots=True)
class SceneEditorSettings:
    """Runtime configuration for scene editor behavior."""

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
    spectator_initial_z: float = 20.0
    spectator_min_z: float = -20.0
    spectator_max_z: float = 120.0
    keyboard_xy_step: float = 1.0
    keyboard_z_step: float = 1.0
    scene_import_path: str | None = None
    scene_export_path: str | None = None
    start_in_follow_mode: bool = False
    allow_mode_toggle: bool = True
    allow_spawn_vehicle_hotkey: bool = True

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
        if self.spectator_max_z < self.spectator_min_z:
            raise ValueError("spectator_max_z must be >= spectator_min_z")
        if self.keyboard_xy_step < 0:
            raise ValueError("keyboard_xy_step must be >= 0")
        if self.keyboard_z_step < 0:
            raise ValueError("keyboard_z_step must be >= 0")
        if self.scene_import_path is not None and not self.scene_import_path.strip():
            raise ValueError("scene_import_path must not be empty when set")
        if self.scene_export_path is not None and not self.scene_export_path.strip():
            raise ValueError("scene_export_path must not be empty when set")


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
        offscreen_mode=settings.offscreen_mode,
    )

    with managed_carla_session(session_config) as session:
        container = build_scene_editor_container(
            world=session.world,
            synchronous_mode=settings.synchronous_mode,
            sleep_seconds=settings.tick_sleep_seconds,
            follow_vehicle_id=settings.follow_vehicle_id,
            spectator_initial_z=settings.spectator_initial_z,
            spectator_min_z=settings.spectator_min_z,
            spectator_max_z=settings.spectator_max_z,
            keyboard_xy_step=settings.keyboard_xy_step,
            keyboard_z_step=settings.keyboard_z_step,
            map_name=settings.map_name,
            scene_export_path=settings.scene_export_path,
            start_in_follow_mode=settings.start_in_follow_mode,
            allow_mode_toggle=settings.allow_mode_toggle,
            allow_spawn_vehicle_hotkey=settings.allow_spawn_vehicle_hotkey,
        )
        if settings.scene_import_path is not None:
            if container.import_scene_template is None:
                raise RuntimeError("scene import is unavailable in current runtime.")
            imported_count = container.import_scene_template.run(settings.scene_import_path)
            print(
                "[INFO] scene imported: "
                f"path={settings.scene_import_path} objects={imported_count}"
            )
        return container.runtime.run(max_ticks=max_ticks)
