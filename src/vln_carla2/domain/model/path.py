"""Domain value object for planned path."""

from __future__ import annotations

from dataclasses import dataclass

from vln_carla2.domain.model.pose2d import Pose2D


@dataclass(frozen=True, slots=True)
class Path:
    """Immutable path represented as ordered poses."""

    poses: tuple[Pose2D, ...]

    def __post_init__(self) -> None:
        if not self.poses:
            raise ValueError("path poses must not be empty")

