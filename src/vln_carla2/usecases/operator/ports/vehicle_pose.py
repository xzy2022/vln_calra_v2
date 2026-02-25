"""Port for reading vehicle transforms by actor id."""

from typing import Protocol

from vln_carla2.usecases.ports.spectator_world import SpectatorTransform


class VehiclePosePort(Protocol):
    """Read vehicle transform for one actor id."""

    def get_vehicle_transform(self, actor_id: int) -> SpectatorTransform | None:
        ...
