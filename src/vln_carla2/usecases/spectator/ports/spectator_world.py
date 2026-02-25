"""Backward-compatible combined spectator world port.

Prefer using split ports:
- SpectatorCameraPort
- VehiclePosePort
"""

from typing import Protocol

from vln_carla2.usecases.spectator.ports.spectator_camera import SpectatorCameraPort
from vln_carla2.usecases.spectator.ports.vehicle_pose import VehiclePosePort


class SpectatorWorld(SpectatorCameraPort, VehiclePosePort, Protocol):
    """Compatibility protocol combining camera + vehicle pose ports."""

    pass
