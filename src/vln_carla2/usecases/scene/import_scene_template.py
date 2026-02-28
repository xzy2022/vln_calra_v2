"""Use case for importing one scene template into current world."""

from __future__ import annotations

from dataclasses import dataclass

from vln_carla2.domain.services.scene_template_rules import (
    assert_map_matches,
    assert_supported_schema,
)
from vln_carla2.usecases.scene.ports.scene_object_spawner import SceneObjectSpawnerPort
from vln_carla2.usecases.scene.ports.scene_template_store import SceneTemplateStorePort


@dataclass(slots=True)
class ImportSceneTemplate:
    """Load scene template and spawn objects sequentially."""

    store: SceneTemplateStorePort
    spawner: SceneObjectSpawnerPort
    expected_map_name: str

    def run(self, path: str) -> int:
        template = self.store.load(path)
        assert_supported_schema(template.schema_version)
        assert_map_matches(
            expected_map_name=self.expected_map_name,
            template_map_name=template.map_name,
        )

        imported = 0
        for obj in template.objects:
            self.spawner.spawn(obj)
            imported += 1
        return imported

