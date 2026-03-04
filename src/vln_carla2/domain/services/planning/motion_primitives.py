"""Forward-only motion primitives for hybrid A* search."""

from __future__ import annotations

import math
from dataclasses import dataclass

from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.domain.services.planning.heuristics import normalize_yaw_deg


@dataclass(frozen=True, slots=True)
class ForwardMotionPrimitive:
    """One forward motion primitive in body frame."""

    step_m: float
    delta_yaw_deg: float

    def __post_init__(self) -> None:
        step_m = float(self.step_m)
        delta_yaw_deg = float(self.delta_yaw_deg)
        if step_m <= 0.0:
            raise ValueError("motion primitive step_m must be > 0")
        object.__setattr__(self, "step_m", step_m)
        object.__setattr__(self, "delta_yaw_deg", delta_yaw_deg)


def build_forward_motion_primitives(
    *,
    step_m: float = 1.0,
    turn_delta_deg: float = 15.0,
) -> tuple[ForwardMotionPrimitive, ...]:
    """Build straight/left/right forward primitives."""
    if step_m <= 0.0:
        raise ValueError("step_m must be > 0")
    if turn_delta_deg < 0.0:
        raise ValueError("turn_delta_deg must be >= 0")

    return (
        ForwardMotionPrimitive(step_m=step_m, delta_yaw_deg=0.0),
        ForwardMotionPrimitive(step_m=step_m, delta_yaw_deg=turn_delta_deg),
        ForwardMotionPrimitive(step_m=step_m, delta_yaw_deg=-turn_delta_deg),
    )


def apply_forward_motion(
    *,
    pose: Pose2D,
    primitive: ForwardMotionPrimitive,
) -> Pose2D:
    """Apply one forward primitive with midpoint heading approximation."""
    next_yaw_deg = normalize_yaw_deg(pose.yaw_deg + primitive.delta_yaw_deg)
    mid_yaw_rad = math.radians(pose.yaw_deg + 0.5 * primitive.delta_yaw_deg)

    next_x = pose.x + primitive.step_m * math.cos(mid_yaw_rad)
    next_y = pose.y + primitive.step_m * math.sin(mid_yaw_rad)
    return Pose2D(x=next_x, y=next_y, yaw_deg=next_yaw_deg)

