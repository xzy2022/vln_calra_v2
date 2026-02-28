import pytest

from vln_carla2.domain.model.scene_template import SceneObject, SceneObjectKind, ScenePose, SceneTemplate
from vln_carla2.usecases.scene.import_scene_template import ImportSceneTemplate


class _FakeStore:
    def __init__(self, template: SceneTemplate) -> None:
        self.template = template
        self.calls: list[str] = []

    def load(self, path: str) -> SceneTemplate:
        self.calls.append(path)
        return self.template


class _FakeSpawner:
    def __init__(self, *, fail_at_index: int | None = None) -> None:
        self.calls: list[SceneObject] = []
        self._fail_at_index = fail_at_index

    def spawn(self, obj: SceneObject) -> None:
        self.calls.append(obj)
        if self._fail_at_index is not None and len(self.calls) == self._fail_at_index:
            raise RuntimeError("spawn failed")


def _template(*, map_name: str = "Town10HD_Opt") -> SceneTemplate:
    return SceneTemplate.from_iterable(
        schema_version=1,
        map_name=map_name,
        objects=[
            SceneObject(
                kind=SceneObjectKind.VEHICLE,
                blueprint_id="vehicle.tesla.model3",
                role_name="ego",
                pose=ScenePose(x=1.0, y=2.0, z=0.1, yaw=180.0),
            ),
            SceneObject(
                kind=SceneObjectKind.BARREL,
                blueprint_id="static.prop.barrel",
                role_name="barrel",
                pose=ScenePose(x=3.0, y=4.0, z=0.2, yaw=0.0),
            ),
        ],
    )


def test_import_scene_template_loads_and_spawns_in_order() -> None:
    store = _FakeStore(_template())
    spawner = _FakeSpawner()
    usecase = ImportSceneTemplate(
        store=store,
        spawner=spawner,
        expected_map_name="Town10HD_Opt",
    )

    imported = usecase.run("scene.json")

    assert imported == 2
    assert store.calls == ["scene.json"]
    assert [obj.kind for obj in spawner.calls] == [SceneObjectKind.VEHICLE, SceneObjectKind.BARREL]


def test_import_scene_template_rejects_map_mismatch() -> None:
    usecase = ImportSceneTemplate(
        store=_FakeStore(_template(map_name="Town05")),
        spawner=_FakeSpawner(),
        expected_map_name="Town10HD_Opt",
    )

    with pytest.raises(ValueError, match="scene map mismatch"):
        usecase.run("scene.json")


def test_import_scene_template_stops_on_first_spawn_error_without_rollback() -> None:
    spawner = _FakeSpawner(fail_at_index=2)
    usecase = ImportSceneTemplate(
        store=_FakeStore(_template()),
        spawner=spawner,
        expected_map_name="Town10HD_Opt",
    )

    with pytest.raises(RuntimeError, match="spawn failed"):
        usecase.run("scene.json")

    assert len(spawner.calls) == 2

