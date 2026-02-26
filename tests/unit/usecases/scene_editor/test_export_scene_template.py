from dataclasses import dataclass

from vln_carla2.domain.model.scene_template import SceneObject, SceneObjectKind, ScenePose, SceneTemplate
from vln_carla2.usecases.scene_editor.export_scene_template import ExportSceneTemplate


@dataclass
class _FakeRecorder:
    objects: list[SceneObject]

    def snapshot(self) -> list[SceneObject]:
        return list(self.objects)


class _FakeStore:
    def __init__(self) -> None:
        self.calls: list[tuple[SceneTemplate, str | None]] = []

    def save(self, template: SceneTemplate, path: str | None) -> str:
        self.calls.append((template, path))
        return "saved/path.json"


def test_export_scene_template_uses_recorder_snapshot_and_map_name() -> None:
    obj = SceneObject(
        kind=SceneObjectKind.VEHICLE,
        blueprint_id="vehicle.tesla.model3",
        role_name="ego",
        pose=ScenePose(x=1.0, y=2.0, z=0.1, yaw=180.0),
    )
    store = _FakeStore()
    usecase = ExportSceneTemplate(
        store=store,
        recorder=_FakeRecorder(objects=[obj]),
        map_name="Town10HD_Opt",
        export_path="target.json",
    )

    saved_path = usecase.run()

    assert saved_path == "saved/path.json"
    assert len(store.calls) == 1
    template, path = store.calls[0]
    assert path == "target.json"
    assert template.map_name == "Town10HD_Opt"
    assert template.schema_version == 1
    assert template.objects == (obj,)


def test_export_scene_template_allows_runtime_path_override() -> None:
    store = _FakeStore()
    usecase = ExportSceneTemplate(
        store=store,
        recorder=_FakeRecorder(objects=[]),
        map_name="Town10HD_Opt",
        export_path=None,
    )

    usecase.run(path="override.json")

    assert len(store.calls) == 1
    _, path = store.calls[0]
    assert path == "override.json"
