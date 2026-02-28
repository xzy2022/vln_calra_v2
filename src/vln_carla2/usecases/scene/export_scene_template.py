"""Use case for exporting current scene-editor objects to JSON."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from vln_carla2.domain.model.episode_spec import (
    EPISODE_SPEC_SCHEMA_V1,
    EpisodeSpec,
    EpisodeTransform,
)
from vln_carla2.domain.model.scene_template import SceneObject, SceneObjectKind, SceneTemplate
from vln_carla2.domain.services.scene_template_rules import SCENE_TEMPLATE_SCHEMA_V1
from vln_carla2.usecases.scene.ports.episode_spec_store import EpisodeSpecStorePort
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
    export_episode_spec: bool = False
    episode_spec_store: EpisodeSpecStorePort | None = None
    episode_spec_export_dir: str | None = None
    episode_spec_schema_version: int = EPISODE_SPEC_SCHEMA_V1
    episode_instruction: str = ""
    episode_max_steps: int = 500
    episode_seed: int = 123

    def run(self, *, path: str | None = None) -> str:
        objects = self.recorder.snapshot()
        template = SceneTemplate.from_iterable(
            schema_version=self.schema_version,
            map_name=self.map_name,
            objects=objects,
        )
        save_path = path if path is not None else self.export_path
        scene_path = self.store.save(template, save_path)
        if not self.export_episode_spec:
            return scene_path

        if self.episode_spec_store is None:
            raise RuntimeError("episode spec export is unavailable in current runtime.")

        spec_path = self._resolve_episode_spec_export_path(
            scene_path=scene_path,
            explicit_scene_path=save_path is not None,
        )
        episode_spec = self._build_episode_spec(
            objects=objects,
            scene_path=scene_path,
            spec_path=spec_path,
        )
        self.episode_spec_store.save(episode_spec, spec_path)
        return scene_path

    def _build_episode_spec(
        self,
        *,
        objects: list[SceneObject],
        scene_path: str,
        spec_path: str,
    ) -> EpisodeSpec:
        ego = self._pick_unique_object(
            objects=objects,
            role_name="ego",
        )
        goal = self._pick_unique_object(
            objects=objects,
            role_name="goal",
            kind=SceneObjectKind.GOAL_VEHICLE,
        )
        scene_file = Path(scene_path)
        spec_file = Path(spec_path)

        scene_json_path = self._scene_path_relative_to_spec(
            scene_file=scene_file,
            spec_file=spec_file,
        )

        return EpisodeSpec(
            schema_version=self.episode_spec_schema_version,
            episode_id=scene_file.parent.name or "episode",
            scene_json_path=scene_json_path,
            start_transform=EpisodeTransform(
                x=ego.pose.x,
                y=ego.pose.y,
                z=ego.pose.z,
                yaw=ego.pose.yaw,
            ),
            goal_transform=EpisodeTransform(
                x=goal.pose.x,
                y=goal.pose.y,
                z=goal.pose.z,
                yaw=goal.pose.yaw,
            ),
            instruction=self.episode_instruction,
            max_steps=self.episode_max_steps,
            seed=self.episode_seed,
        )

    def _pick_unique_object(
        self,
        *,
        objects: list[SceneObject],
        role_name: str,
        kind: SceneObjectKind | None = None,
    ) -> SceneObject:
        candidates = [
            obj
            for obj in objects
            if obj.role_name == role_name and (kind is None or obj.kind is kind)
        ]
        if len(candidates) != 1:
            if kind is None:
                raise ValueError(
                    f"episode spec export requires exactly one role '{role_name}', "
                    f"got {len(candidates)}"
                )
            raise ValueError(
                "episode spec export requires exactly one goal object "
                f"(role='goal' kind='{kind.value}'), got {len(candidates)}"
            )
        return candidates[0]

    def _resolve_episode_spec_export_path(
        self,
        *,
        scene_path: str,
        explicit_scene_path: bool,
    ) -> str:
        scene_file = Path(scene_path)
        if explicit_scene_path:
            return str(scene_file.parent / "episode_spec.json")
        if self.episode_spec_export_dir is not None and self.episode_spec_export_dir.strip():
            return str(Path(self.episode_spec_export_dir) / "episode_spec.json")
        return str(scene_file.parent / "episode_spec.json")

    def _scene_path_relative_to_spec(self, *, scene_file: Path, spec_file: Path) -> str:
        try:
            rel_path = os.path.relpath(scene_file, start=spec_file.parent)
        except ValueError:
            return str(scene_file)
        return str(Path(rel_path))

