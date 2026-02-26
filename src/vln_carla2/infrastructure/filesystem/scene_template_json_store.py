"""JSON-backed store for scene templates."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, cast

from vln_carla2.domain.model.scene_template import (
    SceneObject,
    SceneObjectKind,
    ScenePose,
    SceneTemplate,
)


def _default_now() -> datetime:
    return datetime.now()


@dataclass(slots=True)
class SceneTemplateJsonStore:
    """Read/write SceneTemplate using one JSON file."""

    now_fn: Callable[[], datetime] = _default_now
    cwd: Path = field(default_factory=Path.cwd)

    def load(self, path: str) -> SceneTemplate:
        target = Path(path)
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except OSError as exc:
            raise RuntimeError(f"failed to read scene template file: {target}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid scene template json: {target}") from exc
        return self._parse_template(payload)

    def save(self, template: SceneTemplate, path: str | None) -> str:
        target = Path(path) if path is not None else self._resolve_default_export_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = self._to_payload(template)
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        target.write_text(text + "\n", encoding="utf-8")
        return str(target)

    def _resolve_default_export_path(self) -> Path:
        timestamp = self.now_fn().strftime("%Y%m%d_%H%M%S")
        stem = f"scene_export_{timestamp}"
        candidate = self.cwd / f"{stem}.json"
        if not candidate.exists():
            return candidate

        index = 1
        while True:
            candidate = self.cwd / f"{stem}_{index:02d}.json"
            if not candidate.exists():
                return candidate
            index += 1

    def _parse_template(self, payload: Any) -> SceneTemplate:
        if not isinstance(payload, dict):
            raise ValueError("scene template payload must be object")
        payload_dict = cast(dict[str, object], payload)

        raw_schema = payload_dict.get("schema_version")
        raw_map = payload_dict.get("map_name")
        raw_objects = payload_dict.get("objects")

        if type(raw_schema) is not int:
            raise ValueError("scene template schema_version must be int")
        if not isinstance(raw_map, str) or not raw_map:
            raise ValueError("scene template map_name must be non-empty string")
        if not isinstance(raw_objects, list):
            raise ValueError("scene template objects must be list")

        raw_objects_list = cast(list[object], raw_objects)
        objects: list[SceneObject] = []
        for item in raw_objects_list:
            objects.append(self._parse_object(item))

        return SceneTemplate.from_iterable(
            schema_version=raw_schema,
            map_name=raw_map,
            objects=objects,
        )

    def _parse_object(self, payload: Any) -> SceneObject:
        if not isinstance(payload, dict):
            raise ValueError("scene object must be object")
        payload_dict = cast(dict[str, object], payload)

        raw_kind = payload_dict.get("kind")
        raw_blueprint = payload_dict.get("blueprint_id")
        raw_role = payload_dict.get("role_name")

        if not isinstance(raw_kind, str):
            raise ValueError("scene object kind must be string")
        kind = SceneObjectKind(raw_kind)
        if not isinstance(raw_blueprint, str) or not raw_blueprint:
            raise ValueError("scene object blueprint_id must be non-empty string")
        if not isinstance(raw_role, str) or not raw_role:
            raise ValueError("scene object role_name must be non-empty string")

        return SceneObject(
            kind=kind,
            blueprint_id=raw_blueprint,
            role_name=raw_role,
            pose=ScenePose(
                x=self._parse_float_field(payload_dict, "x"),
                y=self._parse_float_field(payload_dict, "y"),
                z=self._parse_float_field(payload_dict, "z"),
                yaw=self._parse_float_field(payload_dict, "yaw"),
            ),
        )

    def _parse_float_field(self, payload: Mapping[str, object], key: str) -> float:
        raw_value = payload.get(key)
        if isinstance(raw_value, bool):
            raise ValueError(f"scene object {key} must be number")
        if not isinstance(raw_value, (int, float, str)):
            raise ValueError(f"scene object {key} must be number")
        try:
            return float(raw_value)
        except ValueError as exc:
            raise ValueError(f"scene object {key} must be number") from exc

    def _to_payload(self, template: SceneTemplate) -> dict[str, object]:
        return {
            "schema_version": template.schema_version,
            "map_name": template.map_name,
            "objects": [self._object_to_payload(obj) for obj in template.objects],
        }

    def _object_to_payload(self, obj: SceneObject) -> dict[str, object]:
        return {
            "kind": obj.kind.value,
            "blueprint_id": obj.blueprint_id,
            "role_name": obj.role_name,
            "x": obj.pose.x,
            "y": obj.pose.y,
            "z": obj.pose.z,
            "yaw": obj.pose.yaw,
        }
