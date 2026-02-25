from dataclasses import dataclass

from vln_carla2.usecases.move_spectator import MoveSpectator


@dataclass
class _Location:
    x: float
    y: float
    z: float


@dataclass
class _Rotation:
    pitch: float
    yaw: float
    roll: float


@dataclass
class _Transform:
    location: _Location
    rotation: _Rotation


class _FakeWorldAdapter:
    def __init__(self, transform: _Transform) -> None:
        self._transform = transform
        self.last_set: _Transform | None = None

    def get_spectator_transform(self) -> _Transform:
        return self._transform

    def set_spectator_transform(self, transform: _Transform) -> None:
        self.last_set = transform
        self._transform = transform


def test_move_spectator_applies_delta_and_lock_top_down_rotation() -> None:
    transform = _Transform(
        location=_Location(x=1.0, y=2.0, z=3.0),
        rotation=_Rotation(pitch=5.0, yaw=90.0, roll=2.0),
    )
    world = _FakeWorldAdapter(transform)
    usecase = MoveSpectator(world=world)

    usecase.move(dx=0.5, dy=-1.5, dz=2.0)

    moved = world.last_set
    assert moved is not None
    assert moved.location.x == 1.5
    assert moved.location.y == 0.5
    assert moved.location.z == 5.0
    assert moved.rotation.pitch == -90.0
    assert moved.rotation.yaw == 0.0
    assert moved.rotation.roll == 0.0

