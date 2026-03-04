"""Baseline 2D grid A* planner."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from vln_carla2.domain.model.path import Path
from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.domain.services.planning.heuristics import euclidean_distance_xy


_GRID_NEIGHBORS: tuple[tuple[int, int, float], ...] = (
    (1, 0, 1.0),
    (-1, 0, 1.0),
    (0, 1, 1.0),
    (0, -1, 1.0),
    (1, 1, math.sqrt(2.0)),
    (1, -1, math.sqrt(2.0)),
    (-1, 1, math.sqrt(2.0)),
    (-1, -1, math.sqrt(2.0)),
)


@dataclass(slots=True)
class GridAStarPlanner:
    """Compute path using occupancy-grid A*."""

    max_expansions: int = 200000

    def plan(
        self,
        *,
        start: Pose2D,
        goal: Pose2D,
        planning_map: PlanningMap,
        route_step_m: float,
        route_max_points: int,
    ) -> Path:
        if route_step_m <= 0.0:
            raise ValueError("route_step_m must be > 0")
        if route_max_points <= 0:
            raise ValueError("route_max_points must be > 0")
        if self.max_expansions <= 0:
            raise ValueError("max_expansions must be > 0")

        try:
            start_cell = planning_map.world_to_grid(x=start.x, y=start.y)
            goal_cell = planning_map.world_to_grid(x=goal.x, y=goal.y)
        except ValueError as exc:
            raise RuntimeError(f"grid astar input out of map bounds: {exc}") from exc

        if planning_map.is_cell_occupied(cell_x=start_cell[0], cell_y=start_cell[1]):
            raise RuntimeError("grid astar start cell is occupied")
        if planning_map.is_cell_occupied(cell_x=goal_cell[0], cell_y=goal_cell[1]):
            raise RuntimeError("grid astar goal cell is occupied")

        open_heap: list[tuple[float, float, tuple[int, int]]] = []
        parent: dict[tuple[int, int], tuple[int, int] | None] = {start_cell: None}
        g_score: dict[tuple[int, int], float] = {start_cell: 0.0}

        heapq.heappush(
            open_heap,
            (
                _cell_heuristic(cell=start_cell, goal=goal_cell),
                0.0,
                start_cell,
            ),
        )

        expansions = 0
        goal_reached = False
        while open_heap:
            _, current_g, current = heapq.heappop(open_heap)
            if current == goal_cell:
                goal_reached = True
                break
            if current_g > g_score.get(current, float("inf")):
                continue

            expansions += 1
            if expansions > self.max_expansions:
                raise RuntimeError("grid astar failed: max expansions exceeded")

            for delta_x, delta_y, step_cost in _GRID_NEIGHBORS:
                neighbor = (current[0] + delta_x, current[1] + delta_y)
                if not planning_map.in_bounds(cell_x=neighbor[0], cell_y=neighbor[1]):
                    continue
                if planning_map.is_cell_occupied(cell_x=neighbor[0], cell_y=neighbor[1]):
                    continue

                candidate_g = current_g + step_cost
                if candidate_g >= g_score.get(neighbor, float("inf")):
                    continue

                g_score[neighbor] = candidate_g
                parent[neighbor] = current
                heapq.heappush(
                    open_heap,
                    (
                        candidate_g + _cell_heuristic(cell=neighbor, goal=goal_cell),
                        candidate_g,
                        neighbor,
                    ),
                )

        if not goal_reached:
            raise RuntimeError("grid astar failed to find path")

        cells = _reconstruct_cells(goal_cell=goal_cell, parent=parent)
        poses = _cells_to_poses(
            cells=cells,
            planning_map=planning_map,
            start=start,
            goal=goal,
        )
        sampled = _resample_poses(poses=poses, route_step_m=route_step_m)
        if len(sampled) > route_max_points:
            raise RuntimeError(
                "grid astar path exceeds route_max_points: "
                f"points={len(sampled)} route_max_points={route_max_points}"
            )
        return Path(poses=tuple(sampled))


def _cell_heuristic(*, cell: tuple[int, int], goal: tuple[int, int]) -> float:
    return math.hypot(float(goal[0] - cell[0]), float(goal[1] - cell[1]))


def _reconstruct_cells(
    *,
    goal_cell: tuple[int, int],
    parent: dict[tuple[int, int], tuple[int, int] | None],
) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    cursor: tuple[int, int] | None = goal_cell
    while cursor is not None:
        cells.append(cursor)
        cursor = parent.get(cursor)
    cells.reverse()
    return cells


def _cells_to_poses(
    *,
    cells: list[tuple[int, int]],
    planning_map: PlanningMap,
    start: Pose2D,
    goal: Pose2D,
) -> list[Pose2D]:
    if not cells:
        return [start, goal]

    centers = [planning_map.grid_to_world(cell_x=cell[0], cell_y=cell[1]) for cell in cells]
    points: list[Pose2D] = [Pose2D(x=start.x, y=start.y, yaw_deg=start.yaw_deg)]

    for idx in range(1, len(centers)):
        prev_x, prev_y = centers[idx - 1]
        curr_x, curr_y = centers[idx]
        yaw = math.degrees(math.atan2(curr_y - prev_y, curr_x - prev_x))
        points.append(Pose2D(x=curr_x, y=curr_y, yaw_deg=yaw))

    if euclidean_distance_xy(
        x1=points[-1].x,
        y1=points[-1].y,
        x2=goal.x,
        y2=goal.y,
    ) > 1e-6:
        points.append(Pose2D(x=goal.x, y=goal.y, yaw_deg=goal.yaw_deg))
    else:
        points[-1] = Pose2D(x=goal.x, y=goal.y, yaw_deg=goal.yaw_deg)

    return points


def _resample_poses(*, poses: list[Pose2D], route_step_m: float) -> list[Pose2D]:
    if len(poses) <= 2:
        return list(poses)

    sampled: list[Pose2D] = [poses[0]]
    accumulated = 0.0

    for idx in range(1, len(poses)):
        prev = poses[idx - 1]
        curr = poses[idx]
        segment = euclidean_distance_xy(x1=prev.x, y1=prev.y, x2=curr.x, y2=curr.y)
        accumulated += segment
        if accumulated >= route_step_m:
            sampled.append(curr)
            accumulated = 0.0

    if sampled[-1] != poses[-1]:
        sampled.append(poses[-1])
    return sampled

