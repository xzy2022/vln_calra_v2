from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from vln_carla2.app.wiring import scene


@dataclass
class _FakeRuntime:
    result: int
    max_ticks_calls: list[int | None]

    def run(self, *, max_ticks: int | None = None) -> int:
        self.max_ticks_calls.append(max_ticks)
        return self.result


def test_run_passes_sync_settings_to_session_and_container(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    fake_world = object()
    runtime = _FakeRuntime(result=11, max_ticks_calls=[])

    @contextmanager
    def fake_managed_session(config: scene.CarlaSessionConfig):
        captured["session_config"] = config
        yield SimpleNamespace(world=fake_world)

    def fake_build_scene_editor_container(**kwargs: Any):
        captured["container_kwargs"] = kwargs
        return SimpleNamespace(runtime=runtime, tick_logger=None)

    monkeypatch.setattr(scene, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(
        scene,
        "build_scene_editor_container",
        fake_build_scene_editor_container,
    )

    result = scene.run_scene_editor(
        scene.SceneEditorSettings(
            synchronous_mode=True,
            fixed_delta_seconds=0.05,
            no_rendering_mode=True,
            offscreen_mode=True,
            tick_sleep_seconds=0.02,
        ),
        max_ticks=3,
    )

    session_config = captured["session_config"]
    container_kwargs = captured["container_kwargs"]

    assert result == 11
    assert session_config.synchronous_mode is True
    assert session_config.fixed_delta_seconds == 0.05
    assert session_config.no_rendering_mode is True
    assert session_config.offscreen_mode is True
    assert container_kwargs["world"] is fake_world
    assert container_kwargs["synchronous_mode"] is True
    assert container_kwargs["sleep_seconds"] == 0.02
    assert container_kwargs["follow_vehicle_id"] is None
    assert container_kwargs["spectator_initial_z"] == 20.0
    assert container_kwargs["spectator_min_z"] == -20.0
    assert container_kwargs["spectator_max_z"] == 120.0
    assert container_kwargs["keyboard_xy_step"] == 1.0
    assert container_kwargs["keyboard_z_step"] == 1.0
    assert container_kwargs["map_name"] == "Town10HD_Opt"
    assert container_kwargs["scene_export_path"] is None
    assert container_kwargs["export_episode_spec"] is False
    assert container_kwargs["episode_spec_export_dir"] is None
    assert container_kwargs["manual_control_target"] is None
    assert container_kwargs["enable_tick_log"] is False
    assert container_kwargs["start_in_follow_mode"] is False
    assert container_kwargs["allow_mode_toggle"] is True
    assert container_kwargs["allow_spawn_vehicle_hotkey"] is True
    assert runtime.max_ticks_calls == [3]


def test_run_passes_async_settings_to_session_and_container(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    runtime = _FakeRuntime(result=5, max_ticks_calls=[])

    @contextmanager
    def fake_managed_session(config: scene.CarlaSessionConfig):
        captured["session_config"] = config
        yield SimpleNamespace(world=object())

    def fake_build_scene_editor_container(**kwargs: Any):
        captured["container_kwargs"] = kwargs
        return SimpleNamespace(runtime=runtime, tick_logger=None)

    monkeypatch.setattr(scene, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(
        scene,
        "build_scene_editor_container",
        fake_build_scene_editor_container,
    )

    result = scene.run_scene_editor(
        scene.SceneEditorSettings(
            map_name="Town10HD_Opt",
            synchronous_mode=False,
            fixed_delta_seconds=0.05,
            tick_sleep_seconds=0.01,
        ),
        max_ticks=2,
    )

    session_config = captured["session_config"]
    container_kwargs = captured["container_kwargs"]

    assert result == 5
    assert session_config.map_name == "Town10HD_Opt"
    assert session_config.synchronous_mode is False
    assert session_config.fixed_delta_seconds == 0.05
    assert session_config.offscreen_mode is False
    assert container_kwargs["synchronous_mode"] is False
    assert container_kwargs["sleep_seconds"] == 0.01
    assert container_kwargs["map_name"] == "Town10HD_Opt"
    assert container_kwargs["scene_export_path"] is None
    assert container_kwargs["export_episode_spec"] is False
    assert container_kwargs["episode_spec_export_dir"] is None
    assert container_kwargs["manual_control_target"] is None
    assert container_kwargs["enable_tick_log"] is False
    assert container_kwargs["spectator_initial_z"] == 20.0
    assert container_kwargs["start_in_follow_mode"] is False
    assert container_kwargs["allow_mode_toggle"] is True
    assert container_kwargs["allow_spawn_vehicle_hotkey"] is True
    assert runtime.max_ticks_calls == [2]


def test_run_passes_follow_vehicle_id_to_container(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    runtime = _FakeRuntime(result=1, max_ticks_calls=[])

    @contextmanager
    def fake_managed_session(_config: scene.CarlaSessionConfig):
        yield SimpleNamespace(world=object())

    def fake_build_scene_editor_container(**kwargs: Any):
        captured["container_kwargs"] = kwargs
        return SimpleNamespace(runtime=runtime, tick_logger=None)

    monkeypatch.setattr(scene, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(
        scene,
        "build_scene_editor_container",
        fake_build_scene_editor_container,
    )

    result = scene.run_scene_editor(
        scene.SceneEditorSettings(
            synchronous_mode=True,
            tick_sleep_seconds=0.01,
            follow_vehicle_id=123,
            spectator_initial_z=33.0,
            start_in_follow_mode=True,
            allow_mode_toggle=False,
            allow_spawn_vehicle_hotkey=False,
        ),
        max_ticks=1,
    )

    assert result == 1
    assert captured["container_kwargs"]["follow_vehicle_id"] == 123
    assert captured["container_kwargs"]["spectator_initial_z"] == 33.0
    assert captured["container_kwargs"]["map_name"] == "Town10HD_Opt"
    assert captured["container_kwargs"]["scene_export_path"] is None
    assert captured["container_kwargs"]["export_episode_spec"] is False
    assert captured["container_kwargs"]["episode_spec_export_dir"] is None
    assert captured["container_kwargs"]["manual_control_target"] is None
    assert captured["container_kwargs"]["enable_tick_log"] is False
    assert captured["container_kwargs"]["start_in_follow_mode"] is True
    assert captured["container_kwargs"]["allow_mode_toggle"] is False
    assert captured["container_kwargs"]["allow_spawn_vehicle_hotkey"] is False
    assert runtime.max_ticks_calls == [1]


def test_run_imports_scene_before_loop_when_scene_import_path_is_set(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    runtime = _FakeRuntime(result=2, max_ticks_calls=[])

    @contextmanager
    def fake_managed_session(_config: scene.CarlaSessionConfig):
        yield SimpleNamespace(world=object())

    class _FakeImporter:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def run(self, path: str) -> int:
            self.calls.append(path)
            return 5

    importer = _FakeImporter()

    class _FakeEpisodeSpecStore:
        def __init__(self) -> None:
            self.load_calls: list[str] = []
            self.resolve_calls: list[tuple[str, str]] = []

        def load(self, path: str):
            self.load_calls.append(path)
            return object()

        def resolve_scene_json_path(self, *, episode_spec, episode_spec_path: str) -> str:
            del episode_spec
            self.resolve_calls.append((episode_spec_path, "scene"))
            return "fixtures/scene.json"

    episode_store = _FakeEpisodeSpecStore()

    def fake_build_scene_editor_container(**kwargs: Any):
        captured["container_kwargs"] = kwargs
        return SimpleNamespace(
            runtime=runtime,
            import_scene_template=importer,
            tick_logger=None,
        )

    monkeypatch.setattr(scene, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(
        scene,
        "build_scene_editor_container",
        fake_build_scene_editor_container,
    )
    monkeypatch.setattr(scene, "EpisodeSpecJsonStore", lambda: episode_store)

    result = scene.run_scene_editor(
        scene.SceneEditorSettings(
            scene_import_path="datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
            scene_export_path="exports/out.json",
            export_episode_spec=True,
            episode_spec_export_dir="datasets/town10hd_val_v1/episodes/ep_000001",
        ),
        max_ticks=4,
    )

    assert result == 2
    assert importer.calls == ["fixtures/scene.json"]
    assert episode_store.load_calls == [
        "datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json"
    ]
    assert captured["container_kwargs"]["scene_export_path"] == "exports/out.json"
    assert captured["container_kwargs"]["export_episode_spec"] is True
    assert (
        captured["container_kwargs"]["episode_spec_export_dir"]
        == "datasets/town10hd_val_v1/episodes/ep_000001"
    )
    assert captured["container_kwargs"]["manual_control_target"] is None
    assert captured["container_kwargs"]["enable_tick_log"] is False
    assert runtime.max_ticks_calls == [4]


def test_run_saves_tick_log_in_finally_when_runtime_is_interrupted(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    @contextmanager
    def fake_managed_session(_config: scene.CarlaSessionConfig):
        yield SimpleNamespace(world=object())

    class _InterruptedRuntime:
        def run(self, *, max_ticks: int | None = None) -> int:
            del max_ticks
            raise KeyboardInterrupt

    class _FakeTickLogger:
        def save(self, path: str) -> str:
            captured["save_path"] = path
            return "/abs/runs/custom/scene_tick_log.json"

    def fake_build_scene_editor_container(**kwargs: Any):
        captured["container_kwargs"] = kwargs
        return SimpleNamespace(
            runtime=_InterruptedRuntime(),
            import_scene_template=None,
            tick_logger=_FakeTickLogger(),
        )

    monkeypatch.setattr(scene, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(scene, "build_scene_editor_container", fake_build_scene_editor_container)

    with pytest.raises(KeyboardInterrupt):
        scene.run_scene_editor(
            scene.SceneEditorSettings(
                manual_control_target=scene.VehicleRefInput(scheme="role", value="ego"),
                enable_tick_log=True,
                tick_log_path="runs/custom/scene_tick_log.json",
            )
        )

    assert captured["container_kwargs"]["manual_control_target"] == scene.VehicleRefInput(
        scheme="role",
        value="ego",
    )
    assert captured["container_kwargs"]["enable_tick_log"] is True
    assert captured["save_path"] == "runs/custom/scene_tick_log.json"


def test_bind_manual_follow_target_sets_default_follow_when_target_exists(
    monkeypatch,
) -> None:
    class _FakeWorld:
        def get_spectator(self) -> object:
            return object()

    runtime = SimpleNamespace(
        state=scene.EditorState(
            mode=scene.EditorMode.FREE,
            follow_vehicle_id=None,
            follow_z=28.0,
        ),
        follow_vehicle_topdown=None,
    )

    class _FakeResolveVehicleRef:
        def __init__(self, *, resolver: Any) -> None:
            del resolver

        def run(self, ref: scene.VehicleRefInput):
            del ref
            return SimpleNamespace(actor_id=42)

    class _FakeFollowVehicleTopDown:
        def __init__(
            self,
            *,
            spectator_camera: Any,
            vehicle_pose: Any,
            vehicle_id: scene.VehicleId,
            z: float,
        ) -> None:
            self.spectator_camera = spectator_camera
            self.vehicle_pose = vehicle_pose
            self.vehicle_id = vehicle_id
            self.z = z

        def follow_once(self) -> bool:
            return True

    monkeypatch.setattr(scene, "ResolveVehicleRef", _FakeResolveVehicleRef)
    monkeypatch.setattr(scene, "CarlaVehicleResolverAdapter", lambda _world: object())
    monkeypatch.setattr(scene, "CarlaWorldAdapter", lambda _world: "world-adapter")
    monkeypatch.setattr(scene, "FollowVehicleTopDown", _FakeFollowVehicleTopDown)

    bound = scene._maybe_bind_manual_follow_target(
        world=_FakeWorld(),
        runtime=runtime,
        follow_vehicle_id=None,
        manual_control_target=scene.VehicleRefInput(scheme="role", value="ego"),
    )

    assert bound is True
    assert runtime.state.mode is scene.EditorMode.FOLLOW
    assert runtime.state.follow_vehicle_id == 42
    assert runtime.follow_vehicle_topdown is not None
    assert runtime.follow_vehicle_topdown.z == 28.0


def test_bind_manual_follow_target_keeps_free_mode_when_target_missing(monkeypatch) -> None:
    class _FakeWorld:
        def get_spectator(self) -> object:
            return object()

    runtime = SimpleNamespace(
        state=scene.EditorState(
            mode=scene.EditorMode.FREE,
            follow_vehicle_id=None,
            follow_z=20.0,
        ),
        follow_vehicle_topdown=None,
    )

    class _FakeResolveVehicleRef:
        def __init__(self, *, resolver: Any) -> None:
            del resolver

        def run(self, ref: scene.VehicleRefInput):
            del ref
            return None

    monkeypatch.setattr(scene, "ResolveVehicleRef", _FakeResolveVehicleRef)
    monkeypatch.setattr(scene, "CarlaVehicleResolverAdapter", lambda _world: object())

    bound = scene._maybe_bind_manual_follow_target(
        world=_FakeWorld(),
        runtime=runtime,
        follow_vehicle_id=None,
        manual_control_target=scene.VehicleRefInput(scheme="role", value="ego"),
    )

    assert bound is False
    assert runtime.state.mode is scene.EditorMode.FREE
    assert runtime.state.follow_vehicle_id is None
    assert runtime.follow_vehicle_topdown is None


def test_bind_manual_follow_target_with_retry_advances_tick_until_resolved(
    monkeypatch,
) -> None:
    class _FakeWorld:
        def __init__(self) -> None:
            self.tick_calls = 0

        def get_spectator(self) -> object:
            return object()

        def tick(self) -> int:
            self.tick_calls += 1
            return self.tick_calls

    world = _FakeWorld()
    runtime = SimpleNamespace(
        state=scene.EditorState(
            mode=scene.EditorMode.FREE,
            follow_vehicle_id=None,
            follow_z=20.0,
        ),
        follow_vehicle_topdown=None,
    )

    class _FakeResolveVehicleRef:
        def __init__(self, *, resolver: Any) -> None:
            del resolver

        def run(self, ref: scene.VehicleRefInput):
            del ref
            if world.tick_calls == 0:
                return None
            return SimpleNamespace(actor_id=7)

    class _FakeFollowVehicleTopDown:
        def __init__(
            self,
            *,
            spectator_camera: Any,
            vehicle_pose: Any,
            vehicle_id: scene.VehicleId,
            z: float,
        ) -> None:
            self.spectator_camera = spectator_camera
            self.vehicle_pose = vehicle_pose
            self.vehicle_id = vehicle_id
            self.z = z

        def follow_once(self) -> bool:
            return True

    monkeypatch.setattr(scene, "ResolveVehicleRef", _FakeResolveVehicleRef)
    monkeypatch.setattr(scene, "CarlaVehicleResolverAdapter", lambda _world: object())
    monkeypatch.setattr(scene, "CarlaWorldAdapter", lambda _world: "world-adapter")
    monkeypatch.setattr(scene, "FollowVehicleTopDown", _FakeFollowVehicleTopDown)

    scene._bind_manual_follow_target_with_retry(
        world=world,
        runtime=runtime,
        follow_vehicle_id=None,
        manual_control_target=scene.VehicleRefInput(scheme="role", value="ego"),
        synchronous_mode=True,
        max_attempts=3,
    )

    assert world.tick_calls == 1
    assert runtime.state.mode is scene.EditorMode.FOLLOW
    assert runtime.state.follow_vehicle_id == 7
