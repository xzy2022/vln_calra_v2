from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Mapping

import pytest

from vln_carla2.usecases.exp.generate_exp_metrics_artifact import (
    ExpMetricsRequest,
    GenerateExpMetricsArtifact,
)


@dataclass
class _FakeMetricsStore:
    calls: list[tuple[Mapping[str, object], str]] = field(default_factory=list)

    def save(self, metrics_payload: Mapping[str, object], path: str) -> str:
        self.calls.append((dict(metrics_payload), path))
        return path


def test_generate_metrics_artifact_computes_distance_and_default_path() -> None:
    store = _FakeMetricsStore()
    usecase = GenerateExpMetricsArtifact(
        store=store,
        now_fn=lambda: datetime(2026, 2, 28, 16, 17, 18),
    )

    result = usecase.run(
        ExpMetricsRequest(
            episode_spec_path="datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
            entered_forbidden_zone=True,
            final_x=14.0,
            final_y=-4.0,
            goal_x=20.0,
            goal_y=4.0,
        )
    )

    assert Path(result.metrics_path).as_posix() == (
        "runs/20260228_161718/results/ep_000001/metrics.json"
    )
    assert result.entered_forbidden_zone is True
    assert result.final_to_goal_distance_xy_m == pytest.approx(10.0)

    payload, saved_path = store.calls[0]
    assert Path(saved_path).as_posix() == "runs/20260228_161718/results/ep_000001/metrics.json"
    assert payload["entered_forbidden_zone"] is True
    assert payload["episode_spec_path"] == (
        "datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json"
    )
    assert payload["final_to_goal_distance_xy_m"] == pytest.approx(10.0)
    assert payload["final_position_xy"] == {"x": 14.0, "y": -4.0}
    assert payload["goal_position_xy"] == {"x": 20.0, "y": 4.0}


def test_generate_metrics_artifact_falls_back_to_episode_spec_stem() -> None:
    store = _FakeMetricsStore()
    usecase = GenerateExpMetricsArtifact(
        store=store,
        now_fn=lambda: datetime(2026, 2, 28, 7, 0, 1),
    )

    result = usecase.run(
        ExpMetricsRequest(
            episode_spec_path="episode_spec.json",
            entered_forbidden_zone=False,
            final_x=0.0,
            final_y=0.0,
            goal_x=3.0,
            goal_y=4.0,
        )
    )

    assert Path(result.metrics_path).as_posix() == (
        "runs/20260228_070001/results/episode_spec/metrics.json"
    )
