"""CARLA adapter for spawning scene-template objects."""

from __future__ import annotations

from typing import Any

from vln_carla2.domain.model.scene_template import SceneObject
from vln_carla2.infrastructure.carla.spawner import spawn_vehicle
from vln_carla2.usecases.scene_editor.ports.scene_object_spawner import SceneObjectSpawnerPort


class CarlaSceneObjectSpawnerAdapter(SceneObjectSpawnerPort):
    """Spawn one scene object into CARLA world."""

    def __init__(self, world: Any) -> None:
        self._world = world

    def spawn(self, obj: SceneObject) -> None:
        spawn_vehicle(
            world=self._world,
            blueprint_filter=obj.blueprint_id,
            spawn_x=obj.pose.x,
            spawn_y=obj.pose.y,
            spawn_z=obj.pose.z,
            spawn_yaw=obj.pose.yaw,
            role_name=obj.role_name,
        )
