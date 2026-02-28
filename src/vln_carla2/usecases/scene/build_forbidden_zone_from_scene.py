"""Build forbidden zone from scene-template barrel points."""

from __future__ import annotations

from dataclasses import dataclass

from vln_carla2.domain.model.forbidden_zone import ForbiddenZone
from vln_carla2.domain.model.point2d import Point2D
from vln_carla2.domain.model.scene_template import SceneObjectKind
from vln_carla2.domain.ports.obstacle_points_to_forbidden_zone import (
    ObstaclePointsToForbiddenZonePort,
)
from vln_carla2.domain.services.scene_template_rules import (
    assert_map_matches,
    assert_supported_schema,
)
from vln_carla2.usecases.scene.ports.scene_template_loader import SceneTemplateLoaderPort


@dataclass(slots=True)
class BuildForbiddenZoneFromScene:
    """Load scene template, extract barrel points, and build forbidden zone."""

    scene_loader: SceneTemplateLoaderPort
    zone_builder: ObstaclePointsToForbiddenZonePort
    expected_map_name: str | None = None

    def run(self, scene_json_path: str) -> ForbiddenZone:
        template = self.scene_loader.load(scene_json_path)
        assert_supported_schema(template.schema_version)
        if self.expected_map_name is not None:
            assert_map_matches(
                expected_map_name=self.expected_map_name,
                template_map_name=template.map_name,
            )

        obstacle_points = [
            Point2D(x=obj.pose.x, y=obj.pose.y)
            for obj in template.objects
            if obj.kind == SceneObjectKind.BARREL
        ]
        if not obstacle_points:
            raise ValueError("scene template contains no barrel objects")
        return self.zone_builder.build(obstacle_points)

