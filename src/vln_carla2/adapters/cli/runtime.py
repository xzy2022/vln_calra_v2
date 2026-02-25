"""Runtime loop adapter for the stage-0 CLI baseline."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CliRuntime:
    """Minimal loop that only advances CARLA frames."""

    world: Any
    synchronous_mode: bool
    sleep_seconds: float

    def run(self, *, max_ticks: int | None = None) -> int:
        """Run until interrupted or until max_ticks is reached."""
        executed_ticks = 0
        running = True

        while running:
            if max_ticks is not None and executed_ticks >= max_ticks:
                break

            self._tick_once()
            executed_ticks += 1
            if self.synchronous_mode:
                time.sleep(self.sleep_seconds)

        return executed_ticks

    def _tick_once(self) -> int:
        if self.synchronous_mode:
            return int(self.world.tick())

        snapshot = self.world.wait_for_tick()
        return int(snapshot.frame)
