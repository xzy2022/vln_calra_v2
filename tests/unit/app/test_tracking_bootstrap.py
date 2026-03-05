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
from vln_carla2.domain.model.forbidden_zone import ForbiddenZone
from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.point2d import Point2D
from vln_carla2.domain.model.scene_template import (
    SceneObject,
    SceneObjectKind,
    ScenePose,
    SceneTemplate,
)
from vln_carla2.usecases.runtime.ports.vehicle_dto import VehicleDescriptor
from vln_carla2.usecases.shared.vehicle_ref import VehicleRefInput
from vln_carla2.usecases.tracking.api import TrackingResult
from vln_carla2.usecases.tracking.models import RoutePoint, TrackingStepTrace

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


def _scene_template_with_barrel() -> SceneTemplate:
    return SceneTemplate.from_iterable(
        schema_version=1,
        map_name="Town10HD_Opt",
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
                role_name="barrel_1",
                pose=ScenePose(x=11.0, y=11.0, z=0.0, yaw=0.0),
            ),
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
    assert "planning_map" not in captured["metrics_payload"]
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


def test_run_tracking_workflow_uses_hybrid_planner_route_adapter(
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
        episode_id="ep_000003",
        scene_json_path="scene_out.json",
        start_transform=EpisodeTransform(x=1.0, y=2.0, z=0.1, yaw=0.0),
        goal_transform=EpisodeTransform(x=9.0, y=4.0, z=0.1, yaw=45.0),
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

    monkeypatch.setattr(tracking, "SceneTemplateJsonStore", lambda: FakeSceneStore())
    monkeypatch.setattr(tracking, "EpisodeSpecJsonStore", lambda: FakeEpisodeStore())
    monkeypatch.setattr(tracking, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(tracking, "ImportSceneTemplate", FakeImportSceneTemplate)
    monkeypatch.setattr(tracking, "RunTrackingLoop", FakeRunTrackingLoop)
    monkeypatch.setattr(
        tracking,
        "_resolve_control_target_with_retry",
        lambda **_kwargs: selected_vehicle,
    )

    def _fail_if_waypoint_planner_used(_world: Any) -> None:
        raise AssertionError("CarlaWaypointRoutePlannerAdapter should not be used")

    monkeypatch.setattr(tracking, "CarlaWaypointRoutePlannerAdapter", _fail_if_waypoint_planner_used)

    settings = tracking.TrackingRunSettings(
        episode_spec_path="datasets/town10hd_val_v1/episodes/ep_000003/episode_spec.json",
        host="127.0.0.1",
        port=2000,
        control_target=VehicleRefInput(scheme="role", value="ego"),
        max_steps=20,
        planner="hybrid_forward",
    )

    tracking.run_tracking_workflow(settings)

    assert isinstance(
        captured["tracking_loop_init"]["route_planner"],
        tracking.PlanningApiRoutePlannerAdapter,
    )


def test_run_tracking_workflow_hybrid_trajectory_log_includes_local_planning_map(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    template = _scene_template_with_barrel()
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
        episode_id="ep_000003",
        scene_json_path="scene_out.json",
        start_transform=EpisodeTransform(x=1.0, y=2.0, z=0.1, yaw=0.0),
        goal_transform=EpisodeTransform(x=9.0, y=4.0, z=0.1, yaw=45.0),
        instruction="",
        max_steps=120,
        seed=321,
    )
    expected_tracking_result = TrackingResult(
        executed_steps=3,
        last_frame=3,
        reached_goal=False,
        termination_reason="max_steps",
        final_distance_to_goal_m=2.0,
        final_yaw_error_deg=5.0,
        route_points=(
            RoutePoint(x=12.0, y=12.0, yaw_deg=0.0),
            RoutePoint(x=13.0, y=13.0, yaw_deg=0.0),
        ),
        step_traces=(),
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

    class FakeHybridRoutePlanner:
        def __init__(self, **kwargs: Any) -> None:
            captured["hybrid_planner_init"] = kwargs
            self.last_planning_map = PlanningMap(
                map_name="Town10HD_Opt",
                resolution_m=1.0,
                min_x=0.0,
                max_x=100.0,
                min_y=0.0,
                max_y=100.0,
                width=100,
                height=100,
                occupied_cells=((15, 15), (90, 90)),
            )

        def plan_route(self, **_kwargs: Any) -> tuple[RoutePoint, ...]:
            return expected_tracking_result.route_points

    monkeypatch.setattr(tracking, "SceneTemplateJsonStore", lambda: FakeSceneStore())
    monkeypatch.setattr(tracking, "EpisodeSpecJsonStore", lambda: FakeEpisodeStore())
    monkeypatch.setattr(tracking, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(tracking, "ImportSceneTemplate", FakeImportSceneTemplate)
    monkeypatch.setattr(tracking, "RunTrackingLoop", FakeRunTrackingLoop)
    monkeypatch.setattr(tracking, "ExpMetricsJsonStore", lambda: FakeMetricsStore())
    monkeypatch.setattr(tracking, "PlanningApiRoutePlannerAdapter", FakeHybridRoutePlanner)
    monkeypatch.setattr(
        tracking,
        "_resolve_control_target_with_retry",
        lambda **_kwargs: selected_vehicle,
    )

    def _fail_if_waypoint_planner_used(_world: Any) -> None:
        raise AssertionError("CarlaWaypointRoutePlannerAdapter should not be used")

    monkeypatch.setattr(tracking, "CarlaWaypointRoutePlannerAdapter", _fail_if_waypoint_planner_used)

    settings = tracking.TrackingRunSettings(
        episode_spec_path="datasets/town10hd_val_v1/episodes/ep_000003/episode_spec.json",
        host="127.0.0.1",
        port=2000,
        control_target=VehicleRefInput(scheme="role", value="ego"),
        max_steps=20,
        planner="hybrid_forward",
        enable_trajectory_log=True,
    )

    tracking.run_tracking_workflow(settings)

    assert isinstance(captured["tracking_loop_init"]["route_planner"], FakeHybridRoutePlanner)
    planning_map_payload = captured["metrics_payload"]["planning_map"]
    assert planning_map_payload["planner"] == "hybrid_forward"
    assert planning_map_payload["scope"] == "episode_local"
    assert planning_map_payload["resolution_m"] == 1.0
    assert planning_map_payload["origin_x"] == pytest.approx(0.0)
    assert planning_map_payload["origin_y"] == pytest.approx(0.0)
    assert planning_map_payload["width"] == 24
    assert planning_map_payload["height"] == 24
    assert planning_map_payload["occupied_cells"] == [[15, 15]]
    assert planning_map_payload["obstacles"] == [
        {"x": 11.0, "y": 11.0, "radius_m": 0.5}
    ]
    assert planning_map_payload["bounds"] == {
        "min_x": 0.0,
        "max_x": 24.0,
        "min_y": 0.0,
        "max_y": 24.0,
    }


def test_run_tracking_workflow_hybrid_embed_forbidden_zone_wires_and_logs_vertices(
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
        episode_id="ep_000003",
        scene_json_path="scene_out.json",
        start_transform=EpisodeTransform(x=1.0, y=2.0, z=0.1, yaw=0.0),
        goal_transform=EpisodeTransform(x=9.0, y=4.0, z=0.1, yaw=45.0),
        instruction="",
        max_steps=120,
        seed=321,
    )
    expected_tracking_result = TrackingResult(
        executed_steps=3,
        last_frame=3,
        reached_goal=False,
        termination_reason="max_steps",
        final_distance_to_goal_m=2.0,
        final_yaw_error_deg=5.0,
        route_points=(
            RoutePoint(x=12.0, y=12.0, yaw_deg=0.0),
            RoutePoint(x=13.0, y=13.0, yaw_deg=0.0),
        ),
        step_traces=(),
    )
    forbidden_zone = ForbiddenZone(
        vertices=(
            Point2D(x=8.0, y=8.0),
            Point2D(x=14.0, y=8.0),
            Point2D(x=12.0, y=14.0),
        )
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

    class FakeForbiddenZoneFromScene:
        def __init__(self, **kwargs: Any) -> None:
            captured["forbidden_zone_builder_init"] = kwargs

        def run(self, scene_json_path: str) -> ForbiddenZone:
            captured["forbidden_zone_scene_json_path"] = scene_json_path
            return forbidden_zone

    class FakeHybridRoutePlanner:
        def __init__(self, **kwargs: Any) -> None:
            captured["hybrid_planner_init"] = kwargs
            self.last_planning_map = PlanningMap(
                map_name="Town10HD_Opt",
                resolution_m=1.0,
                min_x=0.0,
                max_x=100.0,
                min_y=0.0,
                max_y=100.0,
                width=100,
                height=100,
                occupied_cells=((15, 15),),
            )

        def plan_route(self, **_kwargs: Any) -> tuple[RoutePoint, ...]:
            return expected_tracking_result.route_points

    monkeypatch.setattr(tracking, "SceneTemplateJsonStore", lambda: FakeSceneStore())
    monkeypatch.setattr(tracking, "EpisodeSpecJsonStore", lambda: FakeEpisodeStore())
    monkeypatch.setattr(tracking, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(tracking, "ImportSceneTemplate", FakeImportSceneTemplate)
    monkeypatch.setattr(tracking, "RunTrackingLoop", FakeRunTrackingLoop)
    monkeypatch.setattr(tracking, "ExpMetricsJsonStore", lambda: FakeMetricsStore())
    monkeypatch.setattr(tracking, "BuildForbiddenZoneFromScene", FakeForbiddenZoneFromScene)
    monkeypatch.setattr(tracking, "PlanningApiRoutePlannerAdapter", FakeHybridRoutePlanner)
    monkeypatch.setattr(
        tracking,
        "_resolve_control_target_with_retry",
        lambda **_kwargs: selected_vehicle,
    )

    def _fail_if_waypoint_planner_used(_world: Any) -> None:
        raise AssertionError("CarlaWaypointRoutePlannerAdapter should not be used")

    monkeypatch.setattr(tracking, "CarlaWaypointRoutePlannerAdapter", _fail_if_waypoint_planner_used)

    settings = tracking.TrackingRunSettings(
        episode_spec_path="datasets/town10hd_val_v1/episodes/ep_000003/episode_spec.json",
        host="127.0.0.1",
        port=2000,
        control_target=VehicleRefInput(scheme="role", value="ego"),
        max_steps=20,
        planner="hybrid_forward",
        enable_trajectory_log=True,
        embed_forbidden_zone=True,
    )

    tracking.run_tracking_workflow(settings)

    assert isinstance(captured["tracking_loop_init"]["route_planner"], FakeHybridRoutePlanner)
    assert captured["forbidden_zone_scene_json_path"] == "artifacts/scene_out.json"
    assert captured["hybrid_planner_init"]["forbidden_zone"] == forbidden_zone
    planning_map_payload = captured["metrics_payload"]["planning_map"]
    assert planning_map_payload["forbidden_zone"]["source"] == "scene_barrel_convex_hull"
    assert planning_map_payload["forbidden_zone"]["vertices"] == [
        {"x": 8.0, "y": 8.0},
        {"x": 14.0, "y": 8.0},
        {"x": 12.0, "y": 14.0},
    ]


def test_run_tracking_workflow_hybrid_embed_forbidden_zone_build_failure_raises(
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
        episode_id="ep_000003",
        scene_json_path="scene_out.json",
        start_transform=EpisodeTransform(x=1.0, y=2.0, z=0.1, yaw=0.0),
        goal_transform=EpisodeTransform(x=9.0, y=4.0, z=0.1, yaw=45.0),
        instruction="",
        max_steps=120,
        seed=321,
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

    class FailingForbiddenZoneFromScene:
        def __init__(self, **kwargs: Any) -> None:
            captured["forbidden_zone_builder_init"] = kwargs

        def run(self, scene_json_path: str) -> ForbiddenZone:
            del scene_json_path
            raise ValueError("at least 3 unique obstacle points are required")

    monkeypatch.setattr(tracking, "SceneTemplateJsonStore", lambda: FakeSceneStore())
    monkeypatch.setattr(tracking, "EpisodeSpecJsonStore", lambda: FakeEpisodeStore())
    monkeypatch.setattr(tracking, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(tracking, "ImportSceneTemplate", FakeImportSceneTemplate)
    monkeypatch.setattr(tracking, "BuildForbiddenZoneFromScene", FailingForbiddenZoneFromScene)
    monkeypatch.setattr(
        tracking,
        "_resolve_control_target_with_retry",
        lambda **_kwargs: selected_vehicle,
    )

    settings = tracking.TrackingRunSettings(
        episode_spec_path="datasets/town10hd_val_v1/episodes/ep_000003/episode_spec.json",
        host="127.0.0.1",
        port=2000,
        control_target=VehicleRefInput(scheme="role", value="ego"),
        max_steps=20,
        planner="hybrid_forward",
        embed_forbidden_zone=True,
    )

    with pytest.raises(ValueError, match="at least 3 unique obstacle points are required"):
        tracking.run_tracking_workflow(settings)


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


def test_tracking_run_settings_rejects_planner_with_target_tick_log_path() -> None:
    with pytest.raises(ValueError, match="--planner cannot be used with --target-tick-log-path"):
        tracking.TrackingRunSettings(
            episode_spec_path="datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
            planner="hybrid_forward",
            target_tick_log_path="runs/custom/scene_tick_log.json",
        )


def test_tracking_run_settings_rejects_embed_forbidden_zone_without_hybrid() -> None:
    with pytest.raises(ValueError, match="requires --planner hybrid_forward"):
        tracking.TrackingRunSettings(
            episode_spec_path="datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
            planner="waypoint",
            embed_forbidden_zone=True,
        )


def test_tracking_run_settings_rejects_camera_log_with_no_rendering() -> None:
    with pytest.raises(ValueError, match="cannot be used with --no-rendering"):
        tracking.TrackingRunSettings(
            episode_spec_path="datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
            no_rendering_mode=True,
            enable_camera_log=True,
        )


def test_run_tracking_workflow_camera_recorder_default_path_and_result_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    template = _scene_template()
    selected_vehicle = VehicleDescriptor(
        actor_id=101,
        type_id="vehicle.tesla.model3",
        role_name="ego",
        x=0.0,
        y=0.0,
        z=0.0,
    )
    expected_tracking_result = TrackingResult(
        executed_steps=1,
        last_frame=1,
        reached_goal=False,
        termination_reason="max_steps",
        final_distance_to_goal_m=1.0,
        final_yaw_error_deg=2.0,
        route_points=(),
        step_traces=(),
    )
    episode_spec = EpisodeSpec(
        schema_version=1,
        episode_id="ep_000001",
        scene_json_path="scene_out.json",
        start_transform=EpisodeTransform(x=1.0, y=2.0, z=0.1, yaw=0.0),
        goal_transform=EpisodeTransform(x=10.0, y=20.0, z=0.1, yaw=180.0),
        instruction="",
        max_steps=2,
        seed=123,
    )

    class FakeWorld:
        def get_actor(self, actor_id: int) -> Any:
            captured["camera_target_actor_id"] = actor_id
            return object()

    fake_world = FakeWorld()

    class FakeSceneStore:
        def load(self, _path: str) -> SceneTemplate:
            return template

    class FakeEpisodeStore:
        def load(self, _path: str) -> EpisodeSpec:
            return episode_spec

        def resolve_scene_json_path(self, **_kwargs: Any) -> str:
            return "artifacts/scene_out.json"

    @contextmanager
    def fake_managed_session(config: tracking.CarlaSessionConfig):
        captured["session_config"] = config
        yield SimpleNamespace(world=fake_world)

    class FakeImportSceneTemplate:
        def __init__(self, **_kwargs: Any) -> None:
            return

        def run(self, _path: str) -> int:
            return 1

    class FakeRunTrackingLoop:
        def __init__(self, **_kwargs: Any) -> None:
            return

        def run(self, _request: Any) -> TrackingResult:
            return expected_tracking_result

    class FakeRecorder:
        def __init__(self, **kwargs: Any) -> None:
            captured["camera_recorder_init"] = kwargs
            self._base_output_dir = Path(kwargs["base_output_dir"])
            self.frames_captured = 3
            self.last_error = None
            self.output_dir = str(self._base_output_dir / "front_rgb")
            self._index_path = str(self._base_output_dir / "front_rgb" / "index.json")
            self.started = 0
            self.stopped = 0
            self.destroyed = 0
            self.saved = 0

        def start(self) -> None:
            self.started += 1

        def stop(self) -> None:
            self.stopped += 1

        def save_index(self) -> str:
            self.saved += 1
            return self._index_path

        def destroy(self) -> None:
            self.destroyed += 1

    class _FakeDateTime:
        @staticmethod
        def now() -> datetime:
            return datetime(2026, 3, 1, 12, 34, 56)

    monkeypatch.setattr(tracking, "SceneTemplateJsonStore", lambda: FakeSceneStore())
    monkeypatch.setattr(tracking, "EpisodeSpecJsonStore", lambda: FakeEpisodeStore())
    monkeypatch.setattr(tracking, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(tracking, "ImportSceneTemplate", FakeImportSceneTemplate)
    monkeypatch.setattr(tracking, "RunTrackingLoop", FakeRunTrackingLoop)
    monkeypatch.setattr(tracking, "CarlaFrontRgbCameraRecorder", FakeRecorder)
    monkeypatch.setattr(tracking, "datetime", _FakeDateTime)
    monkeypatch.setattr(
        tracking,
        "_resolve_control_target_with_retry",
        lambda **_kwargs: selected_vehicle,
    )

    settings = tracking.TrackingRunSettings(
        episode_spec_path="datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
        host="127.0.0.1",
        port=2000,
        enable_camera_log=True,
        max_steps=1,
    )

    result = tracking.run_tracking_workflow(settings)

    expected_base_dir = Path("runs/20260301_123456/results/ep_000001/camera")
    assert captured["camera_recorder_init"]["base_output_dir"] == expected_base_dir
    assert result.camera_output_dir is not None
    assert Path(result.camera_output_dir).as_posix() == (
        "runs/20260301_123456/results/ep_000001/camera/front_rgb"
    )
    assert result.camera_index_path is not None
    assert Path(result.camera_index_path).as_posix() == (
        "runs/20260301_123456/results/ep_000001/camera/front_rgb/index.json"
    )
    assert result.camera_frames == 3


def test_run_tracking_workflow_camera_recorder_uses_custom_log_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    template = _scene_template()
    selected_vehicle = VehicleDescriptor(
        actor_id=102,
        type_id="vehicle.tesla.model3",
        role_name="ego",
        x=0.0,
        y=0.0,
        z=0.0,
    )
    expected_tracking_result = TrackingResult(
        executed_steps=1,
        last_frame=1,
        reached_goal=False,
        termination_reason="max_steps",
        final_distance_to_goal_m=1.0,
        final_yaw_error_deg=2.0,
        route_points=(),
        step_traces=(),
    )
    episode_spec = EpisodeSpec(
        schema_version=1,
        episode_id="ep_000001",
        scene_json_path="scene_out.json",
        start_transform=EpisodeTransform(x=1.0, y=2.0, z=0.1, yaw=0.0),
        goal_transform=EpisodeTransform(x=10.0, y=20.0, z=0.1, yaw=180.0),
        instruction="",
        max_steps=2,
        seed=123,
    )

    class FakeWorld:
        def get_actor(self, _actor_id: int) -> Any:
            return object()

    @contextmanager
    def fake_managed_session(_config: tracking.CarlaSessionConfig):
        yield SimpleNamespace(world=FakeWorld())

    class FakeSceneStore:
        def load(self, _path: str) -> SceneTemplate:
            return template

    class FakeEpisodeStore:
        def load(self, _path: str) -> EpisodeSpec:
            return episode_spec

        def resolve_scene_json_path(self, **_kwargs: Any) -> str:
            return "artifacts/scene_out.json"

    class FakeImportSceneTemplate:
        def __init__(self, **_kwargs: Any) -> None:
            return

        def run(self, _path: str) -> int:
            return 1

    class FakeRunTrackingLoop:
        def __init__(self, **_kwargs: Any) -> None:
            return

        def run(self, _request: Any) -> TrackingResult:
            return expected_tracking_result

    class FakeRecorder:
        def __init__(self, **kwargs: Any) -> None:
            captured["base_output_dir"] = kwargs["base_output_dir"]
            self.frames_captured = 1
            self.last_error = None
            self.output_dir = str(Path(kwargs["base_output_dir"]) / "front_rgb")

        def start(self) -> None:
            return

        def stop(self) -> None:
            return

        def save_index(self) -> str:
            return str(Path(captured["base_output_dir"]) / "front_rgb" / "index.json")

        def destroy(self) -> None:
            return

    monkeypatch.setattr(tracking, "SceneTemplateJsonStore", lambda: FakeSceneStore())
    monkeypatch.setattr(tracking, "EpisodeSpecJsonStore", lambda: FakeEpisodeStore())
    monkeypatch.setattr(tracking, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(tracking, "ImportSceneTemplate", FakeImportSceneTemplate)
    monkeypatch.setattr(tracking, "RunTrackingLoop", FakeRunTrackingLoop)
    monkeypatch.setattr(tracking, "CarlaFrontRgbCameraRecorder", FakeRecorder)
    monkeypatch.setattr(
        tracking,
        "_resolve_control_target_with_retry",
        lambda **_kwargs: selected_vehicle,
    )

    settings = tracking.TrackingRunSettings(
        episode_spec_path="datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
        host="127.0.0.1",
        port=2000,
        enable_camera_log=True,
        camera_log_dir="runs/custom_camera_log",
        max_steps=1,
    )

    result = tracking.run_tracking_workflow(settings)

    assert Path(captured["base_output_dir"]).as_posix() == "runs/custom_camera_log"
    assert result.camera_output_dir is not None
    assert Path(result.camera_output_dir).as_posix() == "runs/custom_camera_log/front_rgb"


def test_run_tracking_workflow_camera_callback_error_raises_and_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    template = _scene_template()
    selected_vehicle = VehicleDescriptor(
        actor_id=103,
        type_id="vehicle.tesla.model3",
        role_name="ego",
        x=0.0,
        y=0.0,
        z=0.0,
    )
    episode_spec = EpisodeSpec(
        schema_version=1,
        episode_id="ep_000001",
        scene_json_path="scene_out.json",
        start_transform=EpisodeTransform(x=1.0, y=2.0, z=0.1, yaw=0.0),
        goal_transform=EpisodeTransform(x=10.0, y=20.0, z=0.1, yaw=180.0),
        instruction="",
        max_steps=2,
        seed=123,
    )

    class FakeWorld:
        def get_actor(self, _actor_id: int) -> Any:
            return object()

        def tick(self) -> int:
            return 1

    @contextmanager
    def fake_managed_session(_config: tracking.CarlaSessionConfig):
        yield SimpleNamespace(world=FakeWorld())

    class FakeSceneStore:
        def load(self, _path: str) -> SceneTemplate:
            return template

    class FakeEpisodeStore:
        def load(self, _path: str) -> EpisodeSpec:
            return episode_spec

        def resolve_scene_json_path(self, **_kwargs: Any) -> str:
            return "artifacts/scene_out.json"

    class FakeImportSceneTemplate:
        def __init__(self, **_kwargs: Any) -> None:
            return

        def run(self, _path: str) -> int:
            return 1

    class FakeRunTrackingLoop:
        def __init__(self, **kwargs: Any) -> None:
            self._clock = kwargs["clock"]

        def run(self, _request: Any) -> TrackingResult:
            self._clock.tick()
            return TrackingResult(
                executed_steps=1,
                last_frame=1,
                reached_goal=False,
                termination_reason="max_steps",
                final_distance_to_goal_m=1.0,
                final_yaw_error_deg=2.0,
                route_points=(),
                step_traces=(),
            )

    class FakeRecorder:
        def __init__(self, **_kwargs: Any) -> None:
            self.frames_captured = 0
            self.last_error = "jpeg encode failed"
            self.output_dir = "runs/fake/front_rgb"

        def start(self) -> None:
            captured["started"] = captured.get("started", 0) + 1

        def stop(self) -> None:
            captured["stopped"] = captured.get("stopped", 0) + 1

        def save_index(self) -> str:
            captured["saved"] = captured.get("saved", 0) + 1
            return "runs/fake/front_rgb/index.json"

        def destroy(self) -> None:
            captured["destroyed"] = captured.get("destroyed", 0) + 1

    monkeypatch.setattr(tracking, "SceneTemplateJsonStore", lambda: FakeSceneStore())
    monkeypatch.setattr(tracking, "EpisodeSpecJsonStore", lambda: FakeEpisodeStore())
    monkeypatch.setattr(tracking, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(tracking, "ImportSceneTemplate", FakeImportSceneTemplate)
    monkeypatch.setattr(tracking, "RunTrackingLoop", FakeRunTrackingLoop)
    monkeypatch.setattr(tracking, "CarlaFrontRgbCameraRecorder", FakeRecorder)
    monkeypatch.setattr(
        tracking,
        "_resolve_control_target_with_retry",
        lambda **_kwargs: selected_vehicle,
    )

    settings = tracking.TrackingRunSettings(
        episode_spec_path="datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
        host="127.0.0.1",
        port=2000,
        enable_camera_log=True,
        max_steps=1,
    )

    with pytest.raises(RuntimeError, match="camera recorder callback failed"):
        tracking.run_tracking_workflow(settings)
    assert captured["started"] == 1
    assert captured["stopped"] == 1
    assert captured["saved"] == 1
    assert captured["destroyed"] == 1


def test_run_tracking_workflow_camera_start_failure_raises_and_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    template = _scene_template()
    selected_vehicle = VehicleDescriptor(
        actor_id=104,
        type_id="vehicle.tesla.model3",
        role_name="ego",
        x=0.0,
        y=0.0,
        z=0.0,
    )
    episode_spec = EpisodeSpec(
        schema_version=1,
        episode_id="ep_000001",
        scene_json_path="scene_out.json",
        start_transform=EpisodeTransform(x=1.0, y=2.0, z=0.1, yaw=0.0),
        goal_transform=EpisodeTransform(x=10.0, y=20.0, z=0.1, yaw=180.0),
        instruction="",
        max_steps=2,
        seed=123,
    )

    class FakeWorld:
        def get_actor(self, _actor_id: int) -> Any:
            return object()

    @contextmanager
    def fake_managed_session(_config: tracking.CarlaSessionConfig):
        yield SimpleNamespace(world=FakeWorld())

    class FakeSceneStore:
        def load(self, _path: str) -> SceneTemplate:
            return template

    class FakeEpisodeStore:
        def load(self, _path: str) -> EpisodeSpec:
            return episode_spec

        def resolve_scene_json_path(self, **_kwargs: Any) -> str:
            return "artifacts/scene_out.json"

    class FakeImportSceneTemplate:
        def __init__(self, **_kwargs: Any) -> None:
            return

        def run(self, _path: str) -> int:
            return 1

    class FakeRunTrackingLoop:
        def __init__(self, **_kwargs: Any) -> None:
            return

        def run(self, _request: Any) -> TrackingResult:
            raise AssertionError("tracking loop should not run when camera start fails")

    class FailingRecorder:
        def __init__(self, **_kwargs: Any) -> None:
            self.frames_captured = 0
            self.last_error = None
            self.output_dir = "runs/fake/front_rgb"

        def start(self) -> None:
            captured["started"] = captured.get("started", 0) + 1
            raise RuntimeError("spawn failed")

        def stop(self) -> None:
            captured["stopped"] = captured.get("stopped", 0) + 1

        def save_index(self) -> str:
            captured["saved"] = captured.get("saved", 0) + 1
            return "runs/fake/front_rgb/index.json"

        def destroy(self) -> None:
            captured["destroyed"] = captured.get("destroyed", 0) + 1

    monkeypatch.setattr(tracking, "SceneTemplateJsonStore", lambda: FakeSceneStore())
    monkeypatch.setattr(tracking, "EpisodeSpecJsonStore", lambda: FakeEpisodeStore())
    monkeypatch.setattr(tracking, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(tracking, "ImportSceneTemplate", FakeImportSceneTemplate)
    monkeypatch.setattr(tracking, "RunTrackingLoop", FakeRunTrackingLoop)
    monkeypatch.setattr(tracking, "CarlaFrontRgbCameraRecorder", FailingRecorder)
    monkeypatch.setattr(
        tracking,
        "_resolve_control_target_with_retry",
        lambda **_kwargs: selected_vehicle,
    )

    settings = tracking.TrackingRunSettings(
        episode_spec_path="datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
        host="127.0.0.1",
        port=2000,
        enable_camera_log=True,
        max_steps=1,
    )

    with pytest.raises(RuntimeError, match="spawn failed"):
        tracking.run_tracking_workflow(settings)
    assert captured["started"] == 1
    assert captured["stopped"] == 1
    assert captured["saved"] == 1
    assert captured["destroyed"] == 1
