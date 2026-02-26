"""Port for spawning one scene-template object."""

from typing import Protocol

from vln_carla2.domain.model.scene_template import SceneObject


class SceneObjectSpawnerPort(Protocol):
    """Spawn one scene object into runtime world."""

    def spawn(self, obj: SceneObject) -> None:
        ...
