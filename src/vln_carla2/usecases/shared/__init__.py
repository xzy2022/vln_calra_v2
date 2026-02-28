"""Shared DTOs and lightweight contracts for use-case slices."""

from .input_snapshot import InputSnapshot
from .vehicle_dto import SpawnVehicleRequest, VehicleDescriptor
from .vehicle_ref import VehicleRefInput, VehicleRefScheme

__all__ = [
    "InputSnapshot",
    "VehicleRefInput",
    "VehicleRefScheme",
    "VehicleDescriptor",
    "SpawnVehicleRequest",
]

