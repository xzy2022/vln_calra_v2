"""CLI entry point for scene / vehicle / spectator operations."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Any, Callable, Sequence, TypeVar

from vln_carla2.adapters.cli.presenter import print_vehicle, print_vehicle_list
from vln_carla2.adapters.cli.vehicle_ref_parser import VehicleRefParseError, parse_vehicle_ref
from vln_carla2.app.carla_session import CarlaSessionConfig, managed_carla_session
from vln_carla2.app.operator_container import OperatorContainer, build_operator_container
from vln_carla2.app.scene_editor_main import SceneEditorSettings, run as run_scene_editor
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.infrastructure.carla.server_launcher import (
    is_carla_server_reachable,
    is_loopback_host,
    launch_carla_server,
    terminate_carla_server,
    wait_for_carla_server,
)
from vln_carla2.infrastructure.carla.world_adapter import CarlaWorldAdapter
from vln_carla2.usecases.operator.follow_vehicle_topdown import FollowVehicleTopDown
from vln_carla2.usecases.operator.models import SpawnVehicleRequest, VehicleDescriptor


SCENE_COMMAND = "scene"
VEHICLE_COMMAND = "vehicle"
SPECTATOR_COMMAND = "spectator"
_ROOT_COMMANDS = {SCENE_COMMAND, VEHICLE_COMMAND, SPECTATOR_COMMAND}
_LEGACY_DEPRECATED_WARNED = False

T = TypeVar("T")


class CliUsageError(ValueError):
    """Raised when CLI arguments are semantically invalid."""



def build_parser() -> argparse.ArgumentParser:
    _load_env_from_dotenv()
    defaults = SceneEditorSettings()
    default_carla_exe = os.getenv("CARLA_UE4_EXE")

    parser = argparse.ArgumentParser(description="CARLA operator CLI.")
    root_subparsers = parser.add_subparsers(dest="resource", required=True)

    scene_parser = root_subparsers.add_parser(SCENE_COMMAND, help="Scene operations.")
    scene_subparsers = scene_parser.add_subparsers(dest="scene_action", required=True)
    scene_run = scene_subparsers.add_parser("run", help="Run scene editor runtime.")
    _add_scene_runtime_arguments(
        scene_run,
        defaults=defaults,
        default_carla_exe=default_carla_exe,
    )
    scene_run.set_defaults(handler=_handle_scene_run)

    vehicle_parser = root_subparsers.add_parser(VEHICLE_COMMAND, help="Vehicle operations.")
    vehicle_subparsers = vehicle_parser.add_subparsers(dest="vehicle_action", required=True)

    vehicle_list = vehicle_subparsers.add_parser("list", help="List current vehicle actors.")
    _add_world_session_arguments(vehicle_list, defaults=defaults)
    vehicle_list.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Output format.",
    )
    vehicle_list.set_defaults(handler=_handle_vehicle_list)

    vehicle_spawn = vehicle_subparsers.add_parser("spawn", help="Spawn one vehicle actor.")
    _add_world_session_arguments(vehicle_spawn, defaults=defaults)
    vehicle_spawn.add_argument(
        "--blueprint-filter",
        default="vehicle.tesla.model3",
        help="CARLA vehicle blueprint filter.",
    )
    vehicle_spawn.add_argument("--spawn-x", type=float, default=0.038, help="Spawn location X.")
    vehicle_spawn.add_argument("--spawn-y", type=float, default=15.320, help="Spawn location Y.")
    vehicle_spawn.add_argument("--spawn-z", type=float, default=0.15, help="Spawn location Z.")
    vehicle_spawn.add_argument("--spawn-yaw", type=float, default=180.0, help="Spawn yaw.")
    vehicle_spawn.add_argument("--role-name", default="ego", help="role_name actor attribute.")
    vehicle_spawn.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format.",
    )
    vehicle_spawn.set_defaults(handler=_handle_vehicle_spawn)

    spectator_parser = root_subparsers.add_parser(
        SPECTATOR_COMMAND,
        help="Spectator operations.",
    )
    spectator_subparsers = spectator_parser.add_subparsers(dest="spectator_action", required=True)
    spectator_follow = spectator_subparsers.add_parser(
        "follow",
        help="Lock spectator to target vehicle top-down once.",
    )
    _add_world_session_arguments(spectator_follow, defaults=defaults)
    spectator_follow.add_argument(
        "--ref",
        required=True,
        help="Vehicle reference: actor:<id>, role:<name>, or first.",
    )
    spectator_follow.add_argument(
        "--z",
        type=float,
        default=20.0,
        help="Spectator altitude for top-down follow.",
    )
    spectator_follow.set_defaults(handler=_handle_spectator_follow)

    return parser



def build_legacy_parser() -> argparse.ArgumentParser:
    _load_env_from_dotenv()
    defaults = SceneEditorSettings()
    default_carla_exe = os.getenv("CARLA_UE4_EXE")

    parser = argparse.ArgumentParser(description="Run stage-1 CARLA runtime baseline.")
    _add_scene_runtime_arguments(
        parser,
        defaults=defaults,
        default_carla_exe=default_carla_exe,
    )
    return parser



def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    if _is_legacy_entry(raw_argv):
        _print_legacy_deprecation_once()
        parser = build_legacy_parser()
        args = parser.parse_args(raw_argv)
        return _handle_scene_run(args)

    parser = build_parser()
    args = parser.parse_args(raw_argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 2
    return int(handler(args))



def _handle_scene_run(args: argparse.Namespace) -> int:
    launched_process: subprocess.Popen[bytes] | None = None
    no_rendering_mode = args.no_rendering
    offscreen_mode = args.offscreen
    synchronous_mode = args.mode == "sync"

    if offscreen_mode and not args.launch_carla:
        print(
            "[WARN] --offscreen only affects launched CARLA server "
            "(enable --launch-carla)."
        )
    if no_rendering_mode and not args.launch_carla:
        print(
            "[WARN] --no-rendering applies world settings, but window "
            "visibility depends on existing CARLA server startup flags."
        )

    if args.launch_carla:
        launch_result = _maybe_launch_carla(
            args,
            offscreen_mode=offscreen_mode,
            no_rendering_mode=no_rendering_mode,
        )
        if isinstance(launch_result, int):
            if launch_result != 0:
                return launch_result
        else:
            launched_process = launch_result

    try:
        follow_vehicle_id = _resolve_follow_vehicle_id(args)
    except CliUsageError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"[ERROR] failed to resolve follow ref: {exc}", file=sys.stderr)
        return 1

    settings = SceneEditorSettings(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout_seconds,
        map_name=args.map_name,
        synchronous_mode=synchronous_mode,
        fixed_delta_seconds=args.fixed_delta_seconds,
        no_rendering_mode=no_rendering_mode,
        tick_sleep_seconds=args.tick_sleep_seconds,
        follow_vehicle_id=follow_vehicle_id,
    )

    try:
        run_scene_editor(settings)
    except KeyboardInterrupt:
        print("[INFO] interrupted by Ctrl+C")
    except Exception as exc:
        print(f"[ERROR] runtime failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if launched_process is not None and not args.keep_carla_server:
            try:
                terminate_carla_server(launched_process)
            except Exception as exc:
                print(
                    f"[WARN] failed to terminate launched CARLA process: {exc}",
                    file=sys.stderr,
                )

    print(f"[INFO] runtime stopped mode={args.mode} host={args.host} port={args.port}")
    return 0



def _handle_vehicle_list(args: argparse.Namespace) -> int:
    try:
        vehicles = _with_operator_container(
            args,
            operation=lambda container, _world: container.list_vehicles.run(),
        )
        print_vehicle_list(vehicles, output_format=args.format)
        return 0
    except Exception as exc:
        print(f"[ERROR] vehicle list failed: {exc}", file=sys.stderr)
        return 1



def _handle_vehicle_spawn(args: argparse.Namespace) -> int:
    request = SpawnVehicleRequest(
        blueprint_filter=args.blueprint_filter,
        spawn_x=args.spawn_x,
        spawn_y=args.spawn_y,
        spawn_z=args.spawn_z,
        spawn_yaw=args.spawn_yaw,
        role_name=args.role_name,
    )
    try:
        vehicle = _with_operator_container(
            args,
            operation=lambda container, _world: container.spawn_vehicle.run(request),
        )
        print_vehicle(vehicle, output_format=args.output)
        return 0
    except Exception as exc:
        print(f"[ERROR] vehicle spawn failed: {exc}", file=sys.stderr)
        return 1



def _handle_spectator_follow(args: argparse.Namespace) -> int:
    try:
        ref = parse_vehicle_ref(args.ref)
    except VehicleRefParseError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    try:
        outcome = _with_operator_container(
            args,
            operation=lambda container, world: _follow_spectator_once(
                container=container,
                world=world,
                raw_ref=args.ref,
                ref=ref,
                z=args.z,
            ),
        )
        print(f"[INFO] spectator aligned ref={args.ref} actor_id={outcome.actor_id} z={args.z}")
        return 0
    except CliUsageError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"[ERROR] spectator follow failed: {exc}", file=sys.stderr)
        return 1



def _follow_spectator_once(
    *,
    container: OperatorContainer,
    world: Any,
    raw_ref: str,
    ref: Any,
    z: float,
) -> VehicleDescriptor:
    descriptor = container.resolve_vehicle_ref.run(ref)
    if descriptor is None:
        raise CliUsageError(f"no vehicle matches ref '{raw_ref}'")

    world_adapter = CarlaWorldAdapter(world)
    follow = FollowVehicleTopDown(
        spectator_camera=world_adapter,
        vehicle_pose=world_adapter,
        vehicle_id=VehicleId(descriptor.actor_id),
        z=z,
    )
    if not follow.follow_once():
        raise CliUsageError(f"vehicle missing during follow: actor_id={descriptor.actor_id}")
    return descriptor



def _with_operator_container(
    args: argparse.Namespace,
    *,
    operation: Callable[[OperatorContainer, Any], T],
    sleep_seconds: float = 0.0,
) -> T:
    session_config = _build_session_config(args)
    with managed_carla_session(session_config) as session:
        container = build_operator_container(
            world=session.world,
            synchronous_mode=session_config.synchronous_mode,
            sleep_seconds=sleep_seconds,
        )
        return operation(container, session.world)



def _build_session_config(args: argparse.Namespace) -> CarlaSessionConfig:
    synchronous_mode = args.mode == "sync"
    no_rendering_mode = args.no_rendering
    return CarlaSessionConfig(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout_seconds,
        map_name=args.map_name,
        synchronous_mode=synchronous_mode,
        fixed_delta_seconds=args.fixed_delta_seconds,
        no_rendering_mode=no_rendering_mode,
    )



def _resolve_follow_vehicle_id(args: argparse.Namespace) -> int | None:
    follow_vehicle_id = getattr(args, "follow_vehicle_id", None)
    follow_ref_raw = getattr(args, "follow", None)
    if follow_ref_raw is None:
        return follow_vehicle_id
    if follow_vehicle_id is not None:
        raise CliUsageError("cannot combine --follow and --follow-vehicle-id")

    try:
        ref = parse_vehicle_ref(follow_ref_raw)
    except VehicleRefParseError as exc:
        raise CliUsageError(str(exc)) from exc

    if ref.scheme == "actor":
        return int(ref.value or "0")

    descriptor = _with_operator_container(
        args,
        operation=lambda container, _world: container.resolve_vehicle_ref.run(ref),
        sleep_seconds=getattr(args, "tick_sleep_seconds", 0.0),
    )
    if descriptor is None:
        raise CliUsageError(f"no vehicle matches follow ref '{follow_ref_raw}'")
    return descriptor.actor_id



def _maybe_launch_carla(
    args: argparse.Namespace,
    *,
    offscreen_mode: bool,
    no_rendering_mode: bool,
) -> subprocess.Popen[bytes] | int:
    if not is_loopback_host(args.host):
        print(
            f"[ERROR] --launch-carla only supports local host, got host={args.host}",
            file=sys.stderr,
        )
        return 2
    if is_carla_server_reachable(args.host, args.port):
        if not args.reuse_existing_carla:
            print(
                "[ERROR] CARLA already reachable on "
                f"{args.host}:{args.port}. "
                "Stop existing CARLA or add --reuse-existing-carla.",
                file=sys.stderr,
            )
            return 2
        print(f"[INFO] reusing existing CARLA on {args.host}:{args.port}")
        return 0

    if not args.carla_exe:
        print(
            "[ERROR] --carla-exe is required when --launch-carla is set "
            "(or set CARLA_UE4_EXE)",
            file=sys.stderr,
        )
        return 2

    launched_process: subprocess.Popen[bytes] | None = None
    try:
        launched_process = launch_carla_server(
            executable_path=args.carla_exe,
            rpc_port=args.port,
            offscreen=offscreen_mode,
            no_rendering=no_rendering_mode,
            no_sound=not args.with_sound,
            quality_level=args.quality_level,
        )
        print(
            f"[INFO] launched CARLA pid={launched_process.pid} "
            f"on {args.host}:{args.port}"
        )
        wait_for_carla_server(
            host=args.host,
            port=args.port,
            timeout_seconds=args.carla_startup_timeout_seconds,
            process=launched_process,
        )
        return launched_process
    except Exception as exc:
        if launched_process is not None:
            try:
                terminate_carla_server(launched_process)
            except Exception:
                pass
        print(f"[ERROR] failed to launch CARLA server: {exc}", file=sys.stderr)
        return 1



def _add_world_session_arguments(
    parser: argparse.ArgumentParser,
    *,
    defaults: SceneEditorSettings,
) -> None:
    parser.add_argument("--host", default=defaults.host, help="CARLA host.")
    parser.add_argument("--port", type=int, default=defaults.port, help="CARLA RPC port.")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=defaults.timeout_seconds,
        help="CARLA client timeout in seconds.",
    )
    parser.add_argument("--map-name", default=defaults.map_name, help="CARLA map name.")
    parser.add_argument(
        "--mode",
        choices=("sync", "async"),
        default="sync",
        help="Runtime mode: sync uses world.tick, async uses world.wait_for_tick.",
    )
    parser.add_argument(
        "--fixed-delta-seconds",
        type=float,
        default=defaults.fixed_delta_seconds,
        help="Fixed delta used for sync mode world settings.",
    )
    parser.add_argument(
        "--no-rendering",
        action="store_true",
        help="Disable world rendering in CARLA world settings.",
    )



def _add_scene_runtime_arguments(
    parser: argparse.ArgumentParser,
    *,
    defaults: SceneEditorSettings,
    default_carla_exe: str | None,
) -> None:
    _add_world_session_arguments(parser, defaults=defaults)
    parser.add_argument(
        "--tick-sleep-seconds",
        type=float,
        default=defaults.tick_sleep_seconds,
        help="Sleep duration between ticks (sync mode only).",
    )
    parser.add_argument(
        "--follow",
        default=None,
        help="Follow reference: actor:<id>, role:<name>, or first.",
    )
    parser.add_argument(
        "--follow-vehicle-id",
        type=int,
        default=defaults.follow_vehicle_id,
        help="Legacy follow target by actor id.",
    )
    parser.add_argument(
        "--offscreen",
        action="store_true",
        help="Enable offscreen window mode for launched CARLA server.",
    )
    parser.add_argument(
        "--launch-carla",
        action="store_true",
        help="Launch local CarlaUE4 before running.",
    )
    parser.add_argument(
        "--reuse-existing-carla",
        action="store_true",
        help="Reuse running CARLA on host:port instead of failing.",
    )
    parser.add_argument(
        "--carla-exe",
        default=default_carla_exe,
        help="Path to CarlaUE4 executable (or set CARLA_UE4_EXE in .env).",
    )
    parser.add_argument(
        "--carla-startup-timeout-seconds",
        type=float,
        default=45.0,
        help="Maximum time to wait for a launched CARLA server.",
    )
    parser.add_argument(
        "--quality-level",
        choices=("Low", "Epic"),
        default="Epic",
        help="Rendering quality for launched CARLA server.",
    )
    parser.add_argument(
        "--with-sound",
        action="store_true",
        help="Enable server audio (default launches with -nosound).",
    )
    parser.add_argument(
        "--keep-carla-server",
        action="store_true",
        help="Do not terminate launched CARLA process on exit.",
    )



def _is_legacy_entry(argv: Sequence[str]) -> bool:
    if not argv:
        return True
    first = argv[0]
    if first in {"-h", "--help"}:
        return False
    return first not in _ROOT_COMMANDS



def _print_legacy_deprecation_once() -> None:
    global _LEGACY_DEPRECATED_WARNED
    if _LEGACY_DEPRECATED_WARNED:
        return
    print(
        "[DEPRECATED] legacy root args are still supported. "
        "Please migrate to: scene run ..."
    )
    _LEGACY_DEPRECATED_WARNED = True



def _load_env_from_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return

    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                if not key or key in os.environ:
                    continue

                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]
                os.environ[key] = value
    except OSError:
        return


if __name__ == "__main__":
    raise SystemExit(main())

