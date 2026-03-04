from dataclasses import dataclass

from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.domain.model.scene_template import (
    SceneObject,
    SceneObjectKind,
    ScenePose,
    SceneTemplate,
)
from vln_carla2.infrastructure.carla.planning_map_source_adapter import (
    CarlaPlanningMapSourceAdapter,
)


def _scene_template() -> SceneTemplate:
    return SceneTemplate.from_iterable(
        schema_version=1,
        map_name="Town10HD_Opt",
        objects=(
            SceneObject(
                kind=SceneObjectKind.BARREL,
                blueprint_id="static.prop.barrel",
                role_name="barrel",
                pose=ScenePose(x=2.0, y=3.0, z=0.0, yaw=0.0),
            ),
            SceneObject(
                kind=SceneObjectKind.VEHICLE,
                blueprint_id="vehicle.tesla.model3",
                role_name="ego",
                pose=ScenePose(x=0.0, y=0.0, z=0.0, yaw=0.0),
            ),
        ),
    )


@dataclass
class _FakeLocation:
    x: float
    y: float


@dataclass
class _FakeTransform:
    location: _FakeLocation


@dataclass
class _FakeMap:
    spawn_points: tuple[_FakeTransform, ...]

    def get_spawn_points(self) -> tuple[_FakeTransform, ...]:
        return self.spawn_points


@dataclass
class _FakeWorld:
    map_: _FakeMap

    def get_map(self) -> _FakeMap:
        return self.map_


def test_planning_map_source_adapter_collects_obstacles_and_spawn_points() -> None:
    world = _FakeWorld(
        map_=_FakeMap(
            spawn_points=(
                _FakeTransform(location=_FakeLocation(x=-10.0, y=-2.0)),
                _FakeTransform(location=_FakeLocation(x=12.0, y=9.0)),
            )
        )
    )
    adapter = CarlaPlanningMapSourceAdapter(world=world, scene_template=_scene_template())

    seed = adapter.snapshot(
        map_name="Town10HD_Opt",
        start=Pose2D(x=0.0, y=0.0, yaw_deg=0.0),
        goal=Pose2D(x=8.0, y=8.0, yaw_deg=0.0),
    )

    assert seed.map_name == "Town10HD_Opt"
    assert len(seed.obstacles) == 1
    assert seed.obstacles[0].x == 2.0
    assert seed.min_x <= -10.0
    assert seed.max_x >= 12.0
    assert seed.max_y >= 9.0


def test_planning_map_source_adapter_falls_back_without_world_map() -> None:
    class _BrokenWorld:
        def get_map(self) -> _FakeMap:
            raise RuntimeError("map unavailable")

    adapter = CarlaPlanningMapSourceAdapter(world=_BrokenWorld(), scene_template=_scene_template())

    seed = adapter.snapshot(
        map_name="Town10HD_Opt",
        start=Pose2D(x=1.0, y=1.0, yaw_deg=0.0),
        goal=Pose2D(x=2.0, y=2.0, yaw_deg=0.0),
    )

    assert seed.min_x <= 1.0
    assert seed.max_x >= 2.0
    assert seed.min_y <= 1.0
    assert seed.max_y >= 2.0

