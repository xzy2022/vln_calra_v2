"""Use case for generating and saving experiment metrics artifacts."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from vln_carla2.usecases.exp.ports.metrics_store import ExpMetricsStorePort


def _default_now() -> datetime:
    return datetime.now()


@dataclass(frozen=True, slots=True)
class ExpMetricsRequest:
    """Input payload for one exp metrics generation."""

    episode_spec_path: str
    entered_forbidden_zone: bool
    final_x: float
    final_y: float
    goal_x: float
    goal_y: float

    def __post_init__(self) -> None:
        if not self.episode_spec_path or not self.episode_spec_path.strip():
            raise ValueError("episode_spec_path must not be empty")
        object.__setattr__(self, "final_x", float(self.final_x))
        object.__setattr__(self, "final_y", float(self.final_y))
        object.__setattr__(self, "goal_x", float(self.goal_x))
        object.__setattr__(self, "goal_y", float(self.goal_y))


@dataclass(frozen=True, slots=True)
class ExpMetricsResult:
    """Computed metrics plus written artifact location."""

    metrics_path: str
    entered_forbidden_zone: bool
    final_to_goal_distance_xy_m: float


@dataclass(slots=True)
class GenerateExpMetricsArtifact:
    """Compute exp metrics and persist one metrics artifact file."""

    store: ExpMetricsStorePort
    now_fn: Callable[[], datetime] = _default_now
    runs_root: Path = field(default_factory=lambda: Path("runs"))
    metrics_filename: str = "metrics.json"

    def run(self, request: ExpMetricsRequest) -> ExpMetricsResult:
        distance_xy_m = math.hypot(
            request.goal_x - request.final_x,
            request.goal_y - request.final_y,
        )
        output_path = self._resolve_output_path(episode_spec_path=request.episode_spec_path)
        payload: dict[str, object] = {
            "episode_spec_path": request.episode_spec_path,
            "entered_forbidden_zone": request.entered_forbidden_zone,
            "final_position_xy": {
                "x": request.final_x,
                "y": request.final_y,
            },
            "goal_position_xy": {
                "x": request.goal_x,
                "y": request.goal_y,
            },
            "final_to_goal_distance_xy_m": distance_xy_m,
        }
        saved_path = self.store.save(payload, str(output_path))
        return ExpMetricsResult(
            metrics_path=saved_path,
            entered_forbidden_zone=request.entered_forbidden_zone,
            final_to_goal_distance_xy_m=distance_xy_m,
        )

    def _resolve_output_path(self, *, episode_spec_path: str) -> Path:
        run_id = self.now_fn().strftime("%Y%m%d_%H%M%S")
        episode_dir = self._resolve_episode_dir_name(episode_spec_path=episode_spec_path)
        return self.runs_root / run_id / "results" / episode_dir / self.metrics_filename

    def _resolve_episode_dir_name(self, *, episode_spec_path: str) -> str:
        episode_spec = Path(episode_spec_path)
        parent_name = episode_spec.parent.name.strip()
        if parent_name:
            return parent_name
        if episode_spec.stem:
            return episode_spec.stem
        return "episode"
