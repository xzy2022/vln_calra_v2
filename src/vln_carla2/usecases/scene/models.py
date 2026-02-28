"""Domain models for scene editor state transitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EditorMode(str, Enum):
    """Scene editor runtime mode."""

    FREE = "free"
    FOLLOW = "follow"


@dataclass(slots=True)
class EditorState:
    """Mutable scene editor runtime state."""

    mode: EditorMode
    follow_vehicle_id: int | None
    follow_z: float

