"""Pure rules for spawn location calculations."""

from __future__ import annotations


def spawn_z_from_ground(ground_z: float, vehicle_offset: float) -> float:
    """Compute vehicle spawn Z from road ground Z and vertical offset."""
    return float(ground_z) + float(vehicle_offset)
