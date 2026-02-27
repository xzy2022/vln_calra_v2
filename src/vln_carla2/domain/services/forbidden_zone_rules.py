"""Pure rules for forbidden-zone checks."""

from __future__ import annotations

from typing import Iterable

from vln_carla2.domain.model.forbidden_zone import ForbiddenZone
from vln_carla2.domain.model.point2d import Point2D
from vln_carla2.domain.model.vehicle_state import VehicleState

_GEOMETRY_EPSILON = 1e-9


def is_point_in_forbidden_zone(point: Point2D, zone: ForbiddenZone) -> bool:
    """Return True when point is inside polygon or on its boundary."""
    x = point.x
    y = point.y
    vertices = zone.vertices
    inside = False

    for index in range(len(vertices)):
        start = vertices[index]
        end = vertices[(index + 1) % len(vertices)]

        if _is_point_on_segment(point=point, start=start, end=end):
            return True

        if _is_ray_crossing_segment(x=x, y=y, start=start, end=end):
            inside = not inside

    return inside


def is_vehicle_state_in_forbidden_zone(state: VehicleState, zone: ForbiddenZone) -> bool:
    """Use vehicle XY position only (yaw is ignored)."""
    return is_point_in_forbidden_zone(Point2D(x=state.x, y=state.y), zone)


def has_entered_forbidden_zone(states: Iterable[VehicleState], zone: ForbiddenZone) -> bool:
    """Return True when any sampled state enters forbidden zone."""
    return any(is_vehicle_state_in_forbidden_zone(state, zone) for state in states)


def _is_ray_crossing_segment(*, x: float, y: float, start: Point2D, end: Point2D) -> bool:
    y1 = start.y
    y2 = end.y
    if (y1 > y) == (y2 > y):
        return False

    x1 = start.x
    x2 = end.x
    denominator = y2 - y1
    if abs(denominator) <= _GEOMETRY_EPSILON:
        return False

    x_intersection = x1 + (x2 - x1) * (y - y1) / denominator
    return x_intersection > x + _GEOMETRY_EPSILON


def _is_point_on_segment(*, point: Point2D, start: Point2D, end: Point2D) -> bool:
    px = point.x
    py = point.y
    x1 = start.x
    y1 = start.y
    x2 = end.x
    y2 = end.y

    cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    if abs(cross) > _GEOMETRY_EPSILON:
        return False

    min_x = min(x1, x2) - _GEOMETRY_EPSILON
    max_x = max(x1, x2) + _GEOMETRY_EPSILON
    min_y = min(y1, y2) - _GEOMETRY_EPSILON
    max_y = max(y1, y2) + _GEOMETRY_EPSILON
    return min_x <= px <= max_x and min_y <= py <= max_y
