"""Use case for moving spectator camera by world-space deltas."""

from __future__ import annotations

from dataclasses import dataclass

from vln_carla2.usecases.ports.spectator_world import SpectatorWorld


@dataclass(slots=True)
class MoveSpectator:
    """Read spectator transform, add delta, then write it back."""

    world: SpectatorWorld

    def move(self, dx: float, dy: float, dz: float) -> None:
        transform = self.world.get_spectator_transform()
        transform.location.x += dx
        transform.location.y += dy
        transform.location.z += dz
        transform.rotation.pitch = -90.0
        transform.rotation.yaw = 0.0
        transform.rotation.roll = 0.0
        self.world.set_spectator_transform(transform)
