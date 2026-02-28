"""Filesystem adapter for scene-template metadata lookups."""

from dataclasses import dataclass, field

from vln_carla2.infrastructure.filesystem.scene_template_json_store import SceneTemplateJsonStore
from vln_carla2.usecases.cli.ports.scene_template_loader import SceneTemplateLoaderPort


@dataclass(slots=True)
class SceneTemplateLoaderAdapter(SceneTemplateLoaderPort):
    """Loads scene-template map metadata from JSON store."""

    store: SceneTemplateJsonStore = field(default_factory=SceneTemplateJsonStore)

    def load_map_name(self, path: str) -> str:
        return self.store.load(path).map_name
