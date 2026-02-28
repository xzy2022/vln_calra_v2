"""Domain model for serializable scene templates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class SceneObjectKind(str, Enum):
    """Supported object kinds in scene templates."""

    VEHICLE = "vehicle"
    BARREL = "barrel"
    GOAL_VEHICLE = "_vehicle"


@dataclass(frozen=True, slots=True)
class ScenePose:
    """Pose used by scene-template objects."""

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
class SceneObject:
    """Serializable object in one scene template."""

    kind: SceneObjectKind
    blueprint_id: str
    role_name: str
    pose: ScenePose

    def __post_init__(self) -> None:
        if not self.blueprint_id:
            raise ValueError("SceneObject.blueprint_id must not be empty")
        if not self.role_name:
            raise ValueError("SceneObject.role_name must not be empty")


@dataclass(frozen=True, slots=True)
class SceneTemplate:
    """Scene-template aggregate root."""

    schema_version: int
    map_name: str
    objects: tuple[SceneObject, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version <= 0:
            raise ValueError("SceneTemplate.schema_version must be positive int")
        if not self.map_name:
            raise ValueError("SceneTemplate.map_name must not be empty")
        object.__setattr__(self, "objects", tuple(self.objects))

    @classmethod
    def from_iterable(
        cls,
        *,
        schema_version: int,
        map_name: str,
        objects: Iterable[SceneObject],
    ) -> "SceneTemplate":
        """Construct a template from any iterable of scene objects."""
        return cls(
            schema_version=schema_version,
            map_name=map_name,
            objects=tuple(objects),
        )
