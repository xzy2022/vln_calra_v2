"""Tracking route planner adapter backed by planning slice API."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from vln_carla2.domain.model.forbidden_zone import ForbiddenZone
from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.point2d import Point2D
from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.domain.services.forbidden_zone_rules import is_point_in_forbidden_zone
from vln_carla2.usecases.planning.api import (
    BuildPlanningMap,
    BuildPlanningMapRequest,
    PlanRoute,
    PlanRouteRequest,
)
from vln_carla2.usecases.tracking.models import RoutePoint


@dataclass(slots=True)
class PlanningApiRoutePlannerAdapter:
    """Adapter that maps planning API path output to tracking RoutePoint DTO."""

    map_name: str
    build_planning_map: BuildPlanningMap
    plan_route_usecase: PlanRoute
    forbidden_zone: ForbiddenZone | None = None
    last_planning_map: PlanningMap | None = field(default=None, init=False)

    def plan_route(
        self,
        *,
        start_x: float,
        start_y: float,
        start_yaw_deg: float,
        goal: Any,
        route_step_m: float,
        route_max_points: int,
    ) -> tuple[RoutePoint, ...]:
        start_pose = Pose2D(x=start_x, y=start_y, yaw_deg=start_yaw_deg)
        goal_pose = Pose2D(x=float(goal.x), y=float(goal.y), yaw_deg=float(goal.yaw_deg))

        planning_map = self.build_planning_map.run(
            BuildPlanningMapRequest(
                map_name=self.map_name,
                start=start_pose,
                goal=goal_pose,
            )
        )
        planning_map = _embed_forbidden_zone_occupied_cells(
            planning_map=planning_map,
            forbidden_zone=self.forbidden_zone,
        )
        self.last_planning_map = planning_map
        path = self.plan_route_usecase.run(
            PlanRouteRequest(
                start=start_pose,
                goal=goal_pose,
                planning_map=planning_map,
                route_step_m=route_step_m,
                route_max_points=route_max_points,
            )
        )
        return tuple(
            RoutePoint(x=pose.x, y=pose.y, yaw_deg=pose.yaw_deg)
            for pose in path.poses
        )


def _embed_forbidden_zone_occupied_cells(
    *,
    planning_map: PlanningMap,
    forbidden_zone: ForbiddenZone | None,
) -> PlanningMap:
    if forbidden_zone is None:
        return planning_map

    xs = [vertex.x for vertex in forbidden_zone.vertices]
    ys = [vertex.y for vertex in forbidden_zone.vertices]
    min_zone_x = min(xs)
    max_zone_x = max(xs)
    min_zone_y = min(ys)
    max_zone_y = max(ys)

    overlap_min_x = max(planning_map.min_x, min_zone_x)
    overlap_max_x = min(planning_map.max_x, max_zone_x)
    overlap_min_y = max(planning_map.min_y, min_zone_y)
    overlap_max_y = min(planning_map.max_y, max_zone_y)
    if overlap_max_x < overlap_min_x or overlap_max_y < overlap_min_y:
        return planning_map

    resolution = planning_map.resolution_m
    min_cell_x = max(
        0,
        int(math.floor((overlap_min_x - planning_map.min_x) / resolution)),
    )
    max_cell_x = min(
        planning_map.width - 1,
        int(math.floor((overlap_max_x - planning_map.min_x) / resolution)),
    )
    min_cell_y = max(
        0,
        int(math.floor((overlap_min_y - planning_map.min_y) / resolution)),
    )
    max_cell_y = min(
        planning_map.height - 1,
        int(math.floor((overlap_max_y - planning_map.min_y) / resolution)),
    )
    if max_cell_x < min_cell_x or max_cell_y < min_cell_y:
        return planning_map

    occupied = set(planning_map.occupied_cells)
    original_count = len(occupied)
    for cell_x in range(min_cell_x, max_cell_x + 1):
        world_x = planning_map.min_x + (float(cell_x) + 0.5) * resolution
        for cell_y in range(min_cell_y, max_cell_y + 1):
            world_y = planning_map.min_y + (float(cell_y) + 0.5) * resolution
            if is_point_in_forbidden_zone(
                point=Point2D(x=world_x, y=world_y),
                zone=forbidden_zone,
            ):
                occupied.add((cell_x, cell_y))

    if len(occupied) == original_count:
        return planning_map

    return PlanningMap(
        map_name=planning_map.map_name,
        resolution_m=planning_map.resolution_m,
        min_x=planning_map.min_x,
        max_x=planning_map.max_x,
        min_y=planning_map.min_y,
        max_y=planning_map.max_y,
        width=planning_map.width,
        height=planning_map.height,
        occupied_cells=tuple(sorted(occupied)),
    )
