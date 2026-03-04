"""Use case for route planning on planning map."""

from __future__ import annotations

from dataclasses import dataclass

from vln_carla2.domain.model.path import Path
from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.usecases.planning.ports.planner import PlannerPort


@dataclass(frozen=True, slots=True)
class PlanRouteRequest:
    """Input payload for one route planning request."""

    start: Pose2D
    goal: Pose2D
    planning_map: PlanningMap
    route_step_m: float
    route_max_points: int


@dataclass(slots=True)
class PlanRoute:
    """Plan one route path using planner port."""

    planner: PlannerPort

    def run(self, request: PlanRouteRequest) -> Path:
        return self.planner.plan(
            start=request.start,
            goal=request.goal,
            planning_map=request.planning_map,
            route_step_m=request.route_step_m,
            route_max_points=request.route_max_points,
        )

