from pathlib import Path

import pytest

from vln_carla2.domain.model.episode_spec import EpisodeSpec, EpisodeTransform
from vln_carla2.infrastructure.filesystem.episode_spec_json_store import EpisodeSpecJsonStore


CASE_ROOT = Path(".tmp_test_artifacts") / "episode_spec_json_store"


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


def _spec() -> EpisodeSpec:
    return EpisodeSpec(
        schema_version=1,
        episode_id="ep_000001",
        scene_json_path="scene.json",
        start_transform=EpisodeTransform(x=1.0, y=2.0, z=0.1, yaw=180.0),
        goal_transform=EpisodeTransform(x=10.0, y=20.0, z=0.1, yaw=0.0),
        instruction="",
        max_steps=500,
        seed=123,
    )


def test_episode_spec_json_store_save_and_load_roundtrip() -> None:
    case_dir = _case_dir("roundtrip")
    store = EpisodeSpecJsonStore(cwd=case_dir)
    target = case_dir / "episode_spec.json"

    save_path = store.save(_spec(), str(target))
    got = store.load(save_path)

    assert Path(save_path) == target
    assert got == _spec()


def test_episode_spec_json_store_resolves_scene_json_path_relative_to_spec() -> None:
    case_dir = _case_dir("resolve_scene")
    store = EpisodeSpecJsonStore(cwd=case_dir)
    spec_path = case_dir / "episodes" / "ep_000001" / "episode_spec.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    scene_rel = Path("..") / ".." / "scene_exports" / "scene_out.json"
    spec = EpisodeSpec(
        schema_version=1,
        episode_id="ep_000001",
        scene_json_path=str(scene_rel),
        start_transform=EpisodeTransform(x=0.0, y=0.0, z=0.0, yaw=0.0),
        goal_transform=EpisodeTransform(x=1.0, y=1.0, z=0.0, yaw=0.0),
        instruction="",
        max_steps=500,
        seed=123,
    )
    store.save(spec, str(spec_path))

    resolved = store.resolve_scene_json_path(
        episode_spec=spec,
        episode_spec_path=str(spec_path),
    )

    assert Path(resolved) == (spec_path.parent / scene_rel).resolve()


def test_episode_spec_json_store_rejects_invalid_payload_shape() -> None:
    case_dir = _case_dir("invalid_payload")
    target = case_dir / "episode_spec.json"
    target.write_text(
        '{"schema_version": 1, "episode_id": "ep", "scene_json_path": "scene.json", '
        '"instruction": "", "max_steps": 500, "seed": 123}'
    )
    store = EpisodeSpecJsonStore(cwd=case_dir)

    with pytest.raises(ValueError, match="episode spec start_transform must be object"):
        store.load(str(target))
