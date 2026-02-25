"""CLI entry point for stage-1 scene editor baseline."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Sequence

from vln_carla2.app.scene_editor_main import SceneEditorSettings, run as run_scene_editor
from vln_carla2.infrastructure.carla.server_launcher import (
    is_carla_server_reachable,
    is_loopback_host,
    launch_carla_server,
    terminate_carla_server,
    wait_for_carla_server,
)


def build_parser() -> argparse.ArgumentParser:
    _load_env_from_dotenv()
    defaults = SceneEditorSettings()
    default_carla_exe = os.getenv("CARLA_UE4_EXE")

    parser = argparse.ArgumentParser(description="Run stage-1 CARLA runtime baseline.")
    parser.add_argument("--host", default=defaults.host, help="CARLA host")
    parser.add_argument("--port", type=int, default=defaults.port, help="CARLA RPC port")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=defaults.timeout_seconds,
        help="CARLA client timeout in seconds",
    )
    parser.add_argument("--map-name", default=defaults.map_name, help="CARLA map name")
    parser.add_argument(
        "--mode",
        choices=("sync", "async"),
        default="sync",
        help="Runtime mode: sync uses world.tick, async uses world.wait_for_tick",
    )
    parser.add_argument(
        "--fixed-delta-seconds",
        type=float,
        default=defaults.fixed_delta_seconds,
        help="Fixed delta time used in sync mode（每次 world.tick() 前进多少“模拟时间”）",
    )
    parser.add_argument(
        "--tick-sleep-seconds",
        type=float,
        default=defaults.tick_sleep_seconds,
        help="Sleep duration between ticks (sync mode only)（每次 tick 后 time.sleep(...) 多久）",
    )
    parser.add_argument(
        "--render-mode",
        choices=("normal", "no-rendering"),
        default="normal",
        help="World setting for rendering computation",
    )
    parser.add_argument(
        "--window-mode",
        choices=("onscreen", "offscreen"),
        default=None,
        help="Window mode for launched CARLA server",
    )
    parser.add_argument(
        "--launch-carla",
        action="store_true",
        help="Launch local CarlaUE4 before running",
    )
    parser.add_argument(
        "--reuse-existing-carla",
        action="store_true",
        help="Reuse running CARLA on host:port instead of failing",
    )
    parser.add_argument(
        "--carla-exe",
        default=default_carla_exe,
        help="Path to CarlaUE4 executable (or set CARLA_UE4_EXE in .env)",
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

    no_rendering_mode = args.render_mode == "no-rendering"
    offscreen_mode = args.window_mode == "offscreen"
    synchronous_mode = args.mode == "sync"

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
            print(f"[INFO] reusing existing CARLA on {args.host}:{args.port}")
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

    settings = SceneEditorSettings(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout_seconds,
        map_name=args.map_name,
        synchronous_mode=synchronous_mode,
        fixed_delta_seconds=args.fixed_delta_seconds,
        no_rendering_mode=no_rendering_mode,
        tick_sleep_seconds=args.tick_sleep_seconds,
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
