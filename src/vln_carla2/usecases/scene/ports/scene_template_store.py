"""Port for loading/saving scene templates."""

from typing import Protocol

from vln_carla2.domain.model.scene_template import SceneTemplate


class SceneTemplateStorePort(Protocol):
    """Persistence port for scene-template JSON."""

    def load(self, path: str) -> SceneTemplate:
        ...

    def save(self, template: SceneTemplate, path: str | None) -> str:
        ...
