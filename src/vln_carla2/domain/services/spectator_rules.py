"""Pure rules for spectator camera behavior."""

from __future__ import annotations


def clamp_z(z: float, min_z: float, max_z: float) -> float:
    """Clamp Z to [min_z, max_z]."""
    if min_z > max_z:
        raise ValueError("min_z must be <= max_z")
    if z < min_z:
        return min_z
    if z > max_z:
        return max_z
    return z

