"""Port for applying spectator movement from operator input."""

from typing import Protocol

from vln_carla2.usecases.shared.input_snapshot import InputSnapshot


class MoveSpectatorProtocol(Protocol):
    """Move spectator based on the read input snapshot."""

    def move(self, snapshot: InputSnapshot) -> None:
        ...


