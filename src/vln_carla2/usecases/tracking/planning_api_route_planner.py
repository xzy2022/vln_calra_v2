"""Tracking route planner adapter backed by planning slice API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.pose2d import Pose2D
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
