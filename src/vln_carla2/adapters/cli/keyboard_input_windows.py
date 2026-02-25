"""Windows keyboard polling adapter for spectator movement."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
from typing import Any

from vln_carla2.usecases.spectator.input_snapshot import InputSnapshot

VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_ADD = 0x6B
VK_SUBTRACT = 0x6D
VK_OEM_PLUS = 0xBB
VK_OEM_MINUS = 0xBD


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
