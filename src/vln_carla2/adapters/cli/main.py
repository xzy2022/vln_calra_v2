"""CLI entry point for slice-0 closed-loop control."""

import argparse
import sys
from typing import Sequence

from vln_carla2.app.bootstrap import run
from vln_carla2.app.settings import Settings, SpawnPoint


def build_parser() -> argparse.ArgumentParser:
    defaults = Settings()
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    settings = Settings(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout_seconds,
        map_name=args.map_name,
        fixed_delta_seconds=args.fixed_delta_seconds,
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

    print(
        "[INFO] loop finished "
        f"steps={result.steps} last_frame={result.last_frame} "
        f"last_speed_mps={result.last_speed_mps:.3f} avg_speed_mps={result.avg_speed_mps:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

