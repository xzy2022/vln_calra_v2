"""Domain pure-pursuit lateral controller used by tracking use case."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PurePursuitController:
    """Pure pursuit steering controller with normalized steering output."""

    wheelbase_m: float = 2.85
    max_steer_angle_deg: float = 70.0

    def __post_init__(self) -> None:
        if self.wheelbase_m <= 0.0:
            raise ValueError("wheelbase_m must be > 0")
        if self.max_steer_angle_deg <= 0.0:
            raise ValueError("max_steer_angle_deg must be > 0")

    def compute_steer(
        self,
        *,
        ego_x: float,
        ego_y: float,
        ego_yaw_deg: float,
        target_x: float,
        target_y: float,
        lookahead_distance_m: float,
    ) -> float:
        """Compute normalized steering command in [-1, 1]."""
        if lookahead_distance_m <= 0.0:
            raise ValueError("lookahead_distance_m must be > 0")

        heading_rad = math.radians(float(ego_yaw_deg))
        target_heading_rad = math.atan2(float(target_y) - float(ego_y), float(target_x) - float(ego_x))
        alpha = _normalize_angle_rad(target_heading_rad - heading_rad)

        curvature = 2.0 * math.sin(alpha) / float(lookahead_distance_m)
        steer_angle_rad = math.atan(self.wheelbase_m * curvature)
        max_steer_angle_rad = math.radians(self.max_steer_angle_deg)
        normalized = steer_angle_rad / max_steer_angle_rad
        return _clamp(normalized, min_value=-1.0, max_value=1.0)


def _normalize_angle_rad(angle_rad: float) -> float:
    wrapped = (angle_rad + math.pi) % (2.0 * math.pi) - math.pi
    return wrapped


def _clamp(value: float, *, min_value: float, max_value: float) -> float:
    return min(max_value, max(min_value, value))

