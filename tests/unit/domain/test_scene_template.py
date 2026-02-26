import pytest

from vln_carla2.domain.model.scene_template import (
    SceneObject,
    SceneObjectKind,
    ScenePose,
    SceneTemplate,
)
from vln_carla2.domain.services.scene_template_rules import (
    SCENE_TEMPLATE_SCHEMA_V1,
    assert_map_matches,
    assert_supported_schema,
)


def test_scene_pose_normalizes_to_float() -> None:
    pose = ScenePose(x=1, y=2, z=3, yaw=180)

    assert pose.x == 1.0
    assert pose.y == 2.0
    assert pose.z == 3.0
    assert pose.yaw == 180.0


def test_scene_object_requires_non_empty_fields() -> None:
    with pytest.raises(ValueError, match="blueprint_id"):
        SceneObject(
            kind=SceneObjectKind.VEHICLE,
            blueprint_id="",
            role_name="ego",
            pose=ScenePose(x=0.0, y=0.0, z=0.0, yaw=0.0),
        )

    with pytest.raises(ValueError, match="role_name"):
        SceneObject(
            kind=SceneObjectKind.VEHICLE,
            blueprint_id="vehicle.tesla.model3",
            role_name="",
            pose=ScenePose(x=0.0, y=0.0, z=0.0, yaw=0.0),
        )


def test_scene_template_from_iterable_converts_to_tuple() -> None:
    obj = SceneObject(
        kind=SceneObjectKind.BARREL,
        blueprint_id="static.prop.barrel",
        role_name="barrel",
        pose=ScenePose(x=1.0, y=2.0, z=0.5, yaw=90.0),
    )
    template = SceneTemplate.from_iterable(
        schema_version=SCENE_TEMPLATE_SCHEMA_V1,
        map_name="Town10HD_Opt",
        objects=[obj],
    )

    assert template.objects == (obj,)


def test_scene_template_requires_positive_schema_and_map_name() -> None:
    with pytest.raises(ValueError, match="schema_version"):
        SceneTemplate(schema_version=0, map_name="Town10HD_Opt", objects=tuple())

    with pytest.raises(ValueError, match="map_name"):
        SceneTemplate(schema_version=1, map_name="", objects=tuple())


def test_assert_supported_schema_rejects_other_versions() -> None:
    assert_supported_schema(SCENE_TEMPLATE_SCHEMA_V1)

    with pytest.raises(ValueError, match="unsupported scene schema version"):
        assert_supported_schema(99)


def test_assert_map_matches_requires_same_map() -> None:
    assert_map_matches(expected_map_name="Town10HD_Opt", template_map_name="Town10HD_Opt")

    with pytest.raises(ValueError, match="scene map mismatch"):
        assert_map_matches(expected_map_name="Town10HD_Opt", template_map_name="Town05")
