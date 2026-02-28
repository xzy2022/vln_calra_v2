"""Domain model for serializable episode specs."""

from __future__ import annotations

from dataclasses import dataclass


EPISODE_SPEC_SCHEMA_V1 = 1


@dataclass(frozen=True, slots=True)
class EpisodeTransform:
    """Transform used by episode spec start/goal markers."""

    x: float
    y: float
    z: float
    yaw: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", float(self.x))
        object.__setattr__(self, "y", float(self.y))
        object.__setattr__(self, "z", float(self.z))
        object.__setattr__(self, "yaw", float(self.yaw))


@dataclass(frozen=True, slots=True)
class EpisodeSpec:
    """Episode metadata for one scene and one instruction run."""

    schema_version: int
    episode_id: str
    scene_json_path: str
    start_transform: EpisodeTransform
    goal_transform: EpisodeTransform
    instruction: str = ""
    max_steps: int = 500
    seed: int = 123

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version <= 0:
            raise ValueError("EpisodeSpec.schema_version must be positive int")
        if not self.episode_id:
            raise ValueError("EpisodeSpec.episode_id must not be empty")
        if not self.scene_json_path:
            raise ValueError("EpisodeSpec.scene_json_path must not be empty")
        if not isinstance(self.instruction, str):
            raise ValueError("EpisodeSpec.instruction must be string")
        if type(self.max_steps) is not int or self.max_steps <= 0:
            raise ValueError("EpisodeSpec.max_steps must be positive int")
        if type(self.seed) is not int:
            raise ValueError("EpisodeSpec.seed must be int")
