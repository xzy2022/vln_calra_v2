from dataclasses import dataclass

import pytest

from vln_carla2.domain.model.scene_template import SceneTemplate
from vln_carla2.infrastructure.filesystem.scene_template_loader_adapter import (
    SceneTemplateLoaderAdapter,
)


@dataclass
class _FakeSceneStore:
    template: SceneTemplate | None = None
    error: Exception | None = None
    calls: list[str] | None = None
    fail_paths: set[str] | None = None

    def load(self, path: str) -> SceneTemplate:
        if self.calls is not None:
            self.calls.append(path)
        if self.error is not None and (
            self.fail_paths is None or path in self.fail_paths
        ):
            raise self.error
        if self.template is None:
            raise RuntimeError("missing template")
        return self.template


@dataclass
class _FakeEpisodeStore:
    error: Exception | None = None
    load_calls: list[str] | None = None
    resolve_calls: list[str] | None = None

    def load(self, path: str):
        if self.load_calls is not None:
            self.load_calls.append(path)
        if self.error is not None:
            raise self.error
        return object()

    def resolve_scene_json_path(self, *, episode_spec, episode_spec_path: str) -> str:
        del episode_spec
        if self.resolve_calls is not None:
            self.resolve_calls.append(episode_spec_path)
        return "resolved/scene.json"


def _template(map_name: str) -> SceneTemplate:
    return SceneTemplate(schema_version=1, map_name=map_name, objects=tuple())


def test_loader_reads_map_name_from_scene_template_path() -> None:
    scene_store = _FakeSceneStore(template=_template("Town10HD_Opt"), calls=[])
    episode_store = _FakeEpisodeStore(load_calls=[], resolve_calls=[])
    adapter = SceneTemplateLoaderAdapter(store=scene_store, episode_store=episode_store)

    got = adapter.load_map_name("artifacts/scene.json")

    assert got == "Town10HD_Opt"
    assert scene_store.calls == ["artifacts/scene.json"]
    assert episode_store.load_calls == []
    assert episode_store.resolve_calls == []


def test_loader_falls_back_to_episode_spec_and_resolved_scene_path() -> None:
    scene_store = _FakeSceneStore(
        template=_template("Town10HD_Opt"),
        error=ValueError("scene template map_name must be non-empty string"),
        calls=[],
        fail_paths={"datasets/ep_000001/episode_spec.json"},
    )
    episode_store = _FakeEpisodeStore(load_calls=[], resolve_calls=[])
    adapter = SceneTemplateLoaderAdapter(store=scene_store, episode_store=episode_store)

    got = adapter.load_map_name("datasets/ep_000001/episode_spec.json")

    assert got == "Town10HD_Opt"
    assert scene_store.calls == [
        "datasets/ep_000001/episode_spec.json",
        "resolved/scene.json",
    ]
    assert episode_store.load_calls == ["datasets/ep_000001/episode_spec.json"]
    assert episode_store.resolve_calls == ["datasets/ep_000001/episode_spec.json"]


def test_loader_raises_when_scene_and_episode_inputs_are_both_invalid() -> None:
    scene_store = _FakeSceneStore(error=RuntimeError("scene parse failed"), calls=[])
    episode_store = _FakeEpisodeStore(
        error=ValueError("episode parse failed"),
        load_calls=[],
        resolve_calls=[],
    )
    adapter = SceneTemplateLoaderAdapter(store=scene_store, episode_store=episode_store)

    with pytest.raises(ValueError, match="episode parse failed"):
        adapter.load_map_name("broken.json")
