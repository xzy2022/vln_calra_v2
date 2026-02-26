"""Windows keyboard polling adapter for spectator movement."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
from typing import Any

from vln_carla2.usecases.scene_editor.input_snapshot import EditorInputSnapshot
from vln_carla2.usecases.spectator.input_snapshot import InputSnapshot

VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_ADD = 0x6B
VK_SUBTRACT = 0x6D
VK_DIVIDE = 0x6F
VK_OEM_PLUS = 0xBB
VK_OEM_MINUS = 0xBD
VK_OEM_2 = 0xBF


def _load_user32() -> Any | None:
    try:
        return ctypes.windll.user32
    except AttributeError:
        return None


@dataclass(slots=True)
class KeyboardInputWindows:
    """Map key state directly to dx/dy/dz."""

    xy_step: float = 1.0
    z_step: float = 1.0
    _user32: Any | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        self._user32 = _load_user32()

    def read_snapshot(self) -> InputSnapshot:
        if self._user32 is None:
            return InputSnapshot.zero()

        up = self._is_pressed(VK_UP)
        down = self._is_pressed(VK_DOWN)
        left = self._is_pressed(VK_LEFT)
        right = self._is_pressed(VK_RIGHT)
        plus = self._is_pressed(VK_OEM_PLUS) or self._is_pressed(VK_ADD)
        minus = self._is_pressed(VK_OEM_MINUS) or self._is_pressed(VK_SUBTRACT)

        dx = self.xy_step if up and not down else -self.xy_step if down and not up else 0.0
        dy = self.xy_step if right and not left else -self.xy_step if left and not right else 0.0
        dz = self.z_step if plus and not minus else -self.z_step if minus and not plus else 0.0
        return InputSnapshot(dx=dx, dy=dy, dz=dz)

    def _is_pressed(self, vk_code: int) -> bool:
        user32 = self._user32
        if user32 is None:
            return False
        return bool(user32.GetAsyncKeyState(vk_code) & 0x8000)


@dataclass(slots=True)
class SceneEditorKeyboardInputWindows:
    """Map key state to scene editor held/pressed actions."""

    xy_step: float = 1.0
    z_step: float = 1.0
    _user32: Any | None = field(init=False, default=None, repr=False)
    _toggle_down_last_tick: bool = field(init=False, default=False, repr=False)

    def __post_init__(self) -> None:
        self._user32 = _load_user32()

    def read_snapshot(self) -> EditorInputSnapshot:
        if self._user32 is None:
            self._toggle_down_last_tick = False
            return EditorInputSnapshot.zero()

        up = self._is_pressed(VK_UP)
        down = self._is_pressed(VK_DOWN)
        left = self._is_pressed(VK_LEFT)
        right = self._is_pressed(VK_RIGHT)
        plus = self._is_pressed(VK_OEM_PLUS) or self._is_pressed(VK_ADD)
        minus = self._is_pressed(VK_OEM_MINUS) or self._is_pressed(VK_SUBTRACT)
        toggle_down = self._is_pressed(VK_OEM_2) or self._is_pressed(VK_DIVIDE)

        held_dx = self.xy_step if up and not down else -self.xy_step if down and not up else 0.0
        held_dy = self.xy_step if right and not left else -self.xy_step if left and not right else 0.0
        held_dz = self.z_step if plus and not minus else -self.z_step if minus and not plus else 0.0

        pressed_toggle_mode = toggle_down and not self._toggle_down_last_tick
        self._toggle_down_last_tick = toggle_down

        return EditorInputSnapshot(
            held_dx=held_dx,
            held_dy=held_dy,
            held_dz=held_dz,
            pressed_toggle_mode=pressed_toggle_mode,
        )

    def _is_pressed(self, vk_code: int) -> bool:
        user32 = self._user32
        if user32 is None:
            return False
        return bool(user32.GetAsyncKeyState(vk_code) & 0x8000)
