"""Runtime port DTO shim re-exporting shared vehicle DTOs."""

from vln_carla2.usecases.shared.vehicle_dto import SpawnVehicleRequest, VehicleDescriptor

__all__ = ["SpawnVehicleRequest", "VehicleDescriptor"]

