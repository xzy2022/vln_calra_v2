"""Spectator world port."""

from typing import Protocol

from vln_carla2.domain.model.vehicle_id import VehicleId


class SpectatorLocation(Protocol):
    """Location-like object with mutable XYZ coordinates."""

    x: float
    y: float
    z: float


class SpectatorRotation(Protocol):
    """Rotation-like object with mutable Euler angles."""

    pitch: float
    yaw: float
    roll: float


class SpectatorTransform(Protocol):
    """Transform-like object exposing location and rotation."""

    location: SpectatorLocation
    rotation: SpectatorRotation


class SpectatorWorld(Protocol):
    """Port for spectator transform read/write."""

    def get_spectator_transform(self) -> SpectatorTransform:
        ...

    def set_spectator_transform(self, transform: SpectatorTransform) -> None:
        ...

    def get_vehicle_transform(self, vehicle_id: VehicleId) -> SpectatorTransform | None:
        """Return vehicle transform or None when actor is missing."""
        ...
