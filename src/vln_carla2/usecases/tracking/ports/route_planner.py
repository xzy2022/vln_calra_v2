"""Route planner port for tracking use case."""

from typing import Protocol

from vln_carla2.usecases.tracking.models import RoutePoint, TrackingGoal


class RoutePlannerPort(Protocol):
    """Build route points between start and goal."""

    def plan_route(
        self,
        *,
        start_x: float,
        start_y: float,
        start_yaw_deg: float,
        goal: TrackingGoal,
        route_step_m: float,
        route_max_points: int,
    ) -> tuple[RoutePoint, ...]:
        ...

