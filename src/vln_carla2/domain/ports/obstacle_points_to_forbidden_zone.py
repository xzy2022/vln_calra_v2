"""Domain port for converting obstacle point sets to forbidden zones."""

from typing import Iterable, Protocol

from vln_carla2.domain.model.forbidden_zone import ForbiddenZone
from vln_carla2.domain.model.point2d import Point2D


class ObstaclePointsToForbiddenZonePort(Protocol):
    """Build one forbidden zone from obstacle points."""

    def build(self, obstacle_points: Iterable[Point2D]) -> ForbiddenZone:
        ...
