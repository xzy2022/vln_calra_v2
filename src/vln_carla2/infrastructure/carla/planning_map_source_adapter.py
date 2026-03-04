"""CARLA-backed planning map source adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vln_carla2.domain.model.obstacle import Obstacle
from vln_carla2.domain.model.planning_map import PlanningMapSeed
from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.domain.model.scene_template import SceneObjectKind, SceneTemplate
from vln_carla2.usecases.planning.ports.map_source import PlanningMapSourcePort

_BARREL_RADIUS_M = 0.5
_MIN_SPAN_M = 1.0


@dataclass(slots=True)
class CarlaPlanningMapSourceAdapter(PlanningMapSourcePort):
    """Build map seed from scene template barrels and CARLA spawn points."""

    world: Any
    scene_template: SceneTemplate

    def snapshot(
        self,
        *,
        map_name: str,
        start: Pose2D,
        goal: Pose2D,
    ) -> PlanningMapSeed:
        points_xy: list[tuple[float, float]] = [(start.x, start.y), (goal.x, goal.y)]

        obstacles: list[Obstacle] = []
        for obj in self.scene_template.objects:
            if obj.kind != SceneObjectKind.BARREL:
                continue
            obstacle = Obstacle(x=obj.pose.x, y=obj.pose.y, radius_m=_BARREL_RADIUS_M)
            obstacles.append(obstacle)
            points_xy.append((obstacle.x, obstacle.y))

        points_xy.extend(self._spawn_points_xy())

        xs = [point[0] for point in points_xy]
        ys = [point[1] for point in points_xy]
        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)

        if max_x - min_x < _MIN_SPAN_M:
            center_x = 0.5 * (min_x + max_x)
            min_x = center_x - 0.5 * _MIN_SPAN_M
            max_x = center_x + 0.5 * _MIN_SPAN_M
        if max_y - min_y < _MIN_SPAN_M:
            center_y = 0.5 * (min_y + max_y)
            min_y = center_y - 0.5 * _MIN_SPAN_M
            max_y = center_y + 0.5 * _MIN_SPAN_M

        return PlanningMapSeed(
            map_name=map_name,
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
            obstacles=tuple(obstacles),
        )

    def _spawn_points_xy(self) -> tuple[tuple[float, float], ...]:
        try:
            world_map = self.world.get_map()
            spawn_points = world_map.get_spawn_points()
        except Exception:
            return ()

        points: list[tuple[float, float]] = []
        for transform in spawn_points:
            location = getattr(transform, "location", None)
            if location is None:
                continue
            points.append((float(location.x), float(location.y)))
        return tuple(points)

