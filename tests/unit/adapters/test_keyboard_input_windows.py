from typing import Iterable

from vln_carla2.adapters.cli.keyboard_input_windows import (
    VK_ADD,
    VK_DOWN,
    VK_LEFT,
    VK_OEM_PLUS,
    VK_RIGHT,
    VK_SUBTRACT,
    VK_UP,
    KeyboardInputWindows,
)


class _FakeUser32:
    def __init__(self, pressed: Iterable[int]) -> None:
        self._pressed = set(pressed)

    def GetAsyncKeyState(self, vk_code: int) -> int:
        return 0x8000 if vk_code in self._pressed else 0


def test_keyboard_input_maps_arrow_and_plus_keys() -> None:
    reader = KeyboardInputWindows(xy_step=1.5, z_step=2.0)
    reader._user32 = _FakeUser32({VK_UP, VK_RIGHT, VK_OEM_PLUS})

    dx, dy, dz = reader.read_delta()

    assert dx == 1.5
    assert dy == 1.5
    assert dz == 2.0


def test_keyboard_input_maps_down_left_and_numpad_minus() -> None:
    reader = KeyboardInputWindows(xy_step=1.0, z_step=0.5)
    reader._user32 = _FakeUser32({VK_DOWN, VK_LEFT, VK_SUBTRACT})

    dx, dy, dz = reader.read_delta()

    assert dx == -1.0
    assert dy == -1.0
    assert dz == -0.5


def test_keyboard_input_conflicting_keys_cancel_each_axis() -> None:
    reader = KeyboardInputWindows(xy_step=3.0, z_step=4.0)
    reader._user32 = _FakeUser32({VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT, VK_ADD, VK_SUBTRACT})

    dx, dy, dz = reader.read_delta()

    assert dx == 0.0
    assert dy == 0.0
    assert dz == 0.0

