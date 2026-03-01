from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from vln_carla2.app.wiring import tracking
from vln_carla2.domain.model.episode_spec import EpisodeSpec, EpisodeTransform
from vln_carla2.domain.model.scene_template import (
    SceneObject,
    SceneObjectKind,
    ScenePose,
    SceneTemplate,
)
from vln_carla2.usecases.runtime.ports.vehicle_dto import VehicleDescriptor
from vln_carla2.usecases.shared.vehicle_ref import VehicleRefInput
from vln_carla2.usecases.tracking.api import TrackingResult


def _scene_template() -> SceneTemplate:
    return SceneTemplate.from_iterable(
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


def test_run_tracking_workflow_wires_dependencies_and_returns_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    template = _scene_template()
    fake_world = object()
    selected_vehicle = VehicleDescriptor(
        actor_id=42,
        type_id="vehicle.tesla.model3",
        role_name="ego",
        x=0.0,
        y=0.0,
        z=0.0,
    )
    expected_tracking_result = TrackingResult(
        executed_steps=12,
        last_frame=12,
        reached_goal=True,
        termination_reason="goal_reached",
        final_distance_to_goal_m=0.4,
        final_yaw_error_deg=2.0,
        route_points=(),
    )
    episode_spec = EpisodeSpec(
        schema_version=1,
        episode_id="ep_000001",
        scene_json_path="scene_out.json",
        start_transform=EpisodeTransform(x=1.0, y=2.0, z=0.1, yaw=0.0),
        goal_transform=EpisodeTransform(x=10.0, y=20.0, z=0.1, yaw=180.0),
        instruction="",
        max_steps=500,
        seed=123,
    )

    class FakeSceneStore:
        def load(self, path: str) -> SceneTemplate:
            captured.setdefault("scene_load_calls", []).append(path)
            return template

    class FakeEpisodeStore:
        def load(self, path: str) -> EpisodeSpec:
            captured["episode_spec_load_path"] = path
            return episode_spec

        def resolve_scene_json_path(
            self,
            *,
            episode_spec: EpisodeSpec,
            episode_spec_path: str,
        ) -> str:
            del episode_spec, episode_spec_path
            return "artifacts/scene_out.json"

    @contextmanager
    def fake_managed_session(config: tracking.CarlaSessionConfig):
        captured["session_config"] = config
        yield SimpleNamespace(world=fake_world)

    class FakeImportSceneTemplate:
        def __init__(self, **kwargs: Any) -> None:
            captured["import_init"] = kwargs

        def run(self, path: str) -> int:
            captured["import_path"] = path
            return 5

    class FakeRunTrackingLoop:
        def __init__(self, **kwargs: Any) -> None:
            captured["tracking_loop_init"] = kwargs

        def run(self, request: Any) -> TrackingResult:
            captured["tracking_request"] = request
            return expected_tracking_result

    monkeypatch.setattr(tracking, "SceneTemplateJsonStore", lambda: FakeSceneStore())
    monkeypatch.setattr(tracking, "EpisodeSpecJsonStore", lambda: FakeEpisodeStore())
    monkeypatch.setattr(tracking, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(tracking, "ImportSceneTemplate", FakeImportSceneTemplate)
    monkeypatch.setattr(tracking, "RunTrackingLoop", FakeRunTrackingLoop)
    def _fake_resolve_control_target_with_retry(**kwargs: Any) -> VehicleDescriptor:
        captured["resolve_kwargs"] = kwargs
        return selected_vehicle

    monkeypatch.setattr(
        tracking,
        "_resolve_control_target_with_retry",
        _fake_resolve_control_target_with_retry,
    )

    settings = tracking.TrackingRunSettings(
        episode_spec_path="datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
        host="127.0.0.1",
        port=2000,
        control_target=VehicleRefInput(scheme="role", value="ego"),
        target_speed_mps=6.0,
        max_steps=None,
    )

    got = tracking.run_tracking_workflow(settings)

    session_config = captured["session_config"]
    assert session_config.map_name == "Town10HD_Opt"
    assert session_config.force_reload_map is True
    assert (
        captured["episode_spec_load_path"]
        == "datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json"
    )
    assert captured["import_path"] == "artifacts/scene_out.json"
    assert captured["resolve_kwargs"]["control_target"] == VehicleRefInput(scheme="role", value="ego")
    assert captured["tracking_request"].vehicle_id.value == 42
    assert captured["tracking_request"].goal_x == 10.0
    assert captured["tracking_request"].goal_y == 20.0
    assert captured["tracking_request"].goal_yaw_deg == 180.0
    assert captured["tracking_request"].target_speed_mps == 6.0
    # max_steps defaults to episode spec when settings.max_steps is None.
    assert captured["tracking_request"].max_steps == 500
    assert got.selected_vehicle == selected_vehicle
    assert got.imported_objects == 5
    assert got.start_transform == episode_spec.start_transform
    assert got.goal_transform == episode_spec.goal_transform
    assert got.tracking_result == expected_tracking_result
