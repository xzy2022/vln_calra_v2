"""Spectator world port."""

from typing import Protocol


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
