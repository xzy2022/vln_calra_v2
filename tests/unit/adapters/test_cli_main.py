from typing import Any

import pytest

from vln_carla2.adapters.cli import main as cli_main


def test_main_passes_sync_mode_settings(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(settings: Any) -> None:
        captured["settings"] = settings

    monkeypatch.setattr(cli_main, "run_scene_editor", fake_run)

    exit_code = cli_main.main(
        [
            "--mode",
            "sync",
            "--render-mode",
            "no-rendering",
            "--tick-sleep-seconds",
            "0.01",
        ]
    )

    assert exit_code == 0
    assert captured["settings"].synchronous_mode is True
    assert captured["settings"].no_rendering_mode is True
    assert captured["settings"].tick_sleep_seconds == 0.01


def test_main_passes_async_mode_settings(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(settings: Any) -> None:
        captured["settings"] = settings

    monkeypatch.setattr(cli_main, "run_scene_editor", fake_run)

    exit_code = cli_main.main(["--mode", "async"])

    assert exit_code == 0
    assert captured["settings"].synchronous_mode is False


def test_main_launches_carla_with_offscreen_and_no_rendering(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeProcess:
        pid = 4321

        def __init__(self) -> None:
            self._exit_code: int | None = None

        def poll(self) -> int | None:
            return self._exit_code

    monkeypatch.setattr(cli_main, "run_scene_editor", lambda _settings: None)
    monkeypatch.setattr(cli_main, "is_carla_server_reachable", lambda *_args, **_kwargs: False)

    def fake_launch(**kwargs: Any) -> FakeProcess:
        captured["launch_kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(cli_main, "launch_carla_server", fake_launch)
    monkeypatch.setattr(cli_main, "wait_for_carla_server", lambda **_kwargs: None)
    monkeypatch.setattr(
        cli_main,
        "terminate_carla_server",
        lambda process: captured.setdefault("terminated", process.pid),
    )

    exit_code = cli_main.main(
        [
            "--launch-carla",
            "--carla-exe",
            "C:/CARLA/CarlaUE4.exe",
            "--window-mode",
            "offscreen",
            "--render-mode",
            "no-rendering",
        ]
    )

    assert exit_code == 0
    assert captured["launch_kwargs"]["offscreen"] is True
    assert captured["launch_kwargs"]["no_rendering"] is True
    assert captured["terminated"] == 4321


def test_main_exits_cleanly_on_ctrl_c(monkeypatch) -> None:
    def fake_run(_settings: Any) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli_main, "run_scene_editor", fake_run)

    exit_code = cli_main.main([])

    assert exit_code == 0


def test_main_rejects_invalid_mode() -> None:
    with pytest.raises(SystemExit) as exc:
        cli_main.main(["--mode", "invalid"])

    assert exc.value.code == 2


def test_main_fails_if_server_running_without_reuse(monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "is_carla_server_reachable", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(cli_main, "run_scene_editor", lambda _settings: None)

    exit_code = cli_main.main(
        [
            "--launch-carla",
            "--carla-exe",
            "C:/CARLA/CarlaUE4.exe",
        ]
    )

    assert exit_code == 2
