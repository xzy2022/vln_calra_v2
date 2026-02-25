from typing import Any
from pathlib import Path

import pytest

from vln_carla2.adapters.cli import main as cli_main


def test_build_parser_uses_carla_exe_from_env(monkeypatch) -> None:
    monkeypatch.setattr(cli_main, "_load_env_from_dotenv", lambda: None)
    monkeypatch.setenv("CARLA_UE4_EXE", "C:/CARLA/CarlaUE4.exe")

    parser = cli_main.build_parser()
    args = parser.parse_args([])

    assert args.carla_exe == "C:/CARLA/CarlaUE4.exe"
    assert args.follow_vehicle_id is None


def test_load_env_from_dotenv_reads_carla_exe(monkeypatch) -> None:
    dotenv = Path(".env.test.cli")
    dotenv.write_text("CARLA_UE4_EXE=C:/CARLA/FromDotEnv.exe\n", encoding="utf-8")
    monkeypatch.delenv("CARLA_UE4_EXE", raising=False)

    try:
        cli_main._load_env_from_dotenv(str(dotenv))
        assert cli_main.os.getenv("CARLA_UE4_EXE") == "C:/CARLA/FromDotEnv.exe"
    finally:
        dotenv.unlink(missing_ok=True)


def test_load_env_from_dotenv_reads_carla_exe_with_utf8_bom(monkeypatch) -> None:
    dotenv = Path(".env.test.cli.bom")
    dotenv.write_bytes(b"\xef\xbb\xbfCARLA_UE4_EXE=C:/CARLA/FromBom.exe\n")
    monkeypatch.delenv("CARLA_UE4_EXE", raising=False)

    try:
        cli_main._load_env_from_dotenv(str(dotenv))
        assert cli_main.os.getenv("CARLA_UE4_EXE") == "C:/CARLA/FromBom.exe"
    finally:
        dotenv.unlink(missing_ok=True)


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
    assert captured["settings"].follow_vehicle_id is None


def test_main_passes_async_mode_settings(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(settings: Any) -> None:
        captured["settings"] = settings

    monkeypatch.setattr(cli_main, "run_scene_editor", fake_run)

    exit_code = cli_main.main(["--mode", "async"])

    assert exit_code == 0
    assert captured["settings"].synchronous_mode is False


def test_main_passes_follow_vehicle_id(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(settings: Any) -> None:
        captured["settings"] = settings

    monkeypatch.setattr(cli_main, "run_scene_editor", fake_run)

    exit_code = cli_main.main(["--follow-vehicle-id", "42"])

    assert exit_code == 0
    assert captured["settings"].follow_vehicle_id == 42


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
