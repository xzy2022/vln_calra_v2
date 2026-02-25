"""Data transfer objects for operator-focused use cases."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VehicleDescriptor:
    """Serializable vehicle snapshot used by list/spawn/resolve use cases."""

    actor_id: int
    type_id: str
    role_name: str
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        if type(self.actor_id) is not int or self.actor_id <= 0:
            raise ValueError("VehicleDescriptor.actor_id must be positive int")
        if not self.type_id:
            raise ValueError("VehicleDescriptor.type_id must not be empty")


@dataclass(frozen=True, slots=True)
class SpawnVehicleRequest:
    """Request payload for spawning one vehicle actor."""

    blueprint_filter: str
    spawn_x: float
    spawn_y: float
    spawn_z: float
    spawn_yaw: float
    role_name: str = "ego"

    def __post_init__(self) -> None:
        if not self.blueprint_filter:
            raise ValueError("SpawnVehicleRequest.blueprint_filter must not be empty")
        if not self.role_name:
            raise ValueError("SpawnVehicleRequest.role_name must not be empty")
