"""Forward-only Hybrid A* planner."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from vln_carla2.domain.model.path import Path
from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.domain.services.planning.collision_checker import is_segment_colliding
from vln_carla2.domain.services.planning.heuristics import (
    absolute_yaw_error_deg,
    euclidean_distance_xy,
    normalize_yaw_deg,
)
from vln_carla2.domain.services.planning.motion_primitives import (
    ForwardMotionPrimitive,
    apply_forward_motion,
    build_forward_motion_primitives,
)


_NodeKey = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class _NodeRecord:
    key: _NodeKey
    pose: Pose2D
    parent_key: _NodeKey | None
    g_cost: float


@dataclass(slots=True)
class HybridAStarForwardPlanner:
    """Hybrid A* with forward-only primitives and yaw-bin state."""

    yaw_bin_deg: float = 15.0
    primitive_step_m: float = 1.0
    max_iterations: int = 80000
    yaw_goal_tolerance_deg: float = 15.0
    sample_step_m: float = 0.25

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
        if self.yaw_bin_deg <= 0.0:
            raise ValueError("yaw_bin_deg must be > 0")
        if self.primitive_step_m <= 0.0:
            raise ValueError("primitive_step_m must be > 0")
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be > 0")
        if self.sample_step_m <= 0.0:
            raise ValueError("sample_step_m must be > 0")

        try:
            planning_map.world_to_grid(x=start.x, y=start.y)
            planning_map.world_to_grid(x=goal.x, y=goal.y)
        except ValueError as exc:
            raise RuntimeError(f"hybrid astar input out of map bounds: {exc}") from exc

        if planning_map.is_world_occupied(x=start.x, y=start.y):
            raise RuntimeError("hybrid astar start pose is occupied")
        if planning_map.is_world_occupied(x=goal.x, y=goal.y):
            raise RuntimeError("hybrid astar goal pose is occupied")

        primitives = build_forward_motion_primitives(
            step_m=self.primitive_step_m,
            turn_delta_deg=self.yaw_bin_deg,
        )
        start_key = _pose_to_key(
            pose=start,
            planning_map=planning_map,
            yaw_bin_deg=self.yaw_bin_deg,
        )

        records: dict[_NodeKey, _NodeRecord] = {
            start_key: _NodeRecord(
                key=start_key,
                pose=start,
                parent_key=None,
                g_cost=0.0,
            )
        }
        best_cost: dict[_NodeKey, float] = {start_key: 0.0}

        open_heap: list[tuple[float, float, _NodeKey]] = []
        heapq.heappush(
            open_heap,
            (
                _f_score(
                    pose=start,
                    goal=goal,
                    g_cost=0.0,
                    yaw_weight=0.05,
                ),
                0.0,
                start_key,
            ),
        )

        iterations = 0
        goal_key: _NodeKey | None = None
        while open_heap:
            _, current_g, current_key = heapq.heappop(open_heap)
            current_record = records[current_key]
            if current_g > best_cost.get(current_key, float("inf")):
                continue

            if _is_goal_reached(
                pose=current_record.pose,
                goal=goal,
                distance_tolerance_m=max(route_step_m, self.primitive_step_m),
                yaw_tolerance_deg=max(self.yaw_goal_tolerance_deg, self.yaw_bin_deg),
            ):
                goal_key = current_key
                break

            iterations += 1
            if iterations > self.max_iterations:
                raise RuntimeError("hybrid astar failed: max iterations exceeded")

            for primitive in primitives:
                candidate_pose = apply_forward_motion(
                    pose=current_record.pose,
                    primitive=primitive,
                )
                if is_segment_colliding(
                    start=current_record.pose,
                    end=candidate_pose,
                    planning_map=planning_map,
                    sample_step_m=self.sample_step_m,
                ):
                    continue

                candidate_key = _pose_to_key(
                    pose=candidate_pose,
                    planning_map=planning_map,
                    yaw_bin_deg=self.yaw_bin_deg,
                )
                candidate_g = current_record.g_cost + _primitive_cost(primitive=primitive)
                if candidate_g >= best_cost.get(candidate_key, float("inf")):
                    continue

                best_cost[candidate_key] = candidate_g
                records[candidate_key] = _NodeRecord(
                    key=candidate_key,
                    pose=candidate_pose,
                    parent_key=current_key,
                    g_cost=candidate_g,
                )
                heapq.heappush(
                    open_heap,
                    (
                        _f_score(
                            pose=candidate_pose,
                            goal=goal,
                            g_cost=candidate_g,
                            yaw_weight=0.05,
                        ),
                        candidate_g,
                        candidate_key,
                    ),
                )

        if goal_key is None:
            raise RuntimeError("hybrid astar failed to find path")

        chain = _reconstruct_poses(goal_key=goal_key, records=records)
        chain.append(Pose2D(x=goal.x, y=goal.y, yaw_deg=goal.yaw_deg))
        sampled = _resample_poses(poses=chain, route_step_m=route_step_m)
        if len(sampled) > route_max_points:
            raise RuntimeError(
                "hybrid astar path exceeds route_max_points: "
                f"points={len(sampled)} route_max_points={route_max_points}"
            )
        return Path(poses=tuple(sampled))


def _pose_to_key(
    *,
    pose: Pose2D,
    planning_map: PlanningMap,
    yaw_bin_deg: float,
) -> _NodeKey:
    cell_x, cell_y = planning_map.world_to_grid(x=pose.x, y=pose.y)
    yaw_bins = max(1, int(round(360.0 / yaw_bin_deg)))
    yaw_norm = normalize_yaw_deg(pose.yaw_deg) + 180.0
    yaw_idx = int(round(yaw_norm / yaw_bin_deg)) % yaw_bins
    return (cell_x, cell_y, yaw_idx)


def _primitive_cost(*, primitive: ForwardMotionPrimitive) -> float:
    turn_penalty = 0.05 if abs(primitive.delta_yaw_deg) > 1e-6 else 0.0
    return primitive.step_m * (1.0 + turn_penalty)


def _f_score(*, pose: Pose2D, goal: Pose2D, g_cost: float, yaw_weight: float) -> float:
    distance_h = euclidean_distance_xy(x1=pose.x, y1=pose.y, x2=goal.x, y2=goal.y)
    yaw_h = absolute_yaw_error_deg(yaw_deg=pose.yaw_deg, target_yaw_deg=goal.yaw_deg)
    return g_cost + distance_h + yaw_weight * yaw_h


def _is_goal_reached(
    *,
    pose: Pose2D,
    goal: Pose2D,
    distance_tolerance_m: float,
    yaw_tolerance_deg: float,
) -> bool:
    return (
        euclidean_distance_xy(x1=pose.x, y1=pose.y, x2=goal.x, y2=goal.y)
        <= distance_tolerance_m
        and absolute_yaw_error_deg(yaw_deg=pose.yaw_deg, target_yaw_deg=goal.yaw_deg)
        <= yaw_tolerance_deg
    )


def _reconstruct_poses(
    *,
    goal_key: _NodeKey,
    records: dict[_NodeKey, _NodeRecord],
) -> list[Pose2D]:
    poses: list[Pose2D] = []
    cursor: _NodeKey | None = goal_key
    while cursor is not None:
        record = records[cursor]
        poses.append(record.pose)
        cursor = record.parent_key
    poses.reverse()
    return poses


def _resample_poses(*, poses: list[Pose2D], route_step_m: float) -> list[Pose2D]:
    if len(poses) <= 2:
        return list(poses)

    sampled: list[Pose2D] = [poses[0]]
    accumulated = 0.0

    for idx in range(1, len(poses)):
        prev = poses[idx - 1]
        curr = poses[idx]
        segment = math.hypot(curr.x - prev.x, curr.y - prev.y)
        accumulated += segment
        if accumulated >= route_step_m:
            sampled.append(curr)
            accumulated = 0.0

    if sampled[-1] != poses[-1]:
        sampled.append(poses[-1])
    return sampled

