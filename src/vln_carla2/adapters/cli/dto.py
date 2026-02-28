"""Adapter-local DTOs used by CLI command parsing."""

from dataclasses import dataclass
from typing import Literal

VehicleRefScheme = Literal["actor", "role", "first"]


@dataclass(frozen=True, slots=True)
class VehicleRefInput:
    scheme: VehicleRefScheme
    value: str | None = None


@dataclass(frozen=True, slots=True)
class SpawnVehicleRequest:
    blueprint_filter: str
    spawn_x: float
    spawn_y: float
    spawn_z: float
    spawn_yaw: float
    role_name: str = "ego"

