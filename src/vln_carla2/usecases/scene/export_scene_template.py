"""Use case for exporting current scene-editor objects to JSON."""

from __future__ import annotations

from dataclasses import dataclass

from vln_carla2.domain.model.scene_template import SceneTemplate
from vln_carla2.domain.services.scene_template_rules import SCENE_TEMPLATE_SCHEMA_V1
from vln_carla2.usecases.scene.ports.scene_object_recorder import (
    SceneObjectRecorderPort,
)
from vln_carla2.usecases.scene.ports.scene_template_store import SceneTemplateStorePort


@dataclass(slots=True)
class ExportSceneTemplate:
    """Export currently recorded scene objects to a template file."""

    store: SceneTemplateStorePort
    recorder: SceneObjectRecorderPort
    map_name: str
    export_path: str | None = None
    schema_version: int = SCENE_TEMPLATE_SCHEMA_V1

    def run(self, *, path: str | None = None) -> str:
        objects = self.recorder.snapshot()
        template = SceneTemplate.from_iterable(
            schema_version=self.schema_version,
            map_name=self.map_name,
            objects=objects,
        )
        save_path = path if path is not None else self.export_path
        return self.store.save(template, save_path)

