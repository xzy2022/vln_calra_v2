import json
from pathlib import Path

import pytest

from vln_carla2.infrastructure.filesystem.exp_metrics_json_store import ExpMetricsJsonStore


CASE_ROOT = Path(".tmp_test_artifacts") / "exp_metrics_json_store"


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


def test_exp_metrics_json_store_saves_payload_and_creates_directories() -> None:
    case_dir = _case_dir("save")
    store = ExpMetricsJsonStore(cwd=case_dir)

    payload = {
        "episode_spec_path": "datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
        "entered_forbidden_zone": False,
        "final_position_xy": {"x": 10.0, "y": 20.0},
        "goal_position_xy": {"x": 13.0, "y": 24.0},
        "final_to_goal_distance_xy_m": 5.0,
    }
    path = "runs/20260228_161718/results/ep_000001/metrics.json"

    saved_path = store.save(payload, path)
    target = case_dir / path

    assert Path(saved_path) == target
    assert target.exists()

    got = json.loads(target.read_text(encoding="utf-8"))
    assert got["entered_forbidden_zone"] is False
    assert got["final_position_xy"] == {"x": 10.0, "y": 20.0}
    assert got["goal_position_xy"] == {"x": 13.0, "y": 24.0}
    assert got["final_to_goal_distance_xy_m"] == 5.0
