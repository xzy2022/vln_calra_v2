"""Use case for moving spectator camera by world-space deltas."""

from __future__ import annotations

from dataclasses import dataclass

from vln_carla2.domain.services.spectator_rules import clamp_z
from vln_carla2.usecases.input_snapshot import InputSnapshot
from vln_carla2.usecases.ports.spectator_world import SpectatorWorld


@dataclass(slots=True)
class MoveSpectator:
    """Read spectator transform, add delta, then write it back."""

    world: SpectatorWorld
    min_z: float | None = None
    max_z: float | None = None

    def __post_init__(self) -> None:
        has_min = self.min_z is not None
        has_max = self.max_z is not None
        if has_min != has_max:
            raise ValueError("min_z and max_z must be both set or both None")

    def move(self, snapshot: InputSnapshot) -> None:
        transform = self.world.get_spectator_transform()
        transform.location.x += snapshot.dx
        transform.location.y += snapshot.dy

        next_z = transform.location.z + snapshot.dz
        if self.min_z is not None and self.max_z is not None:
            next_z = clamp_z(next_z, self.min_z, self.max_z)
        transform.location.z = next_z

        transform.rotation.pitch = -90.0
        transform.rotation.yaw = 0.0
        transform.rotation.roll = 0.0
        self.world.set_spectator_transform(transform)
