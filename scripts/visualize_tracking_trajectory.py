"""Visualize trajectory from tracking_metrics.json or scene_tick_log.json."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np

try:
    import matplotlib.pyplot as plt
except ImportError as exc:  # pragma: no cover - runtime dependency check
    raise SystemExit(
        "matplotlib is required for visualization. Install it with: pip install matplotlib"
    ) from exc

_MAX_OCCUPIED_RENDER_POINTS = 30_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Visualize trajectory from tracking_metrics.json or scene_tick_log.json."
        )
    )
    parser.add_argument(
        "metrics_path",
        type=Path,
        help=(
            "Path to tracking_metrics.json or scene_tick_log.json "
            "(e.g. runs/.../tracking_metrics.json, runs/.../scene_tick_log.json)."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Output image path. Defaults to the metrics file directory with "
            "'_trajectory_compare.png' suffix."
        ),
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=160,
        help="Image DPI when saving the figure (default: 160).",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show an interactive window in addition to saving the image.",
    )
    return parser.parse_args()


def _extract_xy(
    records: Iterable[dict[str, object]], *, x_key: str, y_key: str
) -> np.ndarray:
    points: list[tuple[float, float]] = []
    for row in records:
        if not isinstance(row, dict):
            continue
        x_value = row.get(x_key)
        y_value = row.get(y_key)
        if x_value is None or y_value is None:
            continue
        points.append((float(x_value), float(y_value)))
    if not points:
        return np.empty((0, 2), dtype=float)
    return np.asarray(points, dtype=float)


def _extract_step_series(
    traces: list[dict[str, object]], *, key: str
) -> tuple[np.ndarray, np.ndarray]:
    steps: list[int] = []
    values: list[float] = []
    for idx, trace in enumerate(traces):
        if not isinstance(trace, dict):
            continue
        value = trace.get(key)
        if value is None:
            continue
        step = trace.get("step")
        if step is None:
            step = trace.get("frame", idx + 1)
        steps.append(int(step))
        values.append(float(value))
    if not steps:
        return np.empty((0,), dtype=int), np.empty((0,), dtype=float)
    return np.asarray(steps, dtype=int), np.asarray(values, dtype=float)


def _nearest_plan_distance(actual_xy: np.ndarray, plan_xy: np.ndarray) -> np.ndarray:
    if len(actual_xy) == 0 or len(plan_xy) == 0:
        return np.empty((0,), dtype=float)
    diff = actual_xy[:, None, :] - plan_xy[None, :, :]
    dist = np.linalg.norm(diff, axis=2)
    return dist.min(axis=1)


def _default_output_path(metrics_path: Path) -> Path:
    return metrics_path.with_name(f"{metrics_path.stem}_trajectory_compare.png")


def _extract_planning_map_layers(
    payload: dict[str, object],
) -> tuple[np.ndarray, int, list[tuple[float, float, float | None]]]:
    planning_map = payload.get("planning_map")
    if not isinstance(planning_map, dict):
        return np.empty((0, 2), dtype=float), 0, []
    occupied_xy, occupied_total = _extract_occupied_cell_xy(planning_map)
    obstacles = _extract_obstacle_markers(planning_map)
    return occupied_xy, occupied_total, obstacles


def _extract_occupied_cell_xy(
    planning_map: dict[str, object],
) -> tuple[np.ndarray, int]:
    occupied_cells = planning_map.get("occupied_cells")
    if not isinstance(occupied_cells, list):
        return np.empty((0, 2), dtype=float), 0

    resolution_m = planning_map.get("resolution_m")
    origin_x = planning_map.get("origin_x")
    origin_y = planning_map.get("origin_y")
    if resolution_m is None or origin_x is None or origin_y is None:
        return np.empty((0, 2), dtype=float), 0

    try:
        resolution = float(resolution_m)
        base_x = float(origin_x)
        base_y = float(origin_y)
    except (TypeError, ValueError):
        return np.empty((0, 2), dtype=float), 0
    if not math.isfinite(resolution) or resolution <= 0.0:
        return np.empty((0, 2), dtype=float), 0

    points: list[tuple[float, float]] = []
    for cell in occupied_cells:
        if not isinstance(cell, (list, tuple)) or len(cell) < 2:
            continue
        try:
            cell_x = int(cell[0])
            cell_y = int(cell[1])
        except (TypeError, ValueError):
            continue
        if cell_x < 0 or cell_y < 0:
            continue
        points.append(
            (
                base_x + (float(cell_x) + 0.5) * resolution,
                base_y + (float(cell_y) + 0.5) * resolution,
            )
        )

    total_count = len(points)
    if total_count == 0:
        return np.empty((0, 2), dtype=float), 0

    if total_count > _MAX_OCCUPIED_RENDER_POINTS:
        stride = int(math.ceil(total_count / float(_MAX_OCCUPIED_RENDER_POINTS)))
        points = points[::max(1, stride)]
    return np.asarray(points, dtype=float), total_count


def _extract_obstacle_markers(
    planning_map: dict[str, object],
) -> list[tuple[float, float, float | None]]:
    raw_obstacles = planning_map.get("obstacles")
    if not isinstance(raw_obstacles, list):
        return []

    obstacles: list[tuple[float, float, float | None]] = []
    for item in raw_obstacles:
        if not isinstance(item, dict):
            continue
        x_value = item.get("x")
        y_value = item.get("y")
        if x_value is None or y_value is None:
            continue
        try:
            x = float(x_value)
            y = float(y_value)
        except (TypeError, ValueError):
            continue
        radius_raw = item.get("radius_m")
        radius: float | None = None
        if radius_raw is not None:
            try:
                radius_val = float(radius_raw)
            except (TypeError, ValueError):
                radius_val = float("nan")
            if math.isfinite(radius_val) and radius_val > 0.0:
                radius = radius_val
        obstacles.append((x, y, radius))
    return obstacles


def main() -> None:
    args = parse_args()
    metrics_path = args.metrics_path
    if not metrics_path.exists():
        raise SystemExit(f"metrics file does not exist: {metrics_path}")

    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("invalid metrics payload: expected a JSON object")

    target_trajectory = payload.get("target_trajectory", [])
    tick_traces = payload.get("tick_traces", [])
    if not isinstance(target_trajectory, list) or not isinstance(tick_traces, list):
        raise SystemExit("invalid payload: expected list fields target_trajectory/tick_traces")

    planned_xy = _extract_xy(target_trajectory, x_key="x", y_key="y")
    actual_xy = _extract_xy(tick_traces, x_key="actual_x", y_key="actual_y")
    if len(actual_xy) == 0:
        # scene tick log format stores world position directly as x/y.
        actual_xy = _extract_xy(tick_traces, x_key="x", y_key="y")
    occupied_xy, occupied_total, obstacles = _extract_planning_map_layers(payload)
    if len(planned_xy) == 0 and len(actual_xy) == 0:
        raise SystemExit("no trajectory points found in the metrics file")

    nearest_dist = _nearest_plan_distance(actual_xy, planned_xy)
    step_idx = np.arange(1, len(nearest_dist) + 1, dtype=int)

    summary = payload.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    termination_reason = str(summary.get("termination_reason", "unknown"))
    final_dist = summary.get("final_distance_to_goal_m")
    map_name = str(payload.get("map_name", "unknown_map"))

    fig, (ax_xy, ax_metric) = plt.subplots(
        1, 2, figsize=(13, 6), gridspec_kw={"width_ratios": [2.2, 1.0]}
    )

    if len(occupied_xy) > 0:
        occupied_label = f"Occupied Cells ({len(occupied_xy)} shown)"
        if occupied_total == len(occupied_xy):
            occupied_label = f"Occupied Cells ({occupied_total})"
        ax_xy.scatter(
            occupied_xy[:, 0],
            occupied_xy[:, 1],
            color="#7f7f7f",
            marker="s",
            s=8,
            alpha=0.18,
            linewidths=0.0,
            label=occupied_label,
            zorder=1,
        )

    obstacle_label_used = False
    for x, y, radius in obstacles:
        label = None if obstacle_label_used else "Obstacles"
        if radius is not None:
            obstacle_circle = plt.Circle(
                (x, y),
                radius,
                edgecolor="#b22222",
                facecolor="none",
                linewidth=1.2,
                alpha=0.85,
            )
            ax_xy.add_patch(obstacle_circle)
        ax_xy.scatter(
            [x],
            [y],
            color="#b22222",
            marker="x",
            s=36,
            linewidths=1.4,
            label=label,
            zorder=2,
        )
        obstacle_label_used = True

    if len(planned_xy) > 0:
        ax_xy.plot(
            planned_xy[:, 0],
            planned_xy[:, 1],
            color="#1f77b4",
            linestyle="--",
            linewidth=2.0,
            label=f"Planned ({len(planned_xy)} pts)",
            zorder=3,
        )
        ax_xy.scatter(
            planned_xy[0, 0],
            planned_xy[0, 1],
            color="#1f77b4",
            marker="o",
            s=55,
            label="Plan Start",
            zorder=4,
        )
        ax_xy.scatter(
            planned_xy[-1, 0],
            planned_xy[-1, 1],
            color="#1f77b4",
            marker="X",
            s=85,
            label="Plan Goal",
            zorder=4,
        )

    if len(actual_xy) > 0:
        ax_xy.plot(
            actual_xy[:, 0],
            actual_xy[:, 1],
            color="#ff7f0e",
            linewidth=2.0,
            label=f"Actual ({len(actual_xy)} pts)",
            zorder=5,
        )
        ax_xy.scatter(
            actual_xy[0, 0],
            actual_xy[0, 1],
            color="#ff7f0e",
            marker="o",
            s=45,
            label="Actual Start",
            zorder=6,
        )
        ax_xy.scatter(
            actual_xy[-1, 0],
            actual_xy[-1, 1],
            color="#ff7f0e",
            marker="s",
            s=60,
            label="Actual End",
            zorder=6,
        )

    ax_xy.set_title("Trajectory Comparison (XY)")
    ax_xy.set_xlabel("X (m)")
    ax_xy.set_ylabel("Y (m)")
    ax_xy.grid(True, alpha=0.25)
    ax_xy.set_aspect("equal", adjustable="box")
    ax_xy.legend(loc="best", fontsize=9)

    has_metric_series = False
    if len(nearest_dist) > 0:
        ax_metric.plot(
            step_idx,
            nearest_dist,
            color="#2ca02c",
            linewidth=1.8,
            label="Nearest distance to plan (m)",
        )
        has_metric_series = True
    goal_steps, goal_dist = _extract_step_series(
        tick_traces, key="distance_to_goal_m"
    )
    if len(goal_steps) > 0:
        ax_metric.plot(
            goal_steps,
            goal_dist,
            color="#d62728",
            linewidth=1.2,
            alpha=0.9,
            label="Distance to goal (m)",
        )
        has_metric_series = True

    speed_steps, speed_values = _extract_step_series(tick_traces, key="speed_mps")
    if not has_metric_series and len(speed_steps) > 0:
        ax_metric.plot(
            speed_steps,
            speed_values,
            color="#9467bd",
            linewidth=1.4,
            label="Speed (m/s)",
        )
        has_metric_series = True

    ax_metric.set_title("Tracking Metrics")
    ax_metric.set_xlabel("Step")
    ax_metric.set_ylabel("Distance (m)" if len(nearest_dist) > 0 or len(goal_steps) > 0 else "Speed (m/s)")
    ax_metric.grid(True, alpha=0.25)
    if has_metric_series:
        ax_metric.legend(loc="best", fontsize=8)
    else:
        ax_metric.text(
            0.5,
            0.5,
            "No metric series available",
            ha="center",
            va="center",
            transform=ax_metric.transAxes,
            fontsize=9,
            color="#666666",
        )

    dist_text = "n/a" if final_dist is None else f"{float(final_dist):.3f}m"
    reached_goal_text = summary.get("reached_goal")
    if reached_goal_text is None:
        reached_goal_text = "n/a"
    fig.suptitle(
        "Tracking vs Plan | "
        f"map={map_name}, reached_goal={reached_goal_text}, "
        f"reason={termination_reason}, final_dist={dist_text}",
        fontsize=11,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    output_path = args.output or _default_output_path(metrics_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=args.dpi)
    print(f"saved: {output_path}")

    if args.show:
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
