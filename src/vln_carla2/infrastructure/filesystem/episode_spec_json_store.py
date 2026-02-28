"""JSON-backed store for episode specs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, cast

from vln_carla2.domain.model.episode_spec import EpisodeSpec, EpisodeTransform


@dataclass(slots=True)
class EpisodeSpecJsonStore:
    """Read/write EpisodeSpec using one JSON file."""

    cwd: Path = field(default_factory=Path.cwd)

    def load(self, path: str) -> EpisodeSpec:
        target = Path(path)
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except OSError as exc:
            raise RuntimeError(f"failed to read episode spec file: {target}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid episode spec json: {target}") from exc
        return self._parse_spec(payload)

    def save(self, spec: EpisodeSpec, path: str | None) -> str:
        target = Path(path) if path is not None else self.cwd / "episode_spec.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = self._to_payload(spec)
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        target.write_text(text + "\n", encoding="utf-8")
        return str(target)

    def resolve_scene_json_path(
        self,
        *,
        episode_spec: EpisodeSpec,
        episode_spec_path: str,
    ) -> str:
        scene_path = Path(episode_spec.scene_json_path)
        if scene_path.is_absolute():
            return str(scene_path)
        base = Path(episode_spec_path).parent
        return str((base / scene_path).resolve())

    def _parse_spec(self, payload: Any) -> EpisodeSpec:
        if not isinstance(payload, dict):
            raise ValueError("episode spec payload must be object")
        payload_dict = cast(dict[str, object], payload)

        raw_schema = payload_dict.get("schema_version")
        raw_episode_id = payload_dict.get("episode_id")
        raw_scene_json_path = payload_dict.get("scene_json_path")
        raw_start = payload_dict.get("start_transform")
        raw_goal = payload_dict.get("goal_transform")
        raw_instruction = payload_dict.get("instruction")
        raw_max_steps = payload_dict.get("max_steps")
        raw_seed = payload_dict.get("seed")

        if type(raw_schema) is not int:
            raise ValueError("episode spec schema_version must be int")
        if not isinstance(raw_episode_id, str) or not raw_episode_id:
            raise ValueError("episode spec episode_id must be non-empty string")
        if not isinstance(raw_scene_json_path, str) or not raw_scene_json_path:
            raise ValueError("episode spec scene_json_path must be non-empty string")
        if not isinstance(raw_instruction, str):
            raise ValueError("episode spec instruction must be string")
        if type(raw_max_steps) is not int or raw_max_steps <= 0:
            raise ValueError("episode spec max_steps must be positive int")
        if type(raw_seed) is not int:
            raise ValueError("episode spec seed must be int")

        return EpisodeSpec(
            schema_version=raw_schema,
            episode_id=raw_episode_id,
            scene_json_path=raw_scene_json_path,
            start_transform=self._parse_transform(raw_start, "start_transform"),
            goal_transform=self._parse_transform(raw_goal, "goal_transform"),
            instruction=raw_instruction,
            max_steps=raw_max_steps,
            seed=raw_seed,
        )

    def _parse_transform(self, payload: object, key: str) -> EpisodeTransform:
        if not isinstance(payload, dict):
            raise ValueError(f"episode spec {key} must be object")
        payload_dict = cast(dict[str, object], payload)
        return EpisodeTransform(
            x=self._parse_float_field(payload_dict, key="x", parent_key=key),
            y=self._parse_float_field(payload_dict, key="y", parent_key=key),
            z=self._parse_float_field(payload_dict, key="z", parent_key=key),
            yaw=self._parse_float_field(payload_dict, key="yaw", parent_key=key),
        )

    def _parse_float_field(self, payload: Mapping[str, object], *, key: str, parent_key: str) -> float:
        raw_value = payload.get(key)
        if isinstance(raw_value, bool):
            raise ValueError(f"episode spec {parent_key}.{key} must be number")
        if not isinstance(raw_value, (int, float, str)):
            raise ValueError(f"episode spec {parent_key}.{key} must be number")
        try:
            return float(raw_value)
        except ValueError as exc:
            raise ValueError(f"episode spec {parent_key}.{key} must be number") from exc

    def _to_payload(self, spec: EpisodeSpec) -> dict[str, object]:
        return {
            "schema_version": spec.schema_version,
            "episode_id": spec.episode_id,
            "scene_json_path": spec.scene_json_path,
            "start_transform": self._transform_to_payload(spec.start_transform),
            "goal_transform": self._transform_to_payload(spec.goal_transform),
            "instruction": spec.instruction,
            "max_steps": spec.max_steps,
            "seed": spec.seed,
        }

    def _transform_to_payload(self, transform: EpisodeTransform) -> dict[str, float]:
        return {
            "x": transform.x,
            "y": transform.y,
            "z": transform.z,
            "yaw": transform.yaw,
        }
