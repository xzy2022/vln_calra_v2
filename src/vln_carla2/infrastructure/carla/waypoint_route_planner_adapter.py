"""CARLA waypoint-based route planner adapter for tracking use case."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from vln_carla2.infrastructure.carla.types import require_carla
from vln_carla2.usecases.tracking.ports.route_planner import RoutePlannerPort


@dataclass(frozen=True, slots=True)
class _RoutePoint:
    x: float
    y: float
    yaw_deg: float


class CarlaWaypointRoutePlannerAdapter(RoutePlannerPort):
    """Build a forward waypoint route from start to goal using map waypoint API only."""

    def __init__(self, world: Any) -> None:
        self._world = world

    def plan_route(
        self,
        *,
        start_x: float,
        start_y: float,
        start_yaw_deg: float,
        goal: Any,
        route_step_m: float,
        route_max_points: int,
    ) -> tuple[_RoutePoint, ...]:
        del start_yaw_deg
        if route_step_m <= 0.0:
            raise ValueError("route_step_m must be > 0")
        if route_max_points <= 0:
            raise ValueError("route_max_points must be > 0")

        carla = require_carla()
        world_map = self._world.get_map()
        start_waypoint = world_map.get_waypoint(
            carla.Location(x=float(start_x), y=float(start_y), z=0.0),
            project_to_road=True,
        )
        goal_waypoint = world_map.get_waypoint(
            carla.Location(x=float(goal.x), y=float(goal.y), z=0.0),
            project_to_road=True,
        )
        if start_waypoint is None:
            raise RuntimeError(
                f"start waypoint not found near (x={float(start_x):.3f}, y={float(start_y):.3f})"
            )
        if goal_waypoint is None:
            raise RuntimeError(
                f"goal waypoint not found near (x={float(goal.x):.3f}, y={float(goal.y):.3f})"
            )

        route: list[_RoutePoint] = [_to_route_point(start_waypoint)]
        current_waypoint = start_waypoint
        visited_keys = {_waypoint_key(start_waypoint)}
        goal_accept_distance_m = max(route_step_m, 1.0)

        for _ in range(route_max_points - 1):
            if _distance_xy(
                x1=float(current_waypoint.transform.location.x),
                y1=float(current_waypoint.transform.location.y),
                x2=float(goal_waypoint.transform.location.x),
                y2=float(goal_waypoint.transform.location.y),
            ) <= goal_accept_distance_m:
                return tuple(route)

            candidates = list(current_waypoint.next(float(route_step_m)))
            if not candidates:
                break

            ranked = sorted(
                candidates,
                key=lambda candidate: (
                    _distance_xy(
                        x1=float(candidate.transform.location.x),
                        y1=float(candidate.transform.location.y),
                        x2=float(goal_waypoint.transform.location.x),
                        y2=float(goal_waypoint.transform.location.y),
                    ),
                    _absolute_yaw_error_deg(
                        yaw_deg=float(candidate.transform.rotation.yaw),
                        target_yaw_deg=float(goal.yaw_deg),
                    ),
                ),
            )

            next_waypoint = None
            for candidate in ranked:
                key = _waypoint_key(candidate)
                if key not in visited_keys:
                    next_waypoint = candidate
                    break
            if next_waypoint is None:
                next_waypoint = ranked[0]

            current_waypoint = next_waypoint
            visited_keys.add(_waypoint_key(current_waypoint))
            route.append(_to_route_point(current_waypoint))

        if _distance_xy(
            x1=route[-1].x,
            y1=route[-1].y,
            x2=float(goal_waypoint.transform.location.x),
            y2=float(goal_waypoint.transform.location.y),
        ) <= goal_accept_distance_m:
            return tuple(route)

        raise RuntimeError(
            "failed to build waypoint route: "
            f"points={len(route)} route_step_m={route_step_m:.3f} route_max_points={route_max_points}"
        )


def _to_route_point(waypoint: Any) -> _RoutePoint:
    transform = waypoint.transform
    return _RoutePoint(
        x=float(transform.location.x),
        y=float(transform.location.y),
        yaw_deg=float(transform.rotation.yaw),
    )


def _waypoint_key(waypoint: Any) -> tuple[int, int, int, float]:
    return (
        int(waypoint.road_id),
        int(waypoint.section_id),
        int(waypoint.lane_id),
        round(float(waypoint.s), 1),
    )


def _distance_xy(*, x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def _absolute_yaw_error_deg(*, yaw_deg: float, target_yaw_deg: float) -> float:
    delta = (target_yaw_deg - yaw_deg + 180.0) % 360.0 - 180.0
    return abs(delta)

