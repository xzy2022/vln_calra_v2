"""CLI entry point for slice-0 closed-loop control."""

import argparse
import os
import subprocess
import sys
from typing import Sequence

from vln_carla2.app.bootstrap import run
from vln_carla2.app.settings import Settings, SpawnPoint
from vln_carla2.infrastructure.carla.server_launcher import (
    is_carla_server_reachable,
    is_loopback_host,
    launch_carla_server,
    terminate_carla_server,
    wait_for_carla_server,
)


def build_parser() -> argparse.ArgumentParser:
    defaults = Settings()
    default_carla_exe = os.getenv("CARLA_UE4_EXE")
    parser = argparse.ArgumentParser(description="Run minimal CARLA control loop.")
    parser.add_argument("--host", default=defaults.host, help="CARLA host")
    parser.add_argument("--port", type=int, default=defaults.port, help="CARLA port")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=defaults.timeout_seconds,
        help="CARLA client timeout in seconds",
    )
    parser.add_argument("--map-name", default=defaults.map_name, help="CARLA map name")
    parser.add_argument(
        "--fixed-delta-seconds",
        type=float,
        default=defaults.fixed_delta_seconds,
        help="Synchronous simulation step time",
    )
    parser.add_argument(
        "--render-mode",
        choices=("normal", "no-rendering"),
        default=defaults.render_mode,
        help=(
            "Render computation mode for the run: normal (default), "
            "no-rendering."
        ),
    )
    parser.add_argument(
        "--window-mode",
        choices=("onscreen", "offscreen"),
        default=None,
        help=(
            "Window mode for launched CARLA server: onscreen (default), "
            "offscreen"
        ),
    )
    parser.add_argument(
        "--steps", type=int, default=defaults.steps, help="Control loop iterations"
    )
    parser.add_argument(
        "--target-speed-mps",
        type=float,
        default=defaults.target_speed_mps,
        help="Target speed in m/s",
    )
    parser.add_argument(
        "--vehicle-blueprint",
        default=defaults.vehicle_blueprint,
        help="Blueprint filter, e.g. vehicle.tesla.model3",
    )
    parser.add_argument("--spawn-x", type=float, default=defaults.spawn.x, help="Spawn x")
    parser.add_argument("--spawn-y", type=float, default=defaults.spawn.y, help="Spawn y")
    parser.add_argument("--spawn-z", type=float, default=defaults.spawn.z, help="Spawn z")
    parser.add_argument(
        "--spawn-yaw", type=float, default=defaults.spawn.yaw, help="Spawn yaw"
    )
    parser.add_argument(
        "--launch-carla",
        action="store_true",
        help="Launch local CarlaUE4 before running the control loop",
    )
    parser.add_argument(
        "--reuse-existing-carla",
        action="store_true",
        help="Reuse running CARLA on host:port instead of failing when --launch-carla is set",
    )
    parser.add_argument(
        "--carla-exe",
        default=default_carla_exe,
        help="Path to CarlaUE4 executable (or env CARLA_UE4_EXE)",
    )
    parser.add_argument(
        "--carla-startup-timeout-seconds",
        type=float,
        default=45.0,
        help="Maximum time to wait for a launched CARLA server",
    )
    parser.add_argument(
        "--quality-level",
        choices=("Low", "Epic"),
        default=None,
        help="Rendering quality for launched CARLA server",
    )
    parser.add_argument(
        "--with-sound",
        action="store_true",
        help="Enable server audio (default launches with -nosound)",
    )
    parser.add_argument(
        "--keep-carla-server",
        action="store_true",
        help="Do not terminate launched CARLA process on exit",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    launched_process: subprocess.Popen[bytes] | None = None
    render_mode = args.render_mode
    no_rendering_mode = render_mode == "no-rendering"
    offscreen_mode = args.window_mode == "offscreen"

    if offscreen_mode and not args.launch_carla:
        print(
            "[WARN] window-mode=offscreen only affects launched CARLA server "
            "(enable --launch-carla)."
        )
    if no_rendering_mode and not args.launch_carla:
        print(
            "[WARN] render-mode=no-rendering applies world settings, but window "
            "visibility depends on existing CARLA server startup flags."
        )

    if args.launch_carla:
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
            print(
                f"[INFO] reusing existing CARLA on {args.host}:{args.port}"
            )
        else:
            if not args.carla_exe:
                print(
                    "[ERROR] --carla-exe is required when --launch-carla is set "
                    "(or set CARLA_UE4_EXE)",
                    file=sys.stderr,
                )
                return 2
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
            except Exception as exc:
                if launched_process is not None:
                    try:
                        terminate_carla_server(launched_process)
                    except Exception:
                        pass
                print(f"[ERROR] failed to launch CARLA server: {exc}", file=sys.stderr)
                return 1

    settings = Settings(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout_seconds,
        map_name=args.map_name,
        fixed_delta_seconds=args.fixed_delta_seconds,
        render_mode=render_mode,
        steps=args.steps,
        target_speed_mps=args.target_speed_mps,
        vehicle_blueprint=args.vehicle_blueprint,
        spawn=SpawnPoint(x=args.spawn_x, y=args.spawn_y, z=args.spawn_z, yaw=args.spawn_yaw),
    )

    try:
        result = run(settings)
    except Exception as exc:
        print(f"[ERROR] control loop failed: {exc}", file=sys.stderr)
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

    print(
        "[INFO] loop finished "
        f"steps={result.executed_steps} last_frame={result.last_frame} "
        f"last_speed_mps={result.last_speed_mps:.3f} avg_speed_mps={result.avg_speed_mps:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
