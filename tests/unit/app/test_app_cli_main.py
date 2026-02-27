import json
from dataclasses import dataclass, field
from typing import Any

from vln_carla2.adapters.cli.dispatch import dispatch_args
from vln_carla2.adapters.cli.parser import build_parser
from vln_carla2.app import cli_main
from vln_carla2.usecases.operator.ports.vehicle_dto import VehicleDescriptor


@dataclass
class _FakeApp:
    default_carla_exe: str | None = "C:/CARLA/CarlaUE4.exe"
    load_calls: int = 0
    scene_calls: list[Any] = field(default_factory=list)
    operator_calls: list[Any] = field(default_factory=list)
    exp_calls: list[Any] = field(default_factory=list)
    spectator_calls: list[Any] = field(default_factory=list)
    vehicle_list_calls: list[Any] = field(default_factory=list)
    vehicle_spawn_calls: list[Any] = field(default_factory=list)

    def load_env_from_dotenv(self, path: str = ".env") -> None:
        del path
        self.load_calls += 1

    def get_default_carla_exe(self) -> str | None:
        return self.default_carla_exe

    def run_scene(self, command: Any) -> int:
        self.scene_calls.append(command)
        return 0

    def run_operator(self, command: Any) -> int:
        self.operator_calls.append(command)
        return 0

    def run_exp(self, command: Any) -> int:
        self.exp_calls.append(command)
        return 0

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

    def run_spectator_follow(self, command: Any) -> int:
        self.spectator_calls.append(command)
        return 0


def test_main_delegates_to_adapter(monkeypatch) -> None:
    sentinel_app = object()
    captured: dict[str, Any] = {}

    monkeypatch.setattr(cli_main, "build_cli_application", lambda: sentinel_app)

    def fake_run_cli(argv, app):
        captured["argv"] = argv
        captured["app"] = app
        return 7

    monkeypatch.setattr(cli_main, "run_cli", fake_run_cli)

    exit_code = cli_main.main(["scene", "run"])

    assert exit_code == 7
    assert captured["argv"] == ["scene", "run"]
    assert captured["app"] is sentinel_app


def test_build_parser_uses_carla_exe_from_app_default() -> None:
    app = _FakeApp(default_carla_exe="C:/CARLA/FromApp.exe")
    parser = build_parser(app)

    args = parser.parse_args(["scene", "run"])

    assert app.load_calls == 1
    assert args.carla_exe == "C:/CARLA/FromApp.exe"


def test_build_parser_supports_operator_run_defaults() -> None:
    app = _FakeApp()
    parser = build_parser(app)

    args = parser.parse_args(["operator", "run"])

    assert args.follow == "role:ego"
    assert args.strategy == "parallel"
    assert args.spawn_if_missing is True
    assert args.steps == 80
    assert args.target_speed_mps == 5.0
    assert args.operator_warmup_ticks == 1


def test_build_parser_supports_exp_run_defaults() -> None:
    app = _FakeApp()
    parser = build_parser(app)

    args = parser.parse_args(["exp", "run", "--scene-json", "artifacts/scene_out.json"])

    assert args.scene_json == "artifacts/scene_out.json"
    assert args.control_target == "role:ego"
    assert args.forward_distance_m == 20.0
    assert args.target_speed_mps == 5.0
    assert args.max_steps == 800


def test_dispatch_vehicle_list_outputs_json(capsys) -> None:
    app = _FakeApp()
    parser = build_parser(app)
    args = parser.parse_args(["vehicle", "list", "--format", "json"])

    exit_code = dispatch_args(args, app=app, parser=parser)
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert payload[0]["actor_id"] == 7
    assert app.vehicle_list_calls


def test_dispatch_vehicle_spawn_outputs_json(capsys) -> None:
    app = _FakeApp()
    parser = build_parser(app)
    args = parser.parse_args(["vehicle", "spawn", "--output", "json"])

    exit_code = dispatch_args(args, app=app, parser=parser)
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert payload["actor_id"] == 99
    assert app.vehicle_spawn_calls


def test_dispatch_operator_rejects_invalid_follow_ref(capsys) -> None:
    app = _FakeApp()
    parser = build_parser(app)
    args = parser.parse_args(["operator", "run", "--follow", "bad-ref"])

    exit_code = dispatch_args(args, app=app, parser=parser)
    stderr = capsys.readouterr().err

    assert exit_code == 2
    assert "Invalid vehicle ref" in stderr
    assert not app.operator_calls


def test_dispatch_spectator_rejects_invalid_follow_ref(capsys) -> None:
    app = _FakeApp()
    parser = build_parser(app)
    args = parser.parse_args(["spectator", "follow", "--follow", "bad-ref"])

    exit_code = dispatch_args(args, app=app, parser=parser)
    stderr = capsys.readouterr().err

    assert exit_code == 2
    assert "Invalid vehicle ref" in stderr
    assert not app.spectator_calls

