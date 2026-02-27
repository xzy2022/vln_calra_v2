import argparse
import json
from pathlib import Path
from typing import Any

import pytest

from vln_carla2.app import cli_main as cli_main
from vln_carla2.usecases.operator.ports.vehicle_dto import VehicleDescriptor


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
    assert captured["settings"].scene_import_path is None
    assert captured["settings"].scene_export_path is None
    assert captured["settings"].follow_vehicle_id is None
    assert captured["settings"].start_in_follow_mode is False
    assert captured["settings"].allow_mode_toggle is True
    assert captured["settings"].allow_spawn_vehicle_hotkey is True


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


def test_main_scene_run_passes_scene_import_and_export_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(settings: Any) -> None:
        captured["settings"] = settings

    monkeypatch.setattr(cli_main, "run_scene_editor", fake_run)

    exit_code = cli_main.main(
        [
            "scene",
            "run",
            "--scene-import",
            "fixtures/in_scene.json",
            "--scene-export-path",
            "artifacts/out_scene.json",
        ]
    )

    assert exit_code == 0
    assert captured["settings"].scene_import_path == "fixtures/in_scene.json"
    assert captured["settings"].scene_export_path == "artifacts/out_scene.json"


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
    assert captured["settings"].start_in_follow_mode is True
    assert captured["settings"].allow_mode_toggle is False
    assert captured["settings"].allow_spawn_vehicle_hotkey is False


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


def test_build_parser_supports_operator_run_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_main, "_load_env_from_dotenv", lambda: None)

    parser = cli_main.build_parser()
    args = parser.parse_args(["operator", "run"])

    assert args.follow == "role:ego"
    assert args.strategy == "parallel"
    assert args.spawn_if_missing is True
    assert args.steps == 80
    assert args.target_speed_mps == 5.0
    assert args.operator_warmup_ticks == 1


def test_operator_run_builds_settings_and_calls_workflow(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_operator_workflow(settings: Any) -> Any:
        captured["settings"] = settings
        return argparse.Namespace(
            strategy="parallel",
            vehicle_source="resolved",
            selected_vehicle=argparse.Namespace(actor_id=42),
            operator_ticks=3,
            control_loop_result=argparse.Namespace(executed_steps=3),
        )

    monkeypatch.setattr(cli_main, "run_operator_workflow", fake_run_operator_workflow)

    exit_code = cli_main.main(
        [
            "operator",
            "run",
            "--follow",
            "role:ego",
            "--strategy",
            "serial",
            "--steps",
            "3",
            "--target-speed-mps",
            "4.5",
            "--operator-warmup-ticks",
            "2",
            "--z",
            "30",
        ]
    )
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert captured["settings"].vehicle_ref.scheme == "role"
    assert captured["settings"].vehicle_ref.value == "ego"
    assert captured["settings"].strategy == "serial"
    assert captured["settings"].steps == 3
    assert captured["settings"].target_speed_mps == 4.5
    assert captured["settings"].operator_warmup_ticks == 2
    assert captured["settings"].spectator_initial_z == 30.0
    assert "operator workflow finished" in stdout


def test_operator_run_rejects_invalid_vehicle_ref(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli_main, "run_operator_workflow", lambda _settings: None)

    exit_code = cli_main.main(["operator", "run", "--follow", "bad-ref"])
    stderr = capsys.readouterr().err

    assert exit_code == 2
    assert "Invalid vehicle ref" in stderr


def test_build_parser_supports_exp_run_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_main, "_load_env_from_dotenv", lambda: None)

    parser = cli_main.build_parser()
    args = parser.parse_args(["exp", "run", "--scene-json", "artifacts/scene_out.json"])

    assert args.scene_json == "artifacts/scene_out.json"
    assert args.control_target == "role:ego"
    assert args.forward_distance_m == 20.0
    assert args.target_speed_mps == 5.0
    assert args.max_steps == 800


def test_exp_run_uses_scene_map_and_calls_exp_workflow(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, Any] = {}
    original_build_session_config = cli_main._build_session_config

    def fake_load_scene_template(path: str) -> Any:
        captured["scene_json"] = path
        return argparse.Namespace(map_name="Town05")

    def fake_build_session_config(args: argparse.Namespace, *, map_name_override: str | None = None):
        captured["map_name_override"] = map_name_override
        return original_build_session_config(args, map_name_override=map_name_override)

    def fake_run_exp_workflow(settings: Any) -> Any:
        captured["settings"] = settings
        return argparse.Namespace(
            control_target=settings.control_target,
            selected_vehicle=argparse.Namespace(actor_id=77),
            scene_map_name="Town05",
            imported_objects=4,
            forward_distance_m=settings.forward_distance_m,
            exp_workflow_result=argparse.Namespace(
                traveled_distance_m=20.5,
                entered_forbidden_zone=True,
                control_loop_result=argparse.Namespace(executed_steps=3),
            ),
        )

    monkeypatch.setattr(cli_main, "_load_scene_template", fake_load_scene_template)
    monkeypatch.setattr(cli_main, "_build_session_config", fake_build_session_config)
    monkeypatch.setattr(cli_main, "run_exp_workflow", fake_run_exp_workflow)

    exit_code = cli_main.main(
        [
            "exp",
            "run",
            "--scene-json",
            "artifacts/scene_out.json",
            "--control-target",
            "actor:77",
            "--map-name",
            "Town10HD_Opt",
            "--forward-distance-m",
            "20",
            "--target-speed-mps",
            "4.0",
            "--max-steps",
            "600",
        ]
    )
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert captured["scene_json"] == "artifacts/scene_out.json"
    assert captured["map_name_override"] == "Town05"
    assert captured["settings"].scene_json_path == "artifacts/scene_out.json"
    assert captured["settings"].control_target.scheme == "actor"
    assert captured["settings"].control_target.value == "77"
    assert captured["settings"].forward_distance_m == 20.0
    assert captured["settings"].target_speed_mps == 4.0
    assert captured["settings"].max_steps == 600
    assert "exp workflow finished" in stdout
    assert "entered_forbidden_zone=True" in stdout
    assert "[RESULT] forbidden_zone=ENTERED entered_forbidden_zone=True" in stdout


def test_exp_run_rejects_invalid_control_target(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli_main,
        "_load_scene_template",
        lambda _path: argparse.Namespace(map_name="Town10HD_Opt"),
    )
    monkeypatch.setattr(cli_main, "run_exp_workflow", lambda _settings: None)

    exit_code = cli_main.main(
        ["exp", "run", "--scene-json", "artifacts/scene_out.json", "--control-target", "bad-ref"]
    )
    stderr = capsys.readouterr().err

    assert exit_code == 2
    assert "Invalid vehicle ref" in stderr

