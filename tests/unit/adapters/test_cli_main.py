import argparse
import json
from pathlib import Path
from typing import Any

import pytest

from vln_carla2.adapters.cli import main as cli_main
from vln_carla2.usecases.operator.models import VehicleDescriptor


def test_build_parser_uses_carla_exe_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_main, "_load_env_from_dotenv", lambda: None)
    monkeypatch.setenv("CARLA_UE4_EXE", "C:/CARLA/CarlaUE4.exe")

    parser = cli_main.build_parser()
    args = parser.parse_args(["scene", "run"])

    assert args.carla_exe == "C:/CARLA/CarlaUE4.exe"
    assert not hasattr(args, "follow_vehicle_id")
    assert not hasattr(args, "follow")


def test_load_env_from_dotenv_reads_carla_exe(monkeypatch: pytest.MonkeyPatch) -> None:
    dotenv = Path(".env.test.cli")
    dotenv.write_text("CARLA_UE4_EXE=C:/CARLA/FromDotEnv.exe\n", encoding="utf-8")
    monkeypatch.delenv("CARLA_UE4_EXE", raising=False)

    try:
        cli_main._load_env_from_dotenv(str(dotenv))
        assert cli_main.os.getenv("CARLA_UE4_EXE") == "C:/CARLA/FromDotEnv.exe"
    finally:
        dotenv.unlink(missing_ok=True)


def test_load_env_from_dotenv_reads_carla_exe_with_utf8_bom(monkeypatch: pytest.MonkeyPatch) -> None:
    dotenv = Path(".env.test.cli.bom")
    dotenv.write_bytes(b"\xef\xbb\xbfCARLA_UE4_EXE=C:/CARLA/FromBom.exe\n")
    monkeypatch.delenv("CARLA_UE4_EXE", raising=False)

    try:
        cli_main._load_env_from_dotenv(str(dotenv))
        assert cli_main.os.getenv("CARLA_UE4_EXE") == "C:/CARLA/FromBom.exe"
    finally:
        dotenv.unlink(missing_ok=True)


def test_main_scene_run_passes_sync_mode_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(settings: Any) -> None:
        captured["settings"] = settings

    monkeypatch.setattr(cli_main, "run_scene_editor", fake_run)

    exit_code = cli_main.main(
        [
            "scene",
            "run",
            "--mode",
            "sync",
            "--no-rendering",
            "--tick-sleep-seconds",
            "0.01",
        ]
    )

    assert exit_code == 0
    assert captured["settings"].synchronous_mode is True
    assert captured["settings"].no_rendering_mode is True
    assert captured["settings"].offscreen_mode is False
    assert captured["settings"].tick_sleep_seconds == 0.01
    assert captured["settings"].follow_vehicle_id is None


def test_main_rejects_legacy_root_scene_args() -> None:
    with pytest.raises(SystemExit) as exc:
        cli_main.main(["--mode", "sync"])

    assert exc.value.code == 2


def test_main_launches_carla_with_offscreen_and_no_rendering(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeProcess:
        pid = 4321

        def __init__(self) -> None:
            self._exit_code: int | None = None

        def poll(self) -> int | None:
            return self._exit_code

    def fake_run(settings: Any) -> None:
        captured["settings"] = settings

    monkeypatch.setattr(cli_main, "run_scene_editor", fake_run)
    monkeypatch.setattr(cli_main, "is_carla_server_reachable", lambda *_args, **_kwargs: False)

    def fake_launch(**kwargs: Any) -> FakeProcess:
        captured["launch_kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(cli_main, "launch_carla_server", fake_launch)
    monkeypatch.setattr(cli_main, "wait_for_carla_server", lambda **_kwargs: None)
    monkeypatch.setattr(
        cli_main,
        "record_runtime_session_config",
        lambda config, owner_pid=None: captured.setdefault(
            "recorded",
            {"offscreen_mode": config.offscreen_mode, "owner_pid": owner_pid},
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "clear_runtime_session_config",
        lambda host, port: captured.setdefault("cleared", {"host": host, "port": port}),
    )
    monkeypatch.setattr(
        cli_main,
        "terminate_carla_server",
        lambda process: captured.setdefault("terminated", process.pid),
    )

    exit_code = cli_main.main(
        [
            "scene",
            "run",
            "--launch-carla",
            "--carla-exe",
            "C:/CARLA/CarlaUE4.exe",
            "--offscreen",
            "--no-rendering",
        ]
    )

    assert exit_code == 0
    assert captured["launch_kwargs"]["offscreen"] is True
    assert captured["launch_kwargs"]["no_rendering"] is True
    assert captured["launch_kwargs"]["quality_level"] == "Epic"
    assert captured["settings"].offscreen_mode is True
    assert captured["settings"].no_rendering_mode is True
    assert captured["recorded"]["offscreen_mode"] is True
    assert captured["recorded"]["owner_pid"] == 4321
    assert captured["cleared"] == {"host": "127.0.0.1", "port": 2000}
    assert captured["terminated"] == 4321


def test_main_exits_cleanly_on_ctrl_c(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_settings: Any) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli_main, "run_scene_editor", fake_run)

    exit_code = cli_main.main(["scene", "run"])

    assert exit_code == 0


def test_build_session_config_sets_offscreen_from_args() -> None:
    args = argparse.Namespace(
        host="127.0.0.1",
        port=2000,
        timeout_seconds=10.0,
        map_name="Town10HD_Opt",
        mode="sync",
        fixed_delta_seconds=0.05,
        no_rendering=False,
        offscreen=True,
    )

    config = cli_main._build_session_config(args)

    assert config.offscreen_mode is True


def test_build_session_config_defaults_offscreen_false_when_arg_missing() -> None:
    args = argparse.Namespace(
        host="127.0.0.1",
        port=2000,
        timeout_seconds=10.0,
        map_name="Town10HD_Opt",
        mode="sync",
        fixed_delta_seconds=0.05,
        no_rendering=False,
    )

    config = cli_main._build_session_config(args)

    assert config.offscreen_mode is False


def test_main_rejects_invalid_mode_for_legacy_entry() -> None:
    with pytest.raises(SystemExit) as exc:
        cli_main.main(["--mode", "invalid"])

    assert exc.value.code == 2


@pytest.mark.parametrize(
    "removed_flag, value",
    [
        ("--window-mode", "offscreen"),
        ("--render-mode", "no-rendering"),
    ],
)
def test_main_rejects_removed_scene_run_flags(removed_flag: str, value: str) -> None:
    with pytest.raises(SystemExit) as exc:
        cli_main.main(["scene", "run", removed_flag, value])

    assert exc.value.code == 2


def test_main_fails_if_server_running_without_reuse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_main, "is_carla_server_reachable", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(cli_main, "run_scene_editor", lambda _settings: None)

    exit_code = cli_main.main(
        [
            "scene",
            "run",
            "--launch-carla",
            "--carla-exe",
            "C:/CARLA/CarlaUE4.exe",
        ]
    )

    assert exit_code == 2


def test_vehicle_list_outputs_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vehicles = [
        VehicleDescriptor(
            actor_id=7,
            type_id="vehicle.tesla.model3",
            role_name="ego",
            x=1.0,
            y=2.0,
            z=0.1,
        ),
        VehicleDescriptor(
            actor_id=8,
            type_id="vehicle.audi.tt",
            role_name="npc",
            x=3.0,
            y=4.0,
            z=0.2,
        ),
    ]

    class FakeUsecase:
        def run(self) -> list[VehicleDescriptor]:
            return vehicles

    class FakeContainer:
        list_vehicles = FakeUsecase()

    def fake_with_operator_container(_args: Any, *, operation: Any, sleep_seconds: float = 0.0) -> Any:
        del sleep_seconds
        return operation(FakeContainer(), object())

    monkeypatch.setattr(cli_main, "_with_operator_container", fake_with_operator_container)

    exit_code = cli_main.main(["vehicle", "list", "--format", "json"])
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert isinstance(payload, list)
    assert payload[0]["actor_id"] == 7
    assert payload[1]["role_name"] == "npc"


def test_vehicle_spawn_outputs_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, Any] = {}
    spawned = VehicleDescriptor(
        actor_id=99,
        type_id="vehicle.tesla.model3",
        role_name="ego",
        x=9.0,
        y=8.0,
        z=0.3,
    )

    class FakeUsecase:
        def run(self, request: Any) -> VehicleDescriptor:
            captured["request"] = request
            return spawned

    class FakeContainer:
        spawn_vehicle = FakeUsecase()

    def fake_with_operator_container(_args: Any, *, operation: Any, sleep_seconds: float = 0.0) -> Any:
        del sleep_seconds
        return operation(FakeContainer(), object())

    monkeypatch.setattr(cli_main, "_with_operator_container", fake_with_operator_container)

    exit_code = cli_main.main(["vehicle", "spawn", "--role-name", "ego", "--output", "json"])
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert captured["request"].role_name == "ego"
    assert payload["actor_id"] == 99
    assert payload["type_id"] == "vehicle.tesla.model3"


def test_spectator_follow_runs_scene_editor_with_resolved_follow_and_z(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeResolver:
        def run(self, ref: Any) -> VehicleDescriptor:
            captured["ref"] = ref
            return VehicleDescriptor(
                actor_id=42,
                type_id="vehicle.tesla.model3",
                role_name="ego",
                x=0.0,
                y=0.0,
                z=0.0,
            )

    class FakeContainer:
        resolve_vehicle_ref = FakeResolver()

    def fake_with_operator_container(_args: Any, *, operation: Any, sleep_seconds: float = 0.0) -> Any:
        captured["sleep_seconds"] = sleep_seconds
        return operation(FakeContainer(), object())

    def fake_run_scene_editor(settings: Any) -> None:
        captured["settings"] = settings

    monkeypatch.setattr(cli_main, "_read_session_offscreen_mode", lambda _args: False)
    monkeypatch.setattr(cli_main, "_with_operator_container", fake_with_operator_container)
    monkeypatch.setattr(cli_main, "run_scene_editor", fake_run_scene_editor)

    exit_code = cli_main.main(["spectator", "follow", "--follow", "role:ego", "--z", "30"])

    assert exit_code == 0
    assert captured["ref"].scheme == "role"
    assert captured["ref"].value == "ego"
    assert captured["settings"].follow_vehicle_id == 42
    assert captured["settings"].spectator_initial_z == 30.0


def test_spectator_follow_exits_cleanly_on_ctrl_c(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_settings: Any) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli_main, "_read_session_offscreen_mode", lambda _args: False)
    monkeypatch.setattr(cli_main, "run_scene_editor", fake_run)

    exit_code = cli_main.main(["spectator", "follow", "--follow", "actor:7"])

    assert exit_code == 0


def test_spectator_follow_rejects_invalid_follow_ref(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli_main, "_read_session_offscreen_mode", lambda _args: False)
    monkeypatch.setattr(cli_main, "run_scene_editor", lambda _settings: None)

    exit_code = cli_main.main(["spectator", "follow", "--follow", "bad-ref"])
    stderr = capsys.readouterr().err

    assert exit_code == 2
    assert "Invalid vehicle ref" in stderr


def test_spectator_follow_offscreen_warns_and_skips(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    called = {"resolved": False, "run": False}

    def fake_with_operator_container(_args: Any, *, operation: Any, sleep_seconds: float = 0.0) -> Any:
        del operation, sleep_seconds
        called["resolved"] = True
        return None

    def fake_run_scene_editor(_settings: Any) -> None:
        called["run"] = True

    monkeypatch.setattr(cli_main, "_read_session_offscreen_mode", lambda _args: True)
    monkeypatch.setattr(cli_main, "_with_operator_container", fake_with_operator_container)
    monkeypatch.setattr(cli_main, "run_scene_editor", fake_run_scene_editor)

    exit_code = cli_main.main(["spectator", "follow", "--follow", "role:ego"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert "[WARN] spectator follow skipped in offscreen mode." in stdout
    assert called["resolved"] is False
    assert called["run"] is False


def test_read_session_offscreen_mode_reads_from_carla_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_read_runtime_offscreen_mode(host: str, port: int) -> bool | None:
        captured["host"] = host
        captured["port"] = port
        return True

    monkeypatch.setattr(cli_main, "read_runtime_offscreen_mode", fake_read_runtime_offscreen_mode)

    args = argparse.Namespace(host="127.0.0.1", port=2000)
    assert cli_main._read_session_offscreen_mode(args) is True
    assert captured == {"host": "127.0.0.1", "port": 2000}


def test_spectator_follow_rejects_removed_offscreen_flag() -> None:
    with pytest.raises(SystemExit) as exc:
        cli_main.main(["spectator", "follow", "--follow", "role:ego", "--offscreen"])

    assert exc.value.code == 2


@pytest.mark.parametrize(
    "removed_flag, value",
    [
        ("--follow", "role:ego"),
        ("--follow-vehicle-id", "42"),
    ],
)
def test_scene_run_rejects_removed_follow_flags(removed_flag: str, value: str) -> None:
    with pytest.raises(SystemExit) as exc:
        cli_main.main(["scene", "run", removed_flag, value])

    assert exc.value.code == 2
