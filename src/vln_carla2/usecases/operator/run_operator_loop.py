"""Use case for operator-facing spectator control loop."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from vln_carla2.usecases.operator.ports.follow_vehicle import FollowVehicleProtocol
from vln_carla2.usecases.operator.ports.keyboard_input import KeyboardInputProtocol
from vln_carla2.usecases.operator.ports.move_spectator import MoveSpectatorProtocol


@dataclass(slots=True)
class RunOperatorLoop:
    """
    Operator loop orchestration.

    Order is fixed for each iteration:
    1) keyboard free move
    2) follow override attempt
    3) tick / wait_for_tick
    """

    world: Any
    synchronous_mode: bool
    sleep_seconds: float
    keyboard_input: KeyboardInputProtocol | None = None
    move_spectator: MoveSpectatorProtocol | None = None
    follow_vehicle_topdown: FollowVehicleProtocol | None = None

    def run(self, *, max_ticks: int | None = None) -> int:
        """Run until interrupted or until max_ticks is reached."""
        executed_ticks = 0
        running = True

        while running:
            if max_ticks is not None and executed_ticks >= max_ticks:
                break

            self._handle_keyboard_once()
            self._handle_follow_once()
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

    def _handle_keyboard_once(self) -> None:
        if self.keyboard_input is None or self.move_spectator is None:
            return
        snapshot = self.keyboard_input.read_snapshot()
        self.move_spectator.move(snapshot=snapshot)

    def _handle_follow_once(self) -> None:
        if self.follow_vehicle_topdown is None:
            return
        self.follow_vehicle_topdown.follow_once()
