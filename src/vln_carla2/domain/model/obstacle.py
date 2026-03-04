"""Domain value object for static planning obstacle."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Obstacle:
    """Circular obstacle in world coordinates."""

    x: float
    y: float
    radius_m: float

    def __post_init__(self) -> None:
        x = float(self.x)
        y = float(self.y)
        radius_m = float(self.radius_m)
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("obstacle x/y must be finite numbers")
        if not math.isfinite(radius_m) or radius_m <= 0.0:
            raise ValueError("obstacle radius_m must be > 0")

        object.__setattr__(self, "x", x)
        object.__setattr__(self, "y", y)
        object.__setattr__(self, "radius_m", radius_m)

