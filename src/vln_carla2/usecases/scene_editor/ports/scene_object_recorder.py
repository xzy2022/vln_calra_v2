"""Port for recording exported scene objects."""

from typing import Protocol

from vln_carla2.domain.model.scene_template import SceneObject


class SceneObjectRecorderPort(Protocol):
    """Append-only recorder for objects spawned during scene editing."""

    def record(self, obj: SceneObject) -> None:
        ...

    def snapshot(self) -> list[SceneObject]:
        ...
