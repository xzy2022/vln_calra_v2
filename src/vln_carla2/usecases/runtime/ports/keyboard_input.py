"""Port for polling one operator keyboard snapshot per loop tick."""

from typing import Protocol

from vln_carla2.usecases.shared.input_snapshot import InputSnapshot


class KeyboardInputProtocol(Protocol):
    """Read one keyboard input snapshot per loop iteration."""

    def read_snapshot(self) -> InputSnapshot:
        ...


