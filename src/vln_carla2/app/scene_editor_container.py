"""Dependency wiring for scene-editor runtime."""

from dataclasses import dataclass
from typing import Any

from vln_carla2.adapters.cli.keyboard_input_windows import SceneEditorKeyboardInputWindows
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.infrastructure.carla.world_adapter import CarlaWorldAdapter
from vln_carla2.usecases.operator.follow_vehicle_topdown import FollowVehicleTopDown
from vln_carla2.usecases.scene_editor.models import EditorMode, EditorState
from vln_carla2.usecases.scene_editor.run_scene_editor_loop import RunSceneEditorLoop
from vln_carla2.usecases.spectator.move_spectator import MoveSpectator


@dataclass(slots=True)
class SceneEditorContainer:
    """Built runtime dependencies for scene editor loop."""

    runtime: RunSceneEditorLoop


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
    start_in_follow_mode: bool = False,
    allow_mode_toggle: bool = True,
) -> SceneEditorContainer:
    """Compose scene-editor dependencies and produce runtime."""
    keyboard_input = None
    move_spectator = None
    follow_vehicle_topdown = None
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

    runtime = RunSceneEditorLoop(
        world=world,
        synchronous_mode=synchronous_mode,
        sleep_seconds=sleep_seconds,
        state=state,
        min_follow_z=spectator_min_z,
        max_follow_z=spectator_max_z,
        allow_mode_toggle=allow_mode_toggle,
        keyboard_input=keyboard_input,
        move_spectator=move_spectator,
        follow_vehicle_topdown=follow_vehicle_topdown,
    )
    return SceneEditorContainer(runtime=runtime)


def _initialize_spectator_top_down(*, world_adapter: CarlaWorldAdapter, initial_z: float) -> None:
    transform = world_adapter.get_spectator_transform()
    transform.location.z = initial_z
    transform.rotation.pitch = -90.0
    transform.rotation.yaw = 0.0
    transform.rotation.roll = 0.0
    world_adapter.set_spectator_transform(transform)

