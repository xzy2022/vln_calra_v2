"""Scene-editor composition and runtime wiring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from vln_carla2.adapters.cli.keyboard_input_windows import SceneEditorKeyboardInputWindows
from vln_carla2.domain.model.scene_template import SceneObjectKind
from vln_carla2.domain.model.simple_command import ControlCommand
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.infrastructure.carla.actuator_raw import CarlaRawMotionActuator
from vln_carla2.infrastructure.carla.scene_object_spawner_adapter import (
    CarlaSceneObjectSpawnerAdapter,
)
from vln_carla2.infrastructure.carla.state_reader import CarlaVehicleStateReader
from vln_carla2.infrastructure.carla.vehicle_resolver_adapter import CarlaVehicleResolverAdapter
from vln_carla2.infrastructure.carla.vehicle_spawner_adapter import CarlaVehicleSpawnerAdapter
from vln_carla2.infrastructure.carla.world_adapter import CarlaWorldAdapter
from vln_carla2.infrastructure.filesystem.episode_spec_json_store import EpisodeSpecJsonStore
from vln_carla2.infrastructure.filesystem.exp_metrics_json_store import ExpMetricsJsonStore
from vln_carla2.infrastructure.filesystem.scene_template_json_store import SceneTemplateJsonStore
from vln_carla2.usecases.runtime.follow_vehicle_topdown import FollowVehicleTopDown
from vln_carla2.usecases.runtime.resolve_vehicle_ref import ResolveVehicleRef
from vln_carla2.usecases.runtime.spawn_vehicle import SpawnVehicle
from vln_carla2.usecases.scene.export_scene_template import ExportSceneTemplate
from vln_carla2.usecases.scene.import_scene_template import ImportSceneTemplate
from vln_carla2.usecases.scene.input_snapshot import EditorInputSnapshot
from vln_carla2.usecases.scene.models import EditorMode, EditorState
from vln_carla2.usecases.scene.record_spawned_scene_object import (
    RecordSpawnedSceneObject,
)
from vln_carla2.usecases.scene.run_scene_editor_loop import RunSceneEditorLoop
from vln_carla2.usecases.scene.spawn_vehicle_at_spectator_xy import (
    SpawnVehicleAtSpectatorXY,
)
from vln_carla2.usecases.runtime.move_spectator import MoveSpectator
from vln_carla2.usecases.shared.vehicle_ref import VehicleRefInput

from vln_carla2.infrastructure.carla.session_runtime import (
    CarlaSessionConfig,
    managed_carla_session,
)

_SCENE_TICK_LOG_FILENAME = "scene_tick_log.json"


@dataclass(slots=True)
class _SceneManualControl:
    control_target: VehicleRefInput
    resolver: ResolveVehicleRef
    motion_actuator: CarlaRawMotionActuator

    def apply(self, snapshot: EditorInputSnapshot) -> None:
        selected = self.resolver.run(self.control_target)
        if selected is None:
            raise RuntimeError(
                "manual control target not found: "
                f"{_format_vehicle_ref(self.control_target)}"
            )
        self.motion_actuator.apply(
            VehicleId(selected.actor_id),
            ControlCommand(
                throttle=snapshot.held_throttle,
                brake=snapshot.held_brake,
                steer=snapshot.held_steer,
            ),
        )


@dataclass(slots=True)
class _SceneTickLogger:
    map_name: str
    control_target: VehicleRefInput
    resolver: ResolveVehicleRef
    state_reader: CarlaVehicleStateReader
    world: Any
    tick_traces: list[dict[str, object]] = field(default_factory=list)

    def on_tick(self, *, frame: int) -> None:
        selected = self.resolver.run(self.control_target)
        if selected is None:
            return
        actor_id = int(selected.actor_id)
        actor = self.world.get_actor(actor_id)
        if actor is None:
            return
        try:
            state = self.state_reader.read(VehicleId(actor_id))
        except RuntimeError:
            return
        control = actor.get_control()
        self.tick_traces.append(
            {
                "frame": int(frame),
                "actor_id": actor_id,
                "x": state.x,
                "y": state.y,
                "z": state.z,
                "yaw_deg": state.yaw_deg,
                "vx": state.vx,
                "vy": state.vy,
                "vz": state.vz,
                "speed_mps": state.speed_mps,
                "throttle": float(getattr(control, "throttle", 0.0)),
                "brake": float(getattr(control, "brake", 0.0)),
                "steer": float(getattr(control, "steer", 0.0)),
            }
        )

    def save(self, path: str) -> str:
        payload = {
            "map_name": self.map_name,
            "control_target": {
                "scheme": self.control_target.scheme,
                "value": self.control_target.value,
            },
            "summary": {"ticks_recorded": len(self.tick_traces)},
            "tick_traces": list(self.tick_traces),
        }
        return ExpMetricsJsonStore().save(payload, path)


@dataclass(slots=True)
class SceneEditorContainer:
    """Built runtime dependencies for scene editor loop."""

    runtime: RunSceneEditorLoop
    import_scene_template: ImportSceneTemplate | None = None
    tick_logger: _SceneTickLogger | None = None


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
    export_episode_spec: bool = False
    episode_spec_export_dir: str | None = None
    manual_control_target: VehicleRefInput | None = None
    enable_tick_log: bool = False
    tick_log_path: str | None = None
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
        if self.episode_spec_export_dir is not None and not self.episode_spec_export_dir.strip():
            raise ValueError("episode_spec_export_dir must not be empty when set")
        if self.tick_log_path is not None and not self.tick_log_path.strip():
            raise ValueError("tick_log_path must not be empty when set")
        if self.enable_tick_log and self.manual_control_target is None:
            raise ValueError(
                "enable_tick_log requires manual_control_target "
                "(set --manual-control-target)."
            )


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
            export_episode_spec=settings.export_episode_spec,
            episode_spec_export_dir=settings.episode_spec_export_dir,
            manual_control_target=settings.manual_control_target,
            enable_tick_log=settings.enable_tick_log,
            start_in_follow_mode=settings.start_in_follow_mode,
            allow_mode_toggle=settings.allow_mode_toggle,
            allow_spawn_vehicle_hotkey=settings.allow_spawn_vehicle_hotkey,
        )
        if settings.scene_import_path is not None:
            if container.import_scene_template is None:
                raise RuntimeError("scene import is unavailable in current runtime.")
            spec_store = EpisodeSpecJsonStore()
            episode_spec = spec_store.load(settings.scene_import_path)
            scene_import_path = spec_store.resolve_scene_json_path(
                episode_spec=episode_spec,
                episode_spec_path=settings.scene_import_path,
            )
            imported_count = container.import_scene_template.run(scene_import_path)
            print(
                "[INFO] scene imported: "
                f"episode_spec={settings.scene_import_path} "
                f"scene={scene_import_path} "
                f"objects={imported_count}"
            )
        _bind_manual_follow_target_with_retry(
            world=session.world,
            runtime=container.runtime,
            follow_vehicle_id=settings.follow_vehicle_id,
            manual_control_target=settings.manual_control_target,
            synchronous_mode=settings.synchronous_mode,
        )
        try:
            return container.runtime.run(max_ticks=max_ticks)
        finally:
            if container.tick_logger is not None:
                output_path = settings.tick_log_path or str(_resolve_default_scene_tick_log_path())
                try:
                    saved_path = container.tick_logger.save(output_path)
                    print(f"[INFO] tick log saved path={saved_path}")
                except Exception as exc:
                    print(f"[WARN] failed to save tick log: {exc}")


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
    export_episode_spec: bool = False,
    episode_spec_export_dir: str | None = None,
    manual_control_target: VehicleRefInput | None = None,
    enable_tick_log: bool = False,
    start_in_follow_mode: bool = False,
    allow_mode_toggle: bool = True,
    allow_spawn_vehicle_hotkey: bool = True,
) -> SceneEditorContainer:
    """Compose scene-editor dependencies and produce runtime."""
    if enable_tick_log and manual_control_target is None:
        raise ValueError(
            "enable_tick_log requires manual_control_target (set --manual-control-target)."
        )

    keyboard_input = None
    move_spectator = None
    follow_vehicle_topdown = None
    spawn_vehicle_at_spectator_xy = None
    spawn_barrel_at_spectator_xy = None
    spawn_goal_at_spectator_xy = None
    export_scene = None
    import_scene_template = None
    manual_control = None
    tick_logger = None
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
            export_episode_spec=export_episode_spec,
            episode_spec_store=EpisodeSpecJsonStore(),
            episode_spec_export_dir=episode_spec_export_dir,
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
        spawn_goal_at_spectator_xy = SpawnVehicleAtSpectatorXY(
            spectator_camera=world_adapter,
            ground_z_resolver=world_adapter,
            spawn_vehicle=SpawnVehicle(spawner=CarlaVehicleSpawnerAdapter(world)),
            role_name="goal",
            object_kind=SceneObjectKind.GOAL_VEHICLE,
            recorder=scene_object_recorder,
        )
        if manual_control_target is not None:
            resolver = ResolveVehicleRef(resolver=CarlaVehicleResolverAdapter(world))
            manual_control = _SceneManualControl(
                control_target=manual_control_target,
                resolver=resolver,
                motion_actuator=CarlaRawMotionActuator(world),
            )
            if enable_tick_log:
                tick_logger = _SceneTickLogger(
                    map_name=map_name,
                    control_target=manual_control_target,
                    resolver=resolver,
                    state_reader=CarlaVehicleStateReader(world),
                    world=world,
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
        spawn_goal_at_spectator_xy=spawn_goal_at_spectator_xy,
        export_scene=export_scene,
        manual_control=manual_control,
        tick_observer=tick_logger,
    )
    return SceneEditorContainer(
        runtime=runtime,
        import_scene_template=import_scene_template,
        tick_logger=tick_logger,
    )


def _initialize_spectator_top_down(*, world_adapter: CarlaWorldAdapter, initial_z: float) -> None:
    transform = world_adapter.get_spectator_transform()
    transform.location.z = initial_z
    transform.rotation.pitch = -90.0
    transform.rotation.yaw = 0.0
    transform.rotation.roll = 0.0
    world_adapter.set_spectator_transform(transform)


def _bind_manual_follow_target_with_retry(
    *,
    world: Any,
    runtime: RunSceneEditorLoop,
    follow_vehicle_id: int | None,
    manual_control_target: VehicleRefInput | None,
    synchronous_mode: bool,
    max_attempts: int = 3,
) -> None:
    attempts = max(1, int(max_attempts))
    for idx in range(attempts):
        if _maybe_bind_manual_follow_target(
            world=world,
            runtime=runtime,
            follow_vehicle_id=follow_vehicle_id,
            manual_control_target=manual_control_target,
        ):
            return
        if idx >= attempts - 1:
            return
        _advance_world_one_tick(
            world=world,
            synchronous_mode=synchronous_mode,
        )


def _maybe_bind_manual_follow_target(
    *,
    world: Any,
    runtime: RunSceneEditorLoop,
    follow_vehicle_id: int | None,
    manual_control_target: VehicleRefInput | None,
) -> bool:
    if follow_vehicle_id is not None or manual_control_target is None:
        return False
    if not hasattr(world, "get_spectator"):
        return False

    try:
        selected = ResolveVehicleRef(
            resolver=CarlaVehicleResolverAdapter(world)
        ).run(manual_control_target)
    except Exception:
        return False

    if selected is None:
        return False

    actor_id = int(selected.actor_id)
    world_adapter = CarlaWorldAdapter(world)
    runtime.state.follow_vehicle_id = actor_id
    runtime.follow_vehicle_topdown = FollowVehicleTopDown(
        spectator_camera=world_adapter,
        vehicle_pose=world_adapter,
        vehicle_id=VehicleId(actor_id),
        z=runtime.state.follow_z,
    )
    runtime.state.mode = EditorMode.FOLLOW
    return True


def _advance_world_one_tick(*, world: Any, synchronous_mode: bool) -> None:
    try:
        if synchronous_mode:
            world.tick()
            return
        world.wait_for_tick()
    except Exception:
        return


def _resolve_default_scene_tick_log_path() -> Path:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("runs") / run_id / "scene" / _SCENE_TICK_LOG_FILENAME


def _format_vehicle_ref(ref: VehicleRefInput) -> str:
    if ref.scheme == "first":
        return "first"
    return f"{ref.scheme}:{ref.value}"

