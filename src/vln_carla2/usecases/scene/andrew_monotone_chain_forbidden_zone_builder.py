"""Build forbidden zone polygon from obstacle points via Andrew's algorithm."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from vln_carla2.domain.model.forbidden_zone import ForbiddenZone
from vln_carla2.domain.model.point2d import Point2D
from vln_carla2.domain.ports.obstacle_points_to_forbidden_zone import (
    ObstaclePointsToForbiddenZonePort,
)


@dataclass(slots=True)
class AndrewMonotoneChainForbiddenZoneBuilder(ObstaclePointsToForbiddenZonePort):
    """Construct convex polygon hull from obstacle points."""

    def build(self, obstacle_points: Iterable[Point2D]) -> ForbiddenZone:
        points = self._normalize_points(obstacle_points)
        if len(points) < 3:
            raise ValueError("at least 3 unique obstacle points are required")

        lower: list[Point2D] = []
        for point in points:
            while len(lower) >= 2 and _cross(lower[-2], lower[-1], point) <= 0.0:
                lower.pop()
            lower.append(point)

        upper: list[Point2D] = []
        for point in reversed(points):
            while len(upper) >= 2 and _cross(upper[-2], upper[-1], point) <= 0.0:
                upper.pop()
            upper.append(point)

        hull = lower[:-1] + upper[:-1]
        if len(hull) < 3:
            raise ValueError("obstacle points are collinear; forbidden zone area is zero")

        return ForbiddenZone(vertices=tuple(hull))

    def _normalize_points(self, points: Iterable[Point2D]) -> list[Point2D]:
        unique = {(float(point.x), float(point.y)) for point in points}
        return [Point2D(x=x, y=y) for x, y in sorted(unique)]


def _cross(origin: Point2D, point_a: Point2D, point_b: Point2D) -> float:
    return (point_a.x - origin.x) * (point_b.y - origin.y) - (
        point_a.y - origin.y
    ) * (point_b.x - origin.x)
