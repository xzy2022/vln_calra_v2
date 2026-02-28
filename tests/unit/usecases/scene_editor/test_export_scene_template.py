from dataclasses import dataclass
from pathlib import Path

import pytest

from vln_carla2.domain.model.episode_spec import EpisodeSpec
from vln_carla2.domain.model.scene_template import SceneObject, SceneObjectKind, ScenePose, SceneTemplate
from vln_carla2.usecases.scene.export_scene_template import ExportSceneTemplate


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


class _FakeEpisodeSpecStore:
    def __init__(self) -> None:
        self.calls: list[tuple[EpisodeSpec, str | None]] = []

    def save(self, spec: EpisodeSpec, path: str | None) -> str:
        self.calls.append((spec, path))
        return "saved/episode_spec.json"


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


def test_export_scene_template_exports_episode_spec_with_strict_fields() -> None:
    store = _FakeStore()
    episode_store = _FakeEpisodeSpecStore()
    usecase = ExportSceneTemplate(
        store=store,
        recorder=_FakeRecorder(
            objects=[
                SceneObject(
                    kind=SceneObjectKind.VEHICLE,
                    blueprint_id="vehicle.tesla.model3",
                    role_name="ego",
                    pose=ScenePose(x=1.0, y=2.0, z=0.1, yaw=180.0),
                ),
                SceneObject(
                    kind=SceneObjectKind.GOAL_VEHICLE,
                    blueprint_id="vehicle.tesla.model3",
                    role_name="goal",
                    pose=ScenePose(x=10.0, y=20.0, z=0.1, yaw=0.0),
                ),
            ]
        ),
        map_name="Town10HD_Opt",
        export_path="datasets/town10hd_val_v1/episodes/ep_000001/scene.json",
        export_episode_spec=True,
        episode_spec_store=episode_store,
    )

    usecase.run()

    assert len(episode_store.calls) == 1
    spec, spec_path = episode_store.calls[0]
    assert Path(spec_path or "").as_posix() == "saved/episode_spec.json"
    assert spec.schema_version == 1
    assert spec.episode_id == "saved"
    assert spec.scene_json_path == "path.json"
    assert spec.start_transform.x == 1.0
    assert spec.goal_transform.x == 10.0
    assert spec.instruction == ""
    assert spec.max_steps == 500
    assert spec.seed == 123


def test_export_scene_template_requires_unique_goal_object_for_episode_spec() -> None:
    usecase = ExportSceneTemplate(
        store=_FakeStore(),
        recorder=_FakeRecorder(
            objects=[
                SceneObject(
                    kind=SceneObjectKind.VEHICLE,
                    blueprint_id="vehicle.tesla.model3",
                    role_name="ego",
                    pose=ScenePose(x=1.0, y=2.0, z=0.1, yaw=180.0),
                )
            ]
        ),
        map_name="Town10HD_Opt",
        export_episode_spec=True,
        episode_spec_store=_FakeEpisodeSpecStore(),
    )

    with pytest.raises(ValueError, match="requires exactly one goal object"):
        usecase.run()


def test_export_scene_template_requires_unique_ego_for_episode_spec() -> None:
    usecase = ExportSceneTemplate(
        store=_FakeStore(),
        recorder=_FakeRecorder(
            objects=[
                SceneObject(
                    kind=SceneObjectKind.GOAL_VEHICLE,
                    blueprint_id="vehicle.tesla.model3",
                    role_name="goal",
                    pose=ScenePose(x=10.0, y=20.0, z=0.1, yaw=0.0),
                )
            ]
        ),
        map_name="Town10HD_Opt",
        export_episode_spec=True,
        episode_spec_store=_FakeEpisodeSpecStore(),
    )

    with pytest.raises(ValueError, match="requires exactly one role 'ego'"):
        usecase.run()


def test_export_scene_template_uses_env_dir_when_scene_path_is_implicit() -> None:
    episode_store = _FakeEpisodeSpecStore()
    usecase = ExportSceneTemplate(
        store=_FakeStore(),
        recorder=_FakeRecorder(
            objects=[
                SceneObject(
                    kind=SceneObjectKind.VEHICLE,
                    blueprint_id="vehicle.tesla.model3",
                    role_name="ego",
                    pose=ScenePose(x=1.0, y=2.0, z=0.1, yaw=180.0),
                ),
                SceneObject(
                    kind=SceneObjectKind.GOAL_VEHICLE,
                    blueprint_id="vehicle.tesla.model3",
                    role_name="goal",
                    pose=ScenePose(x=10.0, y=20.0, z=0.1, yaw=0.0),
                ),
            ]
        ),
        map_name="Town10HD_Opt",
        export_path=None,
        export_episode_spec=True,
        episode_spec_store=episode_store,
        episode_spec_export_dir="datasets/town10hd_val_v1/episodes/ep_000002",
    )

    usecase.run()

    assert len(episode_store.calls) == 1
    _, spec_path = episode_store.calls[0]
    assert spec_path == str(Path("datasets/town10hd_val_v1/episodes/ep_000002/episode_spec.json"))


def test_export_scene_template_prefers_explicit_scene_path_over_env_dir() -> None:
    episode_store = _FakeEpisodeSpecStore()
    usecase = ExportSceneTemplate(
        store=_FakeStore(),
        recorder=_FakeRecorder(
            objects=[
                SceneObject(
                    kind=SceneObjectKind.VEHICLE,
                    blueprint_id="vehicle.tesla.model3",
                    role_name="ego",
                    pose=ScenePose(x=1.0, y=2.0, z=0.1, yaw=180.0),
                ),
                SceneObject(
                    kind=SceneObjectKind.GOAL_VEHICLE,
                    blueprint_id="vehicle.tesla.model3",
                    role_name="goal",
                    pose=ScenePose(x=10.0, y=20.0, z=0.1, yaw=0.0),
                ),
            ]
        ),
        map_name="Town10HD_Opt",
        export_path="explicit/scene.json",
        export_episode_spec=True,
        episode_spec_store=episode_store,
        episode_spec_export_dir="datasets/town10hd_val_v1/episodes/ep_000003",
    )

    usecase.run()

    assert len(episode_store.calls) == 1
    _, spec_path = episode_store.calls[0]
    assert Path(spec_path or "").as_posix() == "saved/episode_spec.json"

