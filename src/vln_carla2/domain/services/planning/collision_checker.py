"""Collision checks against occupancy planning map."""

from __future__ import annotations

import math

from vln_carla2.domain.model.path import Path
from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.pose2d import Pose2D


def is_pose_colliding(*, pose: Pose2D, planning_map: PlanningMap) -> bool:
    return planning_map.is_world_occupied(x=pose.x, y=pose.y)


def is_segment_colliding(
    *,
    start: Pose2D,
    end: Pose2D,
    planning_map: PlanningMap,
    sample_step_m: float,
) -> bool:
    if sample_step_m <= 0.0:
        raise ValueError("sample_step_m must be > 0")

    distance = math.hypot(end.x - start.x, end.y - start.y)
    steps = max(1, int(math.ceil(distance / sample_step_m)))

    for idx in range(steps + 1):
        ratio = float(idx) / float(steps)
        sample_x = start.x + (end.x - start.x) * ratio
        sample_y = start.y + (end.y - start.y) * ratio
        if planning_map.is_world_occupied(x=sample_x, y=sample_y):
            return True
    return False


def is_path_colliding(
    *,
    path: Path,
    planning_map: PlanningMap,
    sample_step_m: float,
) -> bool:
    if len(path.poses) == 1:
        return is_pose_colliding(pose=path.poses[0], planning_map=planning_map)

    for idx in range(len(path.poses) - 1):
        if is_segment_colliding(
            start=path.poses[idx],
            end=path.poses[idx + 1],
            planning_map=planning_map,
            sample_step_m=sample_step_m,
        ):
            return True
    return False

