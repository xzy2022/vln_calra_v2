"""Thin input snapshot for spectator movement."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InputSnapshot:
    """Current frame input for spectator translation deltas."""

    dx: float = 0.0
    dy: float = 0.0
    dz: float = 0.0

    @classmethod
    def zero(cls) -> "InputSnapshot":
        return cls(dx=0.0, dy=0.0, dz=0.0)

