from __future__ import annotations

from contextlib import contextmanager
import json
import shutil
from datetime import datetime
from pathlib import Path
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
from vln_carla2.usecases.tracking.models import TrackingStepTrace

CASE_ROOT = Path(".tmp_test_artifacts") / "tracking_bootstrap"


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


def _case_dir(name: str) -> Path:
    case_dir = CASE_ROOT / name
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


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
        step_traces=(
            TrackingStepTrace(
                step=1,
                frame=100,
                actual_x=1.0,
                actual_y=2.0,
                actual_yaw_deg=0.0,
                actual_speed_mps=3.0,
                target_x=2.0,
                target_y=3.0,
                target_yaw_deg=0.0,
                distance_to_goal_m=10.0,
                yaw_error_deg=5.0,
                target_speed_mps=5.0,
                lookahead_distance_m=3.0,
                throttle=0.2,
                brake=0.0,
                steer=0.1,
            ),
        ),
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

    class FakeFollower:
        def __init__(self, **kwargs: Any) -> None:
            captured["follow_init"] = kwargs

        def follow_once(self) -> bool:
            captured["follow_calls"] = captured.get("follow_calls", 0) + 1
            return True

    class FakeMetricsStore:
        def save(self, metrics_payload: dict[str, object], path: str) -> str:
            captured["metrics_payload"] = dict(metrics_payload)
            captured["metrics_path_arg"] = path
            return f"/abs/{path}"

    class _FakeDateTime:
        @staticmethod
        def now() -> datetime:
            return datetime(2026, 3, 1, 12, 34, 56)

    monkeypatch.setattr(tracking, "SceneTemplateJsonStore", lambda: FakeSceneStore())
    monkeypatch.setattr(tracking, "EpisodeSpecJsonStore", lambda: FakeEpisodeStore())
    monkeypatch.setattr(tracking, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(tracking, "ImportSceneTemplate", FakeImportSceneTemplate)
    monkeypatch.setattr(tracking, "RunTrackingLoop", FakeRunTrackingLoop)
    monkeypatch.setattr(tracking, "FollowVehicleTopDown", FakeFollower)
    monkeypatch.setattr(tracking, "ExpMetricsJsonStore", lambda: FakeMetricsStore())
    monkeypatch.setattr(tracking, "datetime", _FakeDateTime)

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
        bind_spectator=True,
        spectator_z=33.0,
        enable_trajectory_log=True,
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
    assert isinstance(captured["tracking_loop_init"]["clock"], tracking._FollowBoundClock)
    assert captured["follow_init"]["z"] == 33.0
    assert captured["follow_calls"] == 1
    assert (
        Path(captured["metrics_path_arg"]).as_posix()
        == "runs/20260301_123456/results/ep_000001/tracking_metrics.json"
    )
    assert captured["metrics_payload"]["episode_spec_path"] == settings.episode_spec_path
    assert captured["metrics_payload"]["summary"]["executed_steps"] == 12
    assert len(captured["metrics_payload"]["tick_traces"]) == 1
    assert got.selected_vehicle == selected_vehicle
    assert got.imported_objects == 5
    assert got.start_transform == episode_spec.start_transform
    assert got.goal_transform == episode_spec.goal_transform
    assert got.tracking_result == expected_tracking_result
    assert got.metrics_path is not None
    assert (
        Path(got.metrics_path).as_posix()
        == "/abs/runs/20260301_123456/results/ep_000001/tracking_metrics.json"
    )


def test_run_tracking_workflow_uses_tick_log_as_target_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    template = _scene_template()
    fake_world = object()
    selected_vehicle = VehicleDescriptor(
        actor_id=24,
        type_id="vehicle.tesla.model3",
        role_name="ego",
        x=0.0,
        y=0.0,
        z=0.0,
    )
    episode_spec = EpisodeSpec(
        schema_version=1,
        episode_id="ep_000002",
        scene_json_path="scene_out.json",
        start_transform=EpisodeTransform(x=1.0, y=2.0, z=0.1, yaw=0.0),
        goal_transform=EpisodeTransform(x=99.0, y=88.0, z=0.1, yaw=180.0),
        instruction="",
        max_steps=120,
        seed=321,
    )
    expected_tracking_result = TrackingResult(
        executed_steps=2,
        last_frame=2,
        reached_goal=False,
        termination_reason="max_steps",
        final_distance_to_goal_m=1.2,
        final_yaw_error_deg=3.0,
        route_points=(),
        step_traces=(),
    )
    tick_log_path = _case_dir("uses_tick_log_route") / "scene_tick_log.json"
    tick_log_path.write_text(
        json.dumps(
            {
                "map_name": "Town10HD_Opt",
                "tick_traces": [
                    {"x": 4.0, "y": -5.0, "z": 0.12, "yaw_deg": 0.0},
                    {"x": 8.5, "y": -6.0, "z": 0.20, "yaw_deg": 45.0},
                ],
            }
        ),
        encoding="utf-8",
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
            return 3

    class FakeRunTrackingLoop:
        def __init__(self, **kwargs: Any) -> None:
            captured["tracking_loop_init"] = kwargs

        def run(self, request: Any) -> TrackingResult:
            captured["tracking_request"] = request
            return expected_tracking_result

    class FakeMetricsStore:
        def save(self, metrics_payload: dict[str, object], path: str) -> str:
            captured["metrics_payload"] = dict(metrics_payload)
            captured["metrics_path_arg"] = path
            return f"/abs/{path}"

    monkeypatch.setattr(tracking, "SceneTemplateJsonStore", lambda: FakeSceneStore())
    monkeypatch.setattr(tracking, "EpisodeSpecJsonStore", lambda: FakeEpisodeStore())
    monkeypatch.setattr(tracking, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(tracking, "ImportSceneTemplate", FakeImportSceneTemplate)
    monkeypatch.setattr(tracking, "RunTrackingLoop", FakeRunTrackingLoop)
    monkeypatch.setattr(tracking, "ExpMetricsJsonStore", lambda: FakeMetricsStore())
    monkeypatch.setattr(
        tracking,
        "_resolve_control_target_with_retry",
        lambda **_kwargs: selected_vehicle,
    )

    def _fail_if_waypoint_planner_used(_world: Any) -> None:
        raise AssertionError("CarlaWaypointRoutePlannerAdapter should not be used")

    monkeypatch.setattr(tracking, "CarlaWaypointRoutePlannerAdapter", _fail_if_waypoint_planner_used)

    settings = tracking.TrackingRunSettings(
        episode_spec_path="datasets/town10hd_val_v1/episodes/ep_000002/episode_spec.json",
        host="127.0.0.1",
        port=2000,
        control_target=VehicleRefInput(scheme="role", value="ego"),
        max_steps=20,
        enable_trajectory_log=True,
        target_tick_log_path=str(tick_log_path),
    )

    got = tracking.run_tracking_workflow(settings)

    assert isinstance(captured["tracking_loop_init"]["route_planner"], tracking._FixedRoutePlanner)
    assert captured["tracking_request"].goal_x == 8.5
    assert captured["tracking_request"].goal_y == -6.0
    assert captured["tracking_request"].goal_yaw_deg == 45.0
    assert got.goal_transform == EpisodeTransform(x=8.5, y=-6.0, z=0.2, yaw=45.0)
    assert (
        captured["metrics_payload"]["goal_transform"]
        == {"x": 8.5, "y": -6.0, "z": 0.2, "yaw": 45.0}
    )


def test_load_target_route_from_tick_log_rejects_map_mismatch() -> None:
    target = _case_dir("rejects_map_mismatch") / "scene_tick_log.json"
    target.write_text(
        json.dumps(
            {
                "map_name": "Town03",
                "tick_traces": [{"x": 1.0, "y": 2.0, "yaw_deg": 0.0}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="map_name mismatch"):
        tracking._load_target_route_from_tick_log(
            path=str(target),
            expected_map_name="Town10HD_Opt",
            route_max_points=2000,
        )


def test_load_target_route_from_tick_log_rejects_missing_points() -> None:
    target = _case_dir("rejects_missing_points") / "scene_tick_log.json"
    target.write_text(
        json.dumps(
            {
                "map_name": "Town10HD_Opt",
                "tick_traces": [{"frame": 1}, {"yaw_deg": 10.0}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not contain any valid x/y trajectory points"):
        tracking._load_target_route_from_tick_log(
            path=str(target),
            expected_map_name="Town10HD_Opt",
            route_max_points=2000,
        )


def test_load_target_route_from_tick_log_rejects_route_max_points_exceeded(
) -> None:
    target = _case_dir("rejects_route_max_points_exceeded") / "scene_tick_log.json"
    target.write_text(
        json.dumps(
            {
                "map_name": "Town10HD_Opt",
                "tick_traces": [
                    {"x": 1.0, "y": 2.0, "yaw_deg": 0.0},
                    {"x": 2.0, "y": 3.0, "yaw_deg": 0.0},
                    {"x": 3.0, "y": 4.0, "yaw_deg": 0.0},
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="exceeds route_max_points"):
        tracking._load_target_route_from_tick_log(
            path=str(target),
            expected_map_name="Town10HD_Opt",
            route_max_points=2,
        )
