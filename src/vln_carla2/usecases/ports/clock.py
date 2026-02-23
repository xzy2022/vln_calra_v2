"""Clock port."""

from typing import Protocol


class Clock(Protocol):
    """Ticks the simulation and returns the current frame."""

    def tick(self) -> int:
        """Advance one step."""

