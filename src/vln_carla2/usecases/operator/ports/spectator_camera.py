"""Port for spectator camera transform operations."""

from typing import Protocol

from vln_carla2.usecases.ports.spectator_world import SpectatorTransform


class SpectatorCameraPort(Protocol):
    """Read and update spectator transform."""

    def get_spectator_transform(self) -> SpectatorTransform:
        ...

    def set_spectator_transform(self, transform: SpectatorTransform) -> None:
        ...
