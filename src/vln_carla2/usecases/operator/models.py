"""Compatibility re-exports for operator DTOs.

Prefer importing from ``vln_carla2.usecases.operator.ports.vehicle_dto``.
"""

from vln_carla2.usecases.operator.ports.vehicle_dto import SpawnVehicleRequest, VehicleDescriptor

__all__ = ["VehicleDescriptor", "SpawnVehicleRequest"]
