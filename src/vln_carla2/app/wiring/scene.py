"""Scene-editor composition and runtime wiring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vln_carla2.adapters.cli.keyboard_input_windows import SceneEditorKeyboardInputWindows
from vln_carla2.domain.model.scene_template import SceneObjectKind
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.infrastructure.carla.scene_object_spawner_adapter import (
    CarlaSceneObjectSpawnerAdapter,
)
from vln_carla2.infrastructure.carla.vehicle_spawner_adapter import CarlaVehicleSpawnerAdapter
from vln_carla2.infrastructure.carla.world_adapter import CarlaWorldAdapter
from vln_carla2.infrastructure.filesystem.scene_template_json_store import SceneTemplateJsonStore
from vln_carla2.usecases.operator.follow_vehicle_topdown import FollowVehicleTopDown
from vln_carla2.usecases.operator.spawn_vehicle import SpawnVehicle
from vln_carla2.usecases.scene_editor.export_scene_template import ExportSceneTemplate
from vln_carla2.usecases.scene_editor.import_scene_template import ImportSceneTemplate
from vln_carla2.usecases.scene_editor.models import EditorMode, EditorState
from vln_carla2.usecases.scene_editor.record_spawned_scene_object import (
    RecordSpawnedSceneObject,
)
from vln_carla2.usecases.scene_editor.run_scene_editor_loop import RunSceneEditorLoop
from vln_carla2.usecases.scene_editor.spawn_vehicle_at_spectator_xy import (
    SpawnVehicleAtSpectatorXY,
)
from vln_carla2.usecases.spectator.move_spectator import MoveSpectator

from .session import CarlaSessionConfig, managed_carla_session


@dataclass(slots=True)
class SceneEditorContainer:
    """Built runtime dependencies for scene editor loop."""

    runtime: RunSceneEditorLoop
    import_scene_template: ImportSceneTemplate | None = None


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


def run_scene_editor(settings: SceneEditorSettings, *, max_ticks: int | None = None) -> int:
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


def build_scene_editor_container(
    *,
    world: Any,
    synchronous_mode: bool,
    sleep_seconds: float,
    follow_vehicle_id: int | None = None,
    spectator_initial_z: float = 20.0,
    spectator_min_z: float = -20.0,
    spectator_max_z: float = 120.0,
    keyboard_xy_step: float = 1.0,
    keyboard_z_step: float = 1.0,
    map_name: str,
    scene_export_path: str | None = None,
    start_in_follow_mode: bool = False,
    allow_mode_toggle: bool = True,
    allow_spawn_vehicle_hotkey: bool = True,
) -> SceneEditorContainer:
    """Compose scene-editor dependencies and produce runtime."""
    keyboard_input = None
    move_spectator = None
    follow_vehicle_topdown = None
    spawn_vehicle_at_spectator_xy = None
    spawn_barrel_at_spectator_xy = None
    export_scene = None
    import_scene_template = None
    state = EditorState(
        mode=EditorMode.FOLLOW if start_in_follow_mode else EditorMode.FREE,
        follow_vehicle_id=follow_vehicle_id,
        follow_z=spectator_initial_z,
    )

    if hasattr(world, "get_spectator"):
        world_adapter = CarlaWorldAdapter(world)
        _initialize_spectator_top_down(
            world_adapter=world_adapter,
            initial_z=spectator_initial_z,
        )
        keyboard_input = SceneEditorKeyboardInputWindows(
            xy_step=keyboard_xy_step,
            z_step=keyboard_z_step,
        )
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
        scene_object_recorder = RecordSpawnedSceneObject()
        scene_template_store = SceneTemplateJsonStore()
        import_scene_template = ImportSceneTemplate(
            store=scene_template_store,
            spawner=CarlaSceneObjectSpawnerAdapter(world),
            expected_map_name=map_name,
        )
        export_scene = ExportSceneTemplate(
            store=scene_template_store,
            recorder=scene_object_recorder,
            map_name=map_name,
            export_path=scene_export_path,
        )
        spawn_vehicle_at_spectator_xy = SpawnVehicleAtSpectatorXY(
            spectator_camera=world_adapter,
            ground_z_resolver=world_adapter,
            spawn_vehicle=SpawnVehicle(spawner=CarlaVehicleSpawnerAdapter(world)),
            object_kind=SceneObjectKind.VEHICLE,
            recorder=scene_object_recorder,
        )
        spawn_barrel_at_spectator_xy = SpawnVehicleAtSpectatorXY(
            spectator_camera=world_adapter,
            ground_z_resolver=world_adapter,
            spawn_vehicle=SpawnVehicle(spawner=CarlaVehicleSpawnerAdapter(world)),
            blueprint_filter="static.prop.barrel*",
            vehicle_z_offset=0.02,
            role_name="barrel",
            object_kind=SceneObjectKind.BARREL,
            recorder=scene_object_recorder,
        )

    runtime = RunSceneEditorLoop(
        world=world,
        synchronous_mode=synchronous_mode,
        sleep_seconds=sleep_seconds,
        state=state,
        min_follow_z=spectator_min_z,
        max_follow_z=spectator_max_z,
        allow_mode_toggle=allow_mode_toggle,
        allow_spawn_vehicle_hotkey=allow_spawn_vehicle_hotkey,
        keyboard_input=keyboard_input,
        move_spectator=move_spectator,
        follow_vehicle_topdown=follow_vehicle_topdown,
        spawn_vehicle_at_spectator_xy=spawn_vehicle_at_spectator_xy,
        spawn_barrel_at_spectator_xy=spawn_barrel_at_spectator_xy,
        export_scene=export_scene,
    )
    return SceneEditorContainer(
        runtime=runtime,
        import_scene_template=import_scene_template,
    )


def _initialize_spectator_top_down(*, world_adapter: CarlaWorldAdapter, initial_z: float) -> None:
    transform = world_adapter.get_spectator_transform()
    transform.location.z = initial_z
    transform.rotation.pitch = -90.0
    transform.rotation.yaw = 0.0
    transform.rotation.roll = 0.0
    world_adapter.set_spectator_transform(transform)

