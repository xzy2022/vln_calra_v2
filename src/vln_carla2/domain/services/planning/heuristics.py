"""Heuristic utilities for grid/hybrid A* planners."""

from __future__ import annotations

import math


def euclidean_distance_xy(*, x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(float(x2) - float(x1), float(y2) - float(y1))


def normalize_yaw_deg(yaw_deg: float) -> float:
    return (float(yaw_deg) + 180.0) % 360.0 - 180.0


def absolute_yaw_error_deg(*, yaw_deg: float, target_yaw_deg: float) -> float:
    return abs(normalize_yaw_deg(float(target_yaw_deg) - float(yaw_deg)))

