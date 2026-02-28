"""Domain representation of vehicle state."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VehicleState:
    """Vehicle state represented with primitive types only."""

    frame: int
    x: float
    y: float
    z: float
    yaw_deg: float
    vx: float
    vy: float
    vz: float
    speed_mps: float
    forbidden_zone_probe_points_xy: tuple[tuple[float, float], ...] = ()
