"""Argparse CLI definition for vln_carla2."""

from __future__ import annotations

import argparse

from .commands import (
    DEFAULT_FIXED_DELTA_SECONDS,
    DEFAULT_HOST,
    DEFAULT_MAP_NAME,
    DEFAULT_PORT,
    DEFAULT_TICK_SLEEP_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
)

SCENE_COMMAND = "scene"
OPERATOR_COMMAND = "operator"
EXP_COMMAND = "exp"
TRACKING_COMMAND = "tracking"
VEHICLE_COMMAND = "vehicle"
SPECTATOR_COMMAND = "spectator"


def build_parser(*, default_carla_exe: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CARLA operator CLI.")
    root_subparsers = parser.add_subparsers(dest="resource", required=True)

    scene_parser = root_subparsers.add_parser(SCENE_COMMAND, help="Scene operations.")
    scene_subparsers = scene_parser.add_subparsers(dest="scene_action", required=True)
    scene_run = scene_subparsers.add_parser("run", help="Run scene editor runtime.")
    _add_scene_runtime_arguments(
        scene_run,
        default_carla_exe=default_carla_exe,
    )
    scene_run.add_argument(
        "--scene-import",
        help="Path to one episode_spec.json file loaded before loop starts.",
    )
    scene_run.add_argument(
        "--scene-export-path",
        help=(
            "Optional export path used by Ctrl+S scene export hotkey. "
            "When omitted, writes scene_export_<time>.json in current directory."
        ),
    )
    scene_run.add_argument(
        "--export-episode-spec",
        action="store_true",
        help="Also export episode_spec.json when Ctrl+S scene export is triggered.",
    )
    scene_run.add_argument(
        "--manual-control-target",
        help=(
            "Manual control target vehicle reference: actor:<id>, role:<name>, "
            "first, or positive integer id."
        ),
    )
    scene_run.add_argument(
        "--enable-tick-log",
        action="store_true",
        help="Save per-tick state/control JSON log for manual control target vehicle.",
    )
    scene_run.add_argument(
        "--tick-log-path",
        help=(
            "Optional output path for scene tick log JSON. "
            "When omitted, writes runs/<time>/scene/scene_tick_log.json."
        ),
    )
    scene_run.set_defaults(command_id="scene_run")

    operator_parser = root_subparsers.add_parser(
        OPERATOR_COMMAND,
        help="Operator workflow operations.",
    )
    operator_subparsers = operator_parser.add_subparsers(dest="operator_action", required=True)
    operator_run = operator_subparsers.add_parser(
        "run",
        help="Run full operator workflow (resolve/spawn -> follow -> control).",
    )
    _add_scene_runtime_arguments(
        operator_run,
        default_carla_exe=default_carla_exe,
    )
    operator_run.add_argument(
        "--follow",
        default="role:ego",
        help="Target vehicle reference: actor:<id>, role:<name>, first, or positive integer id.",
    )
    operator_run.add_argument(
        "--z",
        type=float,
        default=20.0,
        help="Spectator altitude for top-down follow.",
    )
    _add_vehicle_spawn_arguments(operator_run)
    operator_run.add_argument(
        "--spawn-if-missing",
        dest="spawn_if_missing",
        action="store_true",
        default=True,
        help="Spawn vehicle from spawn arguments when follow reference is not resolved.",
    )
    operator_run.add_argument(
        "--no-spawn-if-missing",
        dest="spawn_if_missing",
        action="store_false",
        help="Fail when follow reference cannot be resolved.",
    )
    operator_run.add_argument(
        "--strategy",
        choices=("serial", "parallel"),
        default="parallel",
        help="Execution strategy: serial (operator warmup -> control) or parallel (step interleave).",
    )
    operator_run.add_argument(
        "--steps",
        type=int,
        default=80,
        help="Control loop steps.",
    )
    operator_run.add_argument(
        "--target-speed-mps",
        type=float,
        default=5.0,
        help="Control target speed in m/s.",
    )
    operator_run.add_argument(
        "--operator-warmup-ticks",
        type=int,
        default=1,
        help="Warmup ticks in serial strategy before control starts.",
    )
    operator_run.set_defaults(command_id="operator_run")

    exp_parser = root_subparsers.add_parser(
        EXP_COMMAND,
        help="Experiment workflow operations.",
    )
    exp_subparsers = exp_parser.add_subparsers(dest="exp_action", required=True)
    exp_run = exp_subparsers.add_parser(
        "run",
        help="Run exp workflow (scene import -> follow -> forward demo -> zone check).",
    )
    _add_scene_runtime_arguments(
        exp_run,
        default_carla_exe=default_carla_exe,
    )
    exp_run.add_argument(
        "--episode-spec",
        required=True,
        help="Path to episode_spec.json used to resolve scene import/map/start/goal metadata.",
    )
    exp_run.add_argument(
        "--control-target",
        default="role:ego",
        help="Control target reference: actor:<id>, role:<name>, first, or positive integer id.",
    )
    exp_run.add_argument(
        "--forward-distance-m",
        type=float,
        default=20.0,
        help="Forward demo distance in meters.",
    )
    exp_run.add_argument(
        "--target-speed-mps",
        type=float,
        default=5.0,
        help="Control target speed in m/s.",
    )
    exp_run.add_argument(
        "--max-steps",
        type=int,
        default=800,
        help="Max control steps used as fail-safe stop.",
    )
    exp_run.set_defaults(command_id="exp_run")

    tracking_parser = root_subparsers.add_parser(
        TRACKING_COMMAND,
        help="Tracking workflow operations.",
    )
    tracking_subparsers = tracking_parser.add_subparsers(dest="tracking_action", required=True)
    tracking_run = tracking_subparsers.add_parser(
        "run",
        help="Run pure-pursuit + longitudinal PID tracking workflow.",
    )
    _add_scene_runtime_arguments(
        tracking_run,
        default_carla_exe=default_carla_exe,
    )
    tracking_run.add_argument(
        "--episode-spec",
        required=True,
        help="Path to episode_spec.json used to resolve scene import/map/start/goal metadata.",
    )
    tracking_run.add_argument(
        "--control-target",
        default="role:ego",
        help="Control target reference: actor:<id>, role:<name>, first, or positive integer id.",
    )
    tracking_run.add_argument(
        "--target-speed-mps",
        type=float,
        default=5.0,
        help="Cruise target speed in m/s.",
    )
    tracking_run.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Optional max control steps override (defaults to episode_spec.max_steps).",
    )
    tracking_run.add_argument("--route-step-m", type=float, default=2.0)
    tracking_run.add_argument("--route-max-points", type=int, default=2000)
    tracking_run.add_argument("--lookahead-base-m", type=float, default=3.0)
    tracking_run.add_argument("--lookahead-speed-gain", type=float, default=0.35)
    tracking_run.add_argument("--lookahead-min-m", type=float, default=2.5)
    tracking_run.add_argument("--lookahead-max-m", type=float, default=12.0)
    tracking_run.add_argument("--wheelbase-m", type=float, default=2.85)
    tracking_run.add_argument("--max-steer-angle-deg", type=float, default=70.0)
    tracking_run.add_argument("--pid-kp", type=float, default=1.0)
    tracking_run.add_argument("--pid-ki", type=float, default=0.05)
    tracking_run.add_argument("--pid-kd", type=float, default=0.0)
    tracking_run.add_argument("--max-throttle", type=float, default=0.75)
    tracking_run.add_argument("--max-brake", type=float, default=0.30)
    tracking_run.add_argument("--goal-distance-tolerance-m", type=float, default=1.5)
    tracking_run.add_argument("--goal-yaw-tolerance-deg", type=float, default=15.0)
    tracking_run.add_argument("--slowdown-distance-m", type=float, default=12.0)
    tracking_run.add_argument("--min-slow-speed-mps", type=float, default=0.8)
    tracking_run.add_argument("--steer-rate-limit-per-step", type=float, default=0.10)
    tracking_run.add_argument(
        "--bind-spectator",
        action="store_true",
        help="Continuously bind spectator to tracked vehicle in top-down view.",
    )
    tracking_run.add_argument(
        "--spectator-z",
        type=float,
        default=20.0,
        help="Top-down spectator altitude when --bind-spectator is enabled.",
    )
    tracking_run.add_argument(
        "--enable-trajectory-log",
        action="store_true",
        help="Save structured tracking trajectory evaluation log as JSON.",
    )
    tracking_run.add_argument(
        "--trajectory-log-path",
        help=(
            "Optional output path for tracking trajectory metrics JSON. "
            "When omitted, writes runs/<time>/results/<episode>/tracking_metrics.json."
        ),
    )
    tracking_run.add_argument(
        "--target-tick-log-path",
        help=(
            "Optional input path for scene tick log JSON. "
            "When set, tracking follows tick_traces from this file as target trajectory."
        ),
    )
    tracking_run.set_defaults(command_id="tracking_run")

    vehicle_parser = root_subparsers.add_parser(VEHICLE_COMMAND, help="Vehicle operations.")
    vehicle_subparsers = vehicle_parser.add_subparsers(dest="vehicle_action", required=True)

    vehicle_list = vehicle_subparsers.add_parser("list", help="List current vehicle actors.")
    _add_world_session_arguments(vehicle_list)
    vehicle_list.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Output format.",
    )
    vehicle_list.set_defaults(command_id="vehicle_list")

    vehicle_spawn = vehicle_subparsers.add_parser("spawn", help="Spawn one vehicle actor.")
    _add_world_session_arguments(vehicle_spawn)
    _add_vehicle_spawn_arguments(vehicle_spawn)
    vehicle_spawn.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format.",
    )
    vehicle_spawn.set_defaults(command_id="vehicle_spawn")

    spectator_parser = root_subparsers.add_parser(
        SPECTATOR_COMMAND,
        help="Spectator operations.",
    )
    spectator_subparsers = spectator_parser.add_subparsers(dest="spectator_action", required=True)
    spectator_follow = spectator_subparsers.add_parser(
        "follow",
        help="Continuously follow target vehicle in top-down spectator view.",
    )
    _add_world_session_arguments(spectator_follow)
    spectator_follow.add_argument(
        "--follow",
        required=True,
        help="Follow reference: actor:<id>, role:<name>, or first.",
    )
    spectator_follow.add_argument(
        "--z",
        type=float,
        default=20.0,
        help="Spectator altitude for top-down follow.",
    )
    spectator_follow.set_defaults(command_id="spectator_follow")

    return parser


def _add_world_session_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default=DEFAULT_HOST, help="CARLA host.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="CARLA RPC port.")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="CARLA client timeout in seconds.",
    )
    parser.add_argument("--map-name", default=DEFAULT_MAP_NAME, help="CARLA map name.")
    parser.add_argument(
        "--mode",
        choices=("sync", "async"),
        default="sync",
        help="Runtime mode: sync uses world.tick, async uses world.wait_for_tick.",
    )
    parser.add_argument(
        "--fixed-delta-seconds",
        type=float,
        default=DEFAULT_FIXED_DELTA_SECONDS,
        help="Fixed delta used for sync mode world settings.",
    )
    parser.add_argument(
        "--no-rendering",
        action="store_true",
        help="Disable world rendering in CARLA world settings.",
    )


def _add_vehicle_spawn_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--blueprint-filter",
        default="vehicle.tesla.model3",
        help="CARLA vehicle blueprint filter.",
    )
    parser.add_argument("--spawn-x", type=float, default=0.038, help="Spawn location X.")
    parser.add_argument("--spawn-y", type=float, default=15.320, help="Spawn location Y.")
    parser.add_argument("--spawn-z", type=float, default=0.15, help="Spawn location Z.")
    parser.add_argument("--spawn-yaw", type=float, default=180.0, help="Spawn yaw.")
    parser.add_argument("--role-name", default="ego", help="role_name actor attribute.")


def _add_scene_runtime_arguments(
    parser: argparse.ArgumentParser,
    *,
    default_carla_exe: str | None,
) -> None:
    _add_world_session_arguments(parser)
    parser.add_argument(
        "--tick-sleep-seconds",
        type=float,
        default=DEFAULT_TICK_SLEEP_SECONDS,
        help="Sleep duration between ticks (sync mode only).",
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
