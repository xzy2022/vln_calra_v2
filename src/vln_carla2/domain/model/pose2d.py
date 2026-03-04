"""Domain value object for 2D pose (x, y, yaw)."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Pose2D:
    """Immutable 2D pose in meters/degrees."""

    x: float
    y: float
    yaw_deg: float

    def __post_init__(self) -> None:
        x = float(self.x)
        y = float(self.y)
        yaw_deg = float(self.yaw_deg)
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("pose x/y must be finite numbers")
        if not math.isfinite(yaw_deg):
            raise ValueError("pose yaw_deg must be finite number")

        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "yaw_deg", _normalize_yaw_deg(yaw_deg))


def _normalize_yaw_deg(yaw_deg: float) -> float:
    return (yaw_deg + 180.0) % 360.0 - 180.0

