"""Planner outbound port for planning use cases."""

from __future__ import annotations

from typing import Protocol

from vln_carla2.domain.model.path import Path
from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.pose2d import Pose2D


class PlannerPort(Protocol):
    """Path planner interface."""

    def plan(
        self,
        *,
        start: Pose2D,
        goal: Pose2D,
        planning_map: PlanningMap,
        route_step_m: float,
        route_max_points: int,
    ) -> Path:
        ...

