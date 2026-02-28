"""Filesystem adapter for exp-input map metadata lookups."""

from dataclasses import dataclass, field

from vln_carla2.infrastructure.filesystem.episode_spec_json_store import EpisodeSpecJsonStore
from vln_carla2.infrastructure.filesystem.scene_template_json_store import SceneTemplateJsonStore
from vln_carla2.usecases.cli.ports.scene_template_loader import SceneTemplateLoaderPort


@dataclass(slots=True)
class SceneTemplateLoaderAdapter(SceneTemplateLoaderPort):
    """Loads map metadata from scene-template or episode-spec JSON."""

    store: SceneTemplateJsonStore = field(default_factory=SceneTemplateJsonStore)
    episode_store: EpisodeSpecJsonStore = field(default_factory=EpisodeSpecJsonStore)

    def load_map_name(self, path: str) -> str:
        try:
            return self.store.load(path).map_name
        except Exception:
            episode_spec = self.episode_store.load(path)
            scene_json_path = self.episode_store.resolve_scene_json_path(
                episode_spec=episode_spec,
                episode_spec_path=path,
            )
            return self.store.load(scene_json_path).map_name
