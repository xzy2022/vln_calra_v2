from datetime import datetime
from pathlib import Path

import pytest

from vln_carla2.domain.model.scene_template import (
    SceneObject,
    SceneObjectKind,
    ScenePose,
    SceneTemplate,
)
from vln_carla2.infrastructure.filesystem.scene_template_json_store import SceneTemplateJsonStore


CASE_ROOT = Path(".tmp_test_artifacts") / "scene_template_json_store"


def _remove_tree(path: Path) -> None:
    if not path.exists():
        return
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    path.rmdir()


@pytest.fixture(autouse=True)
def _cleanup_case_root() -> None:
    _remove_tree(CASE_ROOT)
    yield
    _remove_tree(CASE_ROOT)


def _case_dir(name: str) -> Path:
    case_dir = CASE_ROOT / name
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


def _template() -> SceneTemplate:
    return SceneTemplate.from_iterable(
        schema_version=1,
        map_name="Town10HD_Opt",
        objects=[
            SceneObject(
                kind=SceneObjectKind.VEHICLE,
                blueprint_id="vehicle.tesla.model3",
                role_name="ego",
                pose=ScenePose(x=1.0, y=2.0, z=0.1, yaw=180.0),
            )
        ],
    )


def test_scene_template_json_store_save_and_load_roundtrip() -> None:
    case_dir = _case_dir("roundtrip")
    store = SceneTemplateJsonStore(cwd=case_dir)
    expected = _template()
    target = case_dir / "scene.json"

    save_path = store.save(expected, str(target))
    got = store.load(save_path)

    assert Path(save_path) == target
    assert got == expected


def test_scene_template_json_store_uses_default_timestamp_filename() -> None:
    case_dir = _case_dir("default_name")
    fixed = datetime(2026, 2, 26, 12, 30, 45)
    store = SceneTemplateJsonStore(now_fn=lambda: fixed, cwd=case_dir)

    first = store.save(_template(), None)
    second = store.save(_template(), None)

    assert Path(first).name == "scene_export_20260226_123045.json"
    assert Path(second).name == "scene_export_20260226_123045_01.json"


def test_scene_template_json_store_rejects_invalid_json() -> None:
    case_dir = _case_dir("invalid_json")
    target = case_dir / "broken.json"
    target.write_text("{not-json", encoding="utf-8")
    store = SceneTemplateJsonStore(cwd=case_dir)

    with pytest.raises(ValueError, match="invalid scene template json"):
        store.load(str(target))


def test_scene_template_json_store_requires_valid_payload_shape() -> None:
    case_dir = _case_dir("payload_shape")
    target = case_dir / "broken.json"
    target.write_text('{"schema_version": 1, "map_name": "Town10HD_Opt", "objects": [42]}')
    store = SceneTemplateJsonStore(cwd=case_dir)

    with pytest.raises(ValueError, match="scene object must be object"):
        store.load(str(target))
