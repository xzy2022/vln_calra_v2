"""Clock port for tracking use case."""

from typing import Protocol


class Clock(Protocol):
    """Ticks simulation and returns current frame."""

    def tick(self) -> int:
        ...

