"""CARLA route planner adapter for tracking use case."""

from __future__ import annotations

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
    """Build a route from start to goal using CARLA GlobalRoutePlanner."""

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

        planner_cls = _require_global_route_planner()
        planner = planner_cls(world_map, float(route_step_m))
        trace = planner.trace_route(
            start_waypoint.transform.location,
            goal_waypoint.transform.location,
        )
        route = [_to_route_point(_trace_waypoint(item)) for item in trace]
        if not route:
            raise RuntimeError(
                "failed to build waypoint route: "
                f"points=0 route_step_m={route_step_m:.3f} route_max_points={route_max_points}"
            )
        if len(route) > route_max_points:
            raise RuntimeError(
                "failed to build waypoint route: "
                f"points={len(route)} route_step_m={route_step_m:.3f} "
                f"route_max_points={route_max_points}"
            )
        return tuple(route)


def _to_route_point(waypoint: Any) -> _RoutePoint:
    transform = waypoint.transform
    return _RoutePoint(
        x=float(transform.location.x),
        y=float(transform.location.y),
        yaw_deg=float(transform.rotation.yaw),
    )


def _trace_waypoint(trace_item: Any) -> Any:
    if isinstance(trace_item, tuple) and trace_item:
        return trace_item[0]
    if isinstance(trace_item, list) and trace_item:
        return trace_item[0]
    return trace_item


def _import_global_route_planner() -> type[Any]:
    from agents.navigation.global_route_planner import GlobalRoutePlanner

    return GlobalRoutePlanner


def _require_global_route_planner() -> type[Any]:
    try:
        return _import_global_route_planner()
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "CARLA GlobalRoutePlanner is unavailable. Ensure CARLA PythonAPI agents "
            "modules are on PYTHONPATH (for example: <CARLA_ROOT>/PythonAPI/carla)."
        ) from exc
