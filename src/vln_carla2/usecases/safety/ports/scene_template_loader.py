"""Port for loading one scene template from storage."""

from typing import Protocol

from vln_carla2.domain.model.scene_template import SceneTemplate


class SceneTemplateLoaderPort(Protocol):
    """Load one scene template from a path."""

    def load(self, path: str) -> SceneTemplate:
        ...
