from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from vln_carla2.app import scene_editor_main


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
    def fake_managed_session(config: scene_editor_main.CarlaSessionConfig):
        captured["session_config"] = config
        yield SimpleNamespace(world=fake_world)

    def fake_build_operator_container(**kwargs: Any):
        captured["container_kwargs"] = kwargs
        return SimpleNamespace(runtime=runtime)

    monkeypatch.setattr(scene_editor_main, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(
        scene_editor_main,
        "build_operator_container",
        fake_build_operator_container,
    )

    result = scene_editor_main.run(
        scene_editor_main.SceneEditorSettings(
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
    assert runtime.max_ticks_calls == [3]


def test_run_passes_async_settings_to_session_and_container(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    runtime = _FakeRuntime(result=5, max_ticks_calls=[])

    @contextmanager
    def fake_managed_session(config: scene_editor_main.CarlaSessionConfig):
        captured["session_config"] = config
        yield SimpleNamespace(world=object())

    def fake_build_operator_container(**kwargs: Any):
        captured["container_kwargs"] = kwargs
        return SimpleNamespace(runtime=runtime)

    monkeypatch.setattr(scene_editor_main, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(
        scene_editor_main,
        "build_operator_container",
        fake_build_operator_container,
    )

    result = scene_editor_main.run(
        scene_editor_main.SceneEditorSettings(
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
    assert runtime.max_ticks_calls == [2]


def test_run_passes_follow_vehicle_id_to_container(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    runtime = _FakeRuntime(result=1, max_ticks_calls=[])

    @contextmanager
    def fake_managed_session(_config: scene_editor_main.CarlaSessionConfig):
        yield SimpleNamespace(world=object())

    def fake_build_operator_container(**kwargs: Any):
        captured["container_kwargs"] = kwargs
        return SimpleNamespace(runtime=runtime)

    monkeypatch.setattr(scene_editor_main, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(
        scene_editor_main,
        "build_operator_container",
        fake_build_operator_container,
    )

    result = scene_editor_main.run(
        scene_editor_main.SceneEditorSettings(
            synchronous_mode=True,
            tick_sleep_seconds=0.01,
            follow_vehicle_id=123,
        ),
        max_ticks=1,
    )

    assert result == 1
    assert captured["container_kwargs"]["follow_vehicle_id"] == 123
    assert runtime.max_ticks_calls == [1]
