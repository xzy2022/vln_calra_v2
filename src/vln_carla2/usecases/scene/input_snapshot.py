"""Input snapshot for scene editor mode orchestration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EditorInputSnapshot:
    """Current tick input including held axes and pressed toggles."""

    held_dx: float = 0.0
    held_dy: float = 0.0
    held_dz: float = 0.0
    held_throttle: float = 0.0
    held_brake: float = 0.0
    held_steer: float = 0.0
    pressed_toggle_mode: bool = False
    pressed_spawn_vehicle: bool = False
    pressed_spawn_barrel: bool = False
    pressed_spawn_goal: bool = False
    pressed_export_scene: bool = False

    @classmethod
    def zero(cls) -> "EditorInputSnapshot":
        return cls(
            held_dx=0.0,
            held_dy=0.0,
            held_dz=0.0,
            held_throttle=0.0,
            held_brake=0.0,
            held_steer=0.0,
            pressed_toggle_mode=False,
            pressed_spawn_vehicle=False,
            pressed_spawn_barrel=False,
            pressed_spawn_goal=False,
            pressed_export_scene=False,
        )
