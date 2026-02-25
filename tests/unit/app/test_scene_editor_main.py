from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from vln_carla2.app import scene_editor_main


def _settings_copy(settings: Any) -> SimpleNamespace:
    return SimpleNamespace(
        synchronous_mode=settings.synchronous_mode,
        no_rendering_mode=settings.no_rendering_mode,
        fixed_delta_seconds=settings.fixed_delta_seconds,
    )


@dataclass
class _FakeWorld:
    map_name: str
    tick_calls: int = 0

    def __post_init__(self) -> None:
        self._settings = SimpleNamespace(
            synchronous_mode=False,
            no_rendering_mode=False,
            fixed_delta_seconds=None,
        )
        self.applied_settings: list[SimpleNamespace] = []

    def get_map(self) -> SimpleNamespace:
        return SimpleNamespace(name=f"/Game/Carla/Maps/{self.map_name}")

    def get_settings(self) -> SimpleNamespace:
        return _settings_copy(self._settings)

    def apply_settings(self, settings: Any) -> None:
        copied = _settings_copy(settings)
        self._settings = copied
        self.applied_settings.append(copied)

    def tick(self) -> int:
        self.tick_calls += 1
        return self.tick_calls


class _FakeClient:
    def __init__(self, world: _FakeWorld) -> None:
        self._world = world
        self.load_world_calls: list[str] = []
        self.timeout_seconds: float | None = None
        self.connected: tuple[str, int] | None = None

    def set_timeout(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds

    def get_world(self) -> _FakeWorld:
        return self._world

    def load_world(self, map_name: str) -> _FakeWorld:
        self.load_world_calls.append(map_name)
        self._world = _FakeWorld(map_name=map_name)
        return self._world


class _FakeCarla:
    def __init__(self, client: _FakeClient) -> None:
        self._client = client

    def Client(self, host: str, port: int) -> _FakeClient:
        self._client.connected = (host, port)
        return self._client


def test_run_configures_sync_mode_and_restores_settings(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    client = _FakeClient(world=_FakeWorld(map_name="Town10HD_Opt"))

    class FakeRuntime:
        def __init__(
            self,
            world: Any,
            synchronous_mode: bool,
            sleep_seconds: float,
            follow_vehicle_id: int | None,
        ) -> None:
            captured["runtime_world"] = world
            captured["runtime_sync"] = synchronous_mode
            captured["runtime_sleep"] = sleep_seconds
            captured["follow_vehicle_id"] = follow_vehicle_id

        def run(self, *, max_ticks: int | None = None) -> int:
            captured["max_ticks"] = max_ticks
            return 11

    monkeypatch.setattr(scene_editor_main, "require_carla", lambda: _FakeCarla(client))
    monkeypatch.setattr(scene_editor_main, "CliRuntime", FakeRuntime)
    monkeypatch.setattr(
        scene_editor_main,
        "restore_world_settings",
        lambda world, original: captured.setdefault("restored", (world, original)),
    )

    result = scene_editor_main.run(
        scene_editor_main.SceneEditorSettings(
            synchronous_mode=True,
            fixed_delta_seconds=0.05,
            no_rendering_mode=True,
            tick_sleep_seconds=0.02,
        ),
        max_ticks=3,
    )

    runtime_world = captured["runtime_world"]
    applied = runtime_world.applied_settings[-1]
    restored_world, _restored_original = captured["restored"]

    assert result == 11
    assert captured["runtime_sync"] is True
    assert captured["runtime_sleep"] == 0.02
    assert captured["follow_vehicle_id"] is None
    assert captured["max_ticks"] == 3
    assert applied.synchronous_mode is True
    assert applied.no_rendering_mode is True
    assert applied.fixed_delta_seconds == 0.05
    assert runtime_world.tick_calls == 1
    assert restored_world is runtime_world


def test_run_configures_async_mode_without_startup_tick(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    client = _FakeClient(world=_FakeWorld(map_name="Town01"))

    class FakeRuntime:
        def __init__(
            self,
            world: Any,
            synchronous_mode: bool,
            sleep_seconds: float,
            follow_vehicle_id: int | None,
        ) -> None:
            captured["runtime_world"] = world
            captured["runtime_sync"] = synchronous_mode
            captured["runtime_sleep"] = sleep_seconds
            captured["follow_vehicle_id"] = follow_vehicle_id

        def run(self, *, max_ticks: int | None = None) -> int:
            captured["max_ticks"] = max_ticks
            return 5

    monkeypatch.setattr(scene_editor_main, "require_carla", lambda: _FakeCarla(client))
    monkeypatch.setattr(scene_editor_main, "CliRuntime", FakeRuntime)
    monkeypatch.setattr(scene_editor_main, "restore_world_settings", lambda *_args: None)

    result = scene_editor_main.run(
        scene_editor_main.SceneEditorSettings(
            map_name="Town10HD_Opt",
            synchronous_mode=False,
            fixed_delta_seconds=0.05,
            tick_sleep_seconds=0.01,
        ),
        max_ticks=2,
    )

    runtime_world = captured["runtime_world"]
    applied = runtime_world.applied_settings[-1]

    assert result == 5
    assert client.load_world_calls == ["Town10HD_Opt"]
    assert captured["runtime_sync"] is False
    assert captured["runtime_sleep"] == 0.01
    assert captured["follow_vehicle_id"] is None
    assert captured["max_ticks"] == 2
    assert applied.synchronous_mode is False
    assert applied.fixed_delta_seconds is None
    assert runtime_world.tick_calls == 0


def test_run_passes_follow_vehicle_id_to_runtime(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    client = _FakeClient(world=_FakeWorld(map_name="Town10HD_Opt"))

    class FakeRuntime:
        def __init__(
            self,
            world: Any,
            synchronous_mode: bool,
            sleep_seconds: float,
            follow_vehicle_id: int | None,
        ) -> None:
            captured["runtime_world"] = world
            captured["runtime_sync"] = synchronous_mode
            captured["runtime_sleep"] = sleep_seconds
            captured["follow_vehicle_id"] = follow_vehicle_id

        def run(self, *, max_ticks: int | None = None) -> int:
            captured["max_ticks"] = max_ticks
            return 1

    monkeypatch.setattr(scene_editor_main, "require_carla", lambda: _FakeCarla(client))
    monkeypatch.setattr(scene_editor_main, "CliRuntime", FakeRuntime)
    monkeypatch.setattr(scene_editor_main, "restore_world_settings", lambda *_args: None)

    result = scene_editor_main.run(
        scene_editor_main.SceneEditorSettings(
            synchronous_mode=True,
            tick_sleep_seconds=0.01,
            follow_vehicle_id=123,
        ),
        max_ticks=1,
    )

    assert result == 1
    assert captured["follow_vehicle_id"] == 123
