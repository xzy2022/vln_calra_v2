"""Use case for recording spawned objects for scene export."""

from __future__ import annotations

from dataclasses import dataclass, field

from vln_carla2.domain.model.scene_template import SceneObject
from vln_carla2.usecases.scene_editor.ports.scene_object_recorder import (
    SceneObjectRecorderPort,
)


def _new_scene_object_list() -> list[SceneObject]:
    return []


@dataclass(slots=True)
class RecordSpawnedSceneObject(SceneObjectRecorderPort):
    """In-memory recorder for scene objects spawned in current session."""

    _objects: list[SceneObject] = field(default_factory=_new_scene_object_list)

    def run(self, obj: SceneObject) -> None:
        self._objects.append(obj)

    def record(self, obj: SceneObject) -> None:
        self.run(obj)

    def snapshot(self) -> list[SceneObject]:
        return list(self._objects)
