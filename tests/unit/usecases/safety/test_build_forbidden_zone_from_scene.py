import pytest

from vln_carla2.domain.model.forbidden_zone import ForbiddenZone
from vln_carla2.domain.model.point2d import Point2D
from vln_carla2.domain.model.scene_template import (
    SceneObject,
    SceneObjectKind,
    ScenePose,
    SceneTemplate,
)
from vln_carla2.usecases.scene.build_forbidden_zone_from_scene import (
    BuildForbiddenZoneFromScene,
)


class _FakeSceneLoader:
    def __init__(self, template: SceneTemplate) -> None:
        self.template = template
        self.calls: list[str] = []

    def load(self, path: str) -> SceneTemplate:
        self.calls.append(path)
        return self.template


class _FakeBuilder:
    def __init__(self, zone: ForbiddenZone) -> None:
        self.zone = zone
        self.calls: list[list[tuple[float, float]]] = []

    def build(self, obstacle_points):
        points = [(point.x, point.y) for point in obstacle_points]
        self.calls.append(points)
        return self.zone


def _template(*, map_name: str = "Town10HD_Opt", schema_version: int = 1) -> SceneTemplate:
    return SceneTemplate.from_iterable(
        schema_version=schema_version,
        map_name=map_name,
        objects=[
            SceneObject(
                kind=SceneObjectKind.VEHICLE,
                blueprint_id="vehicle.tesla.model3",
                role_name="ego",
                pose=ScenePose(x=1.0, y=2.0, z=0.1, yaw=0.0),
            ),
            SceneObject(
                kind=SceneObjectKind.BARREL,
                blueprint_id="static.prop.barrel",
                role_name="barrel",
                pose=ScenePose(x=10.0, y=20.0, z=0.1, yaw=0.0),
            ),
            SceneObject(
                kind=SceneObjectKind.BARREL,
                blueprint_id="static.prop.barrel",
                role_name="barrel",
                pose=ScenePose(x=30.0, y=40.0, z=0.1, yaw=0.0),
            ),
            SceneObject(
                kind=SceneObjectKind.BARREL,
                blueprint_id="static.prop.barrel",
                role_name="barrel",
                pose=ScenePose(x=50.0, y=60.0, z=0.1, yaw=0.0),
            ),
        ],
    )


def _dummy_zone() -> ForbiddenZone:
    return ForbiddenZone(
        vertices=(
            Point2D(x=0.0, y=0.0),
            Point2D(x=1.0, y=0.0),
            Point2D(x=0.0, y=1.0),
        )
    )


def test_run_extracts_barrel_points_and_builds_zone() -> None:
    expected_zone = _dummy_zone()
    loader = _FakeSceneLoader(_template())
    builder = _FakeBuilder(expected_zone)
    usecase = BuildForbiddenZoneFromScene(
        scene_loader=loader,
        zone_builder=builder,
        expected_map_name="Town10HD_Opt",
    )

    got = usecase.run("artifacts/scene_out.json")

    assert got == expected_zone
    assert loader.calls == ["artifacts/scene_out.json"]
    assert builder.calls == [[(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)]]


def test_run_rejects_map_mismatch() -> None:
    usecase = BuildForbiddenZoneFromScene(
        scene_loader=_FakeSceneLoader(_template(map_name="Town05")),
        zone_builder=_FakeBuilder(_dummy_zone()),
        expected_map_name="Town10HD_Opt",
    )

    with pytest.raises(ValueError, match="scene map mismatch"):
        usecase.run("scene.json")


def test_run_rejects_unsupported_schema() -> None:
    usecase = BuildForbiddenZoneFromScene(
        scene_loader=_FakeSceneLoader(_template(schema_version=99)),
        zone_builder=_FakeBuilder(_dummy_zone()),
        expected_map_name="Town10HD_Opt",
    )

    with pytest.raises(ValueError, match="unsupported scene schema version"):
        usecase.run("scene.json")


def test_run_rejects_when_scene_has_no_barrels() -> None:
    template = SceneTemplate.from_iterable(
        schema_version=1,
        map_name="Town10HD_Opt",
        objects=[
            SceneObject(
                kind=SceneObjectKind.VEHICLE,
                blueprint_id="vehicle.tesla.model3",
                role_name="ego",
                pose=ScenePose(x=1.0, y=2.0, z=0.1, yaw=0.0),
            )
        ],
    )
    usecase = BuildForbiddenZoneFromScene(
        scene_loader=_FakeSceneLoader(template),
        zone_builder=_FakeBuilder(_dummy_zone()),
        expected_map_name="Town10HD_Opt",
    )

    with pytest.raises(ValueError, match="no barrel"):
        usecase.run("scene.json")

