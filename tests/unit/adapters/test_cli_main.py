from types import SimpleNamespace
from typing import Any

from vln_carla2.adapters.cli import main as cli_main


def _loop_result() -> SimpleNamespace:
    return SimpleNamespace(
        executed_steps=1,
        last_frame=10,
        last_speed_mps=2.5,
        avg_speed_mps=2.0,
    )


def test_main_uses_no_rendering_world_settings(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(settings: Any) -> Any:
        captured["settings"] = settings
        return _loop_result()

    monkeypatch.setattr(cli_main, "run", fake_run)

    exit_code = cli_main.main(["--render-mode", "no-rendering", "--steps", "1"])

    assert exit_code == 0
    assert captured["settings"].no_rendering_mode is True


def test_main_launches_carla_with_offscreen_mode(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeProcess:
        pid = 4321

        def __init__(self) -> None:
            self._exit_code: int | None = None

        def poll(self) -> int | None:
            return self._exit_code

    def fake_run(settings: Any) -> Any:
        captured["settings"] = settings
        return _loop_result()

    def fake_launch(**kwargs: Any) -> FakeProcess:
        captured["launch_kwargs"] = kwargs
        return FakeProcess()

    def fake_wait(**kwargs: Any) -> None:
        captured["wait_kwargs"] = kwargs

    def fake_terminate(process: Any) -> None:
        captured["terminated"] = process.pid

    monkeypatch.setattr(cli_main, "run", fake_run)
    monkeypatch.setattr(cli_main, "is_carla_server_reachable", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(cli_main, "launch_carla_server", fake_launch)
    monkeypatch.setattr(cli_main, "wait_for_carla_server", fake_wait)
    monkeypatch.setattr(cli_main, "terminate_carla_server", fake_terminate)

    exit_code = cli_main.main(
        [
            "--launch-carla",
            "--carla-exe",
            "C:/CARLA/CarlaUE4.exe",
            "--render-mode",
            "offscreen",
            "--steps",
            "1",
        ]
    )

    assert exit_code == 0
    assert captured["launch_kwargs"]["offscreen"] is True
    assert captured["launch_kwargs"]["no_rendering"] is False
    assert captured["settings"].no_rendering_mode is False
    assert captured["terminated"] == 4321


def test_main_launches_carla_with_no_rendering_mode(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeProcess:
        pid = 7788

        def __init__(self) -> None:
            self._exit_code: int | None = None

        def poll(self) -> int | None:
            return self._exit_code

    def fake_run(settings: Any) -> Any:
        captured["settings"] = settings
        return _loop_result()

    def fake_launch(**kwargs: Any) -> FakeProcess:
        captured["launch_kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(cli_main, "run", fake_run)
    monkeypatch.setattr(cli_main, "is_carla_server_reachable", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(cli_main, "launch_carla_server", fake_launch)
    monkeypatch.setattr(cli_main, "wait_for_carla_server", lambda **_kwargs: None)
    monkeypatch.setattr(cli_main, "terminate_carla_server", lambda process: captured.setdefault("terminated", process.pid))

    exit_code = cli_main.main(
        [
            "--launch-carla",
            "--carla-exe",
            "C:/CARLA/CarlaUE4.exe",
            "--render-mode",
            "no-rendering",
            "--steps",
            "1",
        ]
    )

    assert exit_code == 0
    assert captured["launch_kwargs"]["offscreen"] is True
    assert captured["launch_kwargs"]["no_rendering"] is True
    assert captured["settings"].no_rendering_mode is True
    assert captured["terminated"] == 7788


def test_main_fails_if_server_running_without_reuse(monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "is_carla_server_reachable", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(cli_main, "run", lambda _settings: _loop_result())

    exit_code = cli_main.main(
        [
            "--launch-carla",
            "--carla-exe",
            "C:/CARLA/CarlaUE4.exe",
            "--steps",
            "1",
        ]
    )

    assert exit_code == 2
