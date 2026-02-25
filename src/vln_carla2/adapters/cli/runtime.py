"""Runtime loop adapter with free spectator movement."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from vln_carla2.adapters.cli.keyboard_input_windows import KeyboardInputWindows
from vln_carla2.infrastructure.carla.world_adapter import CarlaWorldAdapter
from vln_carla2.usecases.move_spectator import MoveSpectator


@dataclass(slots=True)
class CliRuntime:
    """Tick loop with optional free spectator movement."""

    world: Any
    synchronous_mode: bool
    sleep_seconds: float
    spectator_initial_z: float = 20.0
    spectator_min_z: float = -20.0
    spectator_max_z: float = 120.0
    keyboard_input: KeyboardInputWindows | None = None
    move_spectator: MoveSpectator | None = None
    _world_adapter: CarlaWorldAdapter | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        if hasattr(self.world, "get_spectator"):
            self._world_adapter = CarlaWorldAdapter(self.world)
            if self.move_spectator is None:
                self.move_spectator = MoveSpectator(
                    world=self._world_adapter,
                    min_z=self.spectator_min_z,
                    max_z=self.spectator_max_z,
                )
            if self.keyboard_input is None:
                self.keyboard_input = KeyboardInputWindows()
            self._initialize_spectator_top_down()

    def run(self, *, max_ticks: int | None = None) -> int:
        """Run until interrupted or until max_ticks is reached."""
        executed_ticks = 0
        running = True

        while running:
            if max_ticks is not None and executed_ticks >= max_ticks:
                break

            self._handle_keyboard_once()
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

    def _initialize_spectator_top_down(self) -> None:
        if self._world_adapter is None:
            return
        transform = self._world_adapter.get_spectator_transform()
        transform.location.z = self.spectator_initial_z
        transform.rotation.pitch = -90.0
        transform.rotation.yaw = 0.0
        transform.rotation.roll = 0.0
        self._world_adapter.set_spectator_transform(transform)

    def _handle_keyboard_once(self) -> None:
        if self.keyboard_input is None or self.move_spectator is None:
            return
        snapshot = self.keyboard_input.read_snapshot()
        self.move_spectator.move(snapshot=snapshot)
