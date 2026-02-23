"""CARLA-backed clock adapter."""

from typing import Any

from vln_carla2.usecases.ports.clock import Clock


class CarlaClock(Clock):
    """Advance CARLA world by one synchronized tick."""

    def __init__(self, world: Any) -> None:
        self._world = world

    def tick(self) -> int:
        return int(self._world.tick())

