import json
from dataclasses import dataclass, field
from typing import Any

from vln_carla2.adapters.cli.dispatch import CliDispatchConfig, dispatch_args
from vln_carla2.adapters.cli.parser import build_parser
from vln_carla2.app import cli_main
from vln_carla2.usecases.cli.dto import (
    ExpRunResult,
    ExpWorkflowExecution,
    OperatorRunResult,
    OperatorWorkflowExecution,
    SceneRunResult,
    SpectatorFollowResult,
    TrackingRunResult,
    TrackingWorkflowExecution,
    VehicleRefInput,
)
from vln_carla2.usecases.cli.errors import CliRuntimeError, CliUsageError
from vln_carla2.usecases.runtime.ports.vehicle_dto import VehicleDescriptor


@dataclass
class _FakeApp:
    scene_calls: list[Any] = field(default_factory=list)
    operator_calls: list[Any] = field(default_factory=list)
    exp_calls: list[Any] = field(default_factory=list)
    tracking_calls: list[Any] = field(default_factory=list)
    spectator_calls: list[Any] = field(default_factory=list)
    vehicle_list_calls: list[Any] = field(default_factory=list)
    vehicle_spawn_calls: list[Any] = field(default_factory=list)

    def run_scene(self, request: Any) -> SceneRunResult:
        self.scene_calls.append(request)
        return SceneRunResult(mode=request.mode, host=request.host, port=request.port)

    def run_operator(self, request: Any) -> OperatorRunResult:
        self.operator_calls.append(request)
        return OperatorRunResult(
            host=request.host,
            port=request.port,
            execution=OperatorWorkflowExecution(
                strategy="parallel",
                vehicle_source="resolved",
                actor_id=7,
                operator_ticks=3,
                control_steps=5,
            ),
        )

    def run_exp(self, request: Any) -> ExpRunResult:
        self.exp_calls.append(request)
        return ExpRunResult(
            host=request.host,
            port=request.port,
            execution=ExpWorkflowExecution(
                control_target=VehicleRefInput(scheme="role", value="ego"),
                actor_id=7,
                scene_map_name="Town10HD_Opt",
                imported_objects=1,
                forward_distance_m=20.0,
                traveled_distance_m=20.5,
                entered_forbidden_zone=False,
                control_steps=5,
                metrics_path="runs/20260228_161718/results/ep_000001/metrics.json",
            ),
        )

    def run_tracking(self, request: Any) -> TrackingRunResult:
        self.tracking_calls.append(request)
        return TrackingRunResult(
            host=request.host,
            port=request.port,
            execution=TrackingWorkflowExecution(
                control_target=VehicleRefInput(scheme="role", value="ego"),
                actor_id=7,
                scene_map_name="Town10HD_Opt",
                imported_objects=1,
                reached_goal=True,
                termination_reason="goal_reached",
                executed_steps=12,
                final_distance_to_goal_m=0.4,
                final_yaw_error_deg=2.0,
                route_points=120,
                metrics_path="runs/20260228_161718/results/ep_000001/tracking_metrics.json",
            ),
        )

    def list_vehicles(self, command: Any) -> list[VehicleDescriptor]:
        self.vehicle_list_calls.append(command)
        return [
            VehicleDescriptor(
                actor_id=7,
                type_id="vehicle.tesla.model3",
                role_name="ego",
                x=1.0,
                y=2.0,
                z=0.1,
            )
        ]

    def spawn_vehicle(self, command: Any) -> VehicleDescriptor:
        self.vehicle_spawn_calls.append(command)
        return VehicleDescriptor(
            actor_id=99,
            type_id="vehicle.tesla.model3",
            role_name="ego",
            x=9.0,
            y=8.0,
            z=0.3,
        )

    def run_spectator_follow(self, request: Any) -> SpectatorFollowResult:
        self.spectator_calls.append(request)
        return SpectatorFollowResult(mode=request.mode, host=request.host, port=request.port)


def test_main_delegates_to_adapter(monkeypatch) -> None:
    sentinel_app = object()
    sentinel_config = CliDispatchConfig(default_carla_exe="C:/CARLA/FromEntry.exe")
    captured: dict[str, Any] = {}

    monkeypatch.setattr(cli_main, "build_cli_application", lambda: sentinel_app)
    monkeypatch.setattr(cli_main, "build_cli_dispatch_config", lambda: sentinel_config)

    def fake_run_cli(argv, app, *, config):
        captured["argv"] = argv
        captured["app"] = app
        captured["config"] = config
        return 7

    monkeypatch.setattr(cli_main, "run_cli", fake_run_cli)

    exit_code = cli_main.main(["scene", "run"])

    assert exit_code == 7
    assert captured["argv"] == ["scene", "run"]
    assert captured["app"] is sentinel_app
    assert captured["config"] is sentinel_config


def test_build_cli_dispatch_config_loads_env_then_reads_default(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(cli_main, "load_env_from_dotenv", lambda: calls.append("load"))
    monkeypatch.setattr(
        cli_main,
        "get_default_carla_exe",
        lambda: "C:/CARLA/FromDotenv.exe",
    )

    config = cli_main.build_cli_dispatch_config()

    assert calls == ["load"]
    assert config.default_carla_exe == "C:/CARLA/FromDotenv.exe"


def test_build_parser_uses_passed_carla_exe_default() -> None:
    parser = build_parser(default_carla_exe="C:/CARLA/FromApp.exe")

    args = parser.parse_args(["scene", "run"])

    assert args.carla_exe == "C:/CARLA/FromApp.exe"


def test_build_parser_supports_scene_run_episode_options() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "scene",
            "run",
            "--scene-import",
            "datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
            "--export-episode-spec",
        ]
    )

    assert (
        args.scene_import
        == "datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json"
    )
    assert args.export_episode_spec is True


def test_build_parser_supports_scene_run_manual_defaults() -> None:
    parser = build_parser()

    args = parser.parse_args(["scene", "run"])

    assert args.manual_control_target is None
    assert args.enable_tick_log is False
    assert args.tick_log_path is None


def test_build_parser_supports_operator_run_defaults() -> None:
    parser = build_parser()

    args = parser.parse_args(["operator", "run"])

    assert args.follow == "role:ego"
    assert args.strategy == "parallel"
    assert args.spawn_if_missing is True
    assert args.steps == 80
    assert args.target_speed_mps == 5.0
    assert args.operator_warmup_ticks == 1


def test_build_parser_supports_exp_run_defaults() -> None:
    parser = build_parser()

    args = parser.parse_args(
        ["exp", "run", "--episode-spec", "datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json"]
    )

    assert (
        args.episode_spec
        == "datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json"
    )
    assert args.control_target == "role:ego"
    assert args.forward_distance_m == 20.0
    assert args.target_speed_mps == 5.0
    assert args.max_steps == 800


def test_build_parser_supports_tracking_run_defaults() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "tracking",
            "run",
            "--episode-spec",
            "datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
        ]
    )

    assert (
        args.episode_spec
        == "datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json"
    )
    assert args.control_target == "role:ego"
    assert args.target_speed_mps == 5.0
    assert args.max_steps is None
    assert args.route_step_m == 2.0
    assert args.bind_spectator is False
    assert args.spectator_z == 20.0
    assert args.enable_trajectory_log is False
    assert args.trajectory_log_path is None
    assert args.target_tick_log_path is None


def test_build_parser_supports_tracking_run_target_tick_log_path() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "tracking",
            "run",
            "--episode-spec",
            "datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
            "--target-tick-log-path",
            "runs/custom/scene_tick_log.json",
        ]
    )

    assert args.target_tick_log_path == "runs/custom/scene_tick_log.json"


def test_dispatch_vehicle_list_outputs_json(capsys) -> None:
    app = _FakeApp()
    parser = build_parser()
    args = parser.parse_args(["vehicle", "list", "--format", "json"])

    exit_code = dispatch_args(args, app=app, parser=parser)
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert payload[0]["actor_id"] == 7
    assert app.vehicle_list_calls


def test_dispatch_vehicle_spawn_outputs_json(capsys) -> None:
    app = _FakeApp()
    parser = build_parser()
    args = parser.parse_args(["vehicle", "spawn", "--output", "json"])

    exit_code = dispatch_args(args, app=app, parser=parser)
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert payload["actor_id"] == 99
    assert app.vehicle_spawn_calls


def test_dispatch_exp_prints_metrics_path(capsys) -> None:
    app = _FakeApp()
    parser = build_parser()
    args = parser.parse_args(
        [
            "exp",
            "run",
            "--episode-spec",
            "datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
        ]
    )

    exit_code = dispatch_args(args, app=app, parser=parser)
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert "metrics saved path=runs/20260228_161718/results/ep_000001/metrics.json" in stdout


def test_dispatch_tracking_prints_summary(capsys) -> None:
    app = _FakeApp()
    parser = build_parser()
    args = parser.parse_args(
        [
            "tracking",
            "run",
            "--episode-spec",
            "datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
        ]
    )

    exit_code = dispatch_args(args, app=app, parser=parser)
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert "tracking workflow finished" in stdout
    assert "termination_reason=goal_reached" in stdout
    assert (
        "metrics saved path=runs/20260228_161718/results/ep_000001/tracking_metrics.json"
        in stdout
    )
    assert app.tracking_calls


def test_dispatch_operator_rejects_invalid_follow_ref(capsys) -> None:
    app = _FakeApp()
    parser = build_parser()
    args = parser.parse_args(["operator", "run", "--follow", "bad-ref"])

    exit_code = dispatch_args(args, app=app, parser=parser)
    stderr = capsys.readouterr().err

    assert exit_code == 2
    assert "Invalid vehicle ref" in stderr
    assert not app.operator_calls


def test_dispatch_spectator_rejects_invalid_follow_ref(capsys) -> None:
    app = _FakeApp()
    parser = build_parser()
    args = parser.parse_args(["spectator", "follow", "--follow", "bad-ref"])

    exit_code = dispatch_args(args, app=app, parser=parser)
    stderr = capsys.readouterr().err

    assert exit_code == 2
    assert "Invalid vehicle ref" in stderr
    assert not app.spectator_calls


def test_dispatch_scene_rejects_invalid_manual_control_target(capsys) -> None:
    app = _FakeApp()
    parser = build_parser()
    args = parser.parse_args(["scene", "run", "--manual-control-target", "bad-ref"])

    exit_code = dispatch_args(args, app=app, parser=parser)
    stderr = capsys.readouterr().err

    assert exit_code == 2
    assert "Invalid vehicle ref" in stderr
    assert not app.scene_calls


def test_dispatch_scene_enable_tick_log_without_target_maps_usage_error(capsys) -> None:
    app = _FakeApp()
    parser = build_parser()
    args = parser.parse_args(["scene", "run", "--enable-tick-log"])

    def _raise_usage(_request: Any) -> None:
        raise CliUsageError("enable_tick_log requires manual_control_target")

    app.run_scene = _raise_usage
    exit_code = dispatch_args(args, app=app, parser=parser)
    stderr = capsys.readouterr().err

    assert exit_code == 2
    assert "manual_control_target" in stderr


def test_dispatch_maps_usage_error_to_exit_code_2(capsys) -> None:
    app = _FakeApp()
    parser = build_parser()
    args = parser.parse_args(["scene", "run"])

    def _raise_usage(_request: Any) -> None:
        raise CliUsageError("bad usage")

    app.run_scene = _raise_usage

    exit_code = dispatch_args(args, app=app, parser=parser)
    stderr = capsys.readouterr().err

    assert exit_code == 2
    assert "[ERROR] bad usage" in stderr


def test_dispatch_maps_runtime_error_to_exit_code_1(capsys) -> None:
    app = _FakeApp()
    parser = build_parser()
    args = parser.parse_args(["scene", "run"])

    def _raise_runtime(_request: Any) -> None:
        raise CliRuntimeError("runtime broke")

    app.run_scene = _raise_runtime

    exit_code = dispatch_args(args, app=app, parser=parser)
    stderr = capsys.readouterr().err

    assert exit_code == 1
    assert "[ERROR] runtime broke" in stderr

