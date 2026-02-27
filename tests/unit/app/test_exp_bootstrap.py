from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from vln_carla2.app import exp_bootstrap
from vln_carla2.domain.model.scene_template import (
    SceneObject,
    SceneObjectKind,
    ScenePose,
    SceneTemplate,
)
from vln_carla2.domain.model.vehicle_ref import VehicleRef
from vln_carla2.usecases.control.run_control_loop import LoopResult
from vln_carla2.usecases.exp.run_exp_workflow import ExpWorkflowResult
from vln_carla2.usecases.operator.ports.vehicle_dto import VehicleDescriptor


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


def test_run_wires_exp_dependencies_and_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
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
    expected_exp_result = ExpWorkflowResult(
        control_loop_result=LoopResult(
            executed_steps=3,
            last_speed_mps=1.2,
            avg_speed_mps=1.0,
            last_frame=3,
        ),
        sampled_states=4,
        traveled_distance_m=20.4,
        entered_forbidden_zone=True,
    )

    class FakeSceneStore:
        def load(self, path: str) -> SceneTemplate:
            captured.setdefault("scene_load_calls", []).append(path)
            return template

    @contextmanager
    def fake_managed_session(config: exp_bootstrap.CarlaSessionConfig):
        captured["session_config"] = config
        yield SimpleNamespace(world=fake_world)

    class FakeImportSceneTemplate:
        def __init__(self, **kwargs: Any) -> None:
            captured["import_init"] = kwargs

        def run(self, path: str) -> int:
            captured["import_path"] = path
            return 5

    class FakeBuildForbiddenZoneFromScene:
        def __init__(self, **kwargs: Any) -> None:
            captured["zone_init"] = kwargs

        def run(self, path: str) -> object:
            captured["zone_path"] = path
            return "zone"

    class FakeRunExpWorkflow:
        def __init__(self, **kwargs: Any) -> None:
            captured["exp_init"] = kwargs

        def run(self, request: Any) -> ExpWorkflowResult:
            captured["exp_request"] = request
            return expected_exp_result

    monkeypatch.setattr(exp_bootstrap, "SceneTemplateJsonStore", lambda: FakeSceneStore())
    monkeypatch.setattr(exp_bootstrap, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(exp_bootstrap, "ImportSceneTemplate", FakeImportSceneTemplate)
    def _fake_resolve_control_target_with_retry(**kwargs: Any) -> VehicleDescriptor:
        captured["resolve_kwargs"] = kwargs
        return selected_vehicle

    monkeypatch.setattr(
        exp_bootstrap,
        "_resolve_control_target_with_retry",
        _fake_resolve_control_target_with_retry,
    )
    monkeypatch.setattr(
        exp_bootstrap,
        "BuildForbiddenZoneFromScene",
        FakeBuildForbiddenZoneFromScene,
    )
    monkeypatch.setattr(
        exp_bootstrap,
        "AndrewMonotoneChainForbiddenZoneBuilder",
        lambda: "builder",
    )
    monkeypatch.setattr(exp_bootstrap, "_build_control_loop_for_actor", lambda *_args: "control")
    monkeypatch.setattr(exp_bootstrap, "CarlaWorldAdapter", lambda _world: "world-adapter")
    monkeypatch.setattr(exp_bootstrap, "FollowVehicleTopDown", lambda **kwargs: ("follow", kwargs))
    monkeypatch.setattr(exp_bootstrap, "RunExpWorkflow", FakeRunExpWorkflow)

    settings = exp_bootstrap.ExpRunSettings(
        scene_json_path="artifacts/scene_out.json",
        host="127.0.0.1",
        port=2000,
        control_target=VehicleRef(scheme="role", value="ego"),
        forward_distance_m=20.0,
        target_speed_mps=5.0,
        max_steps=800,
    )

    got = exp_bootstrap.run(settings)

    session_config = captured["session_config"]
    assert session_config.map_name == "Town10HD_Opt"
    assert session_config.force_reload_map is True
    assert captured["import_path"] == "artifacts/scene_out.json"
    assert captured["resolve_kwargs"]["control_target"] == VehicleRef(scheme="role", value="ego")
    assert captured["resolve_kwargs"]["synchronous_mode"] is True
    assert captured["zone_path"] == "artifacts/scene_out.json"
    assert captured["exp_request"].vehicle_id.value == 42
    assert captured["exp_request"].forward_distance_m == 20.0
    assert got.selected_vehicle == selected_vehicle
    assert got.imported_objects == 5
    assert got.exp_workflow_result == expected_exp_result


def test_build_control_loop_for_actor_raises_when_actor_missing() -> None:
    world = SimpleNamespace(get_actor=lambda _actor_id: None)

    with pytest.raises(RuntimeError, match="Vehicle actor not found"):
        exp_bootstrap._build_control_loop_for_actor(world, 99)


def test_resolve_control_target_with_retry_ticks_before_first_resolve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    selected_vehicle = VehicleDescriptor(
        actor_id=7,
        type_id="vehicle.tesla.model3",
        role_name="ego",
        x=0.0,
        y=0.0,
        z=0.0,
    )

    class FakeResolver:
        def __init__(self, **kwargs: Any) -> None:
            del kwargs
            self.calls = 0

        def run(self, _control_target: VehicleRef) -> VehicleDescriptor | None:
            self.calls += 1
            events.append("resolve")
            if self.calls >= 2:
                return selected_vehicle
            return None

    world = SimpleNamespace(
        tick=lambda: events.append("tick") or 123,
        wait_for_tick=lambda: SimpleNamespace(frame=456),
    )

    resolver_instance = FakeResolver()
    monkeypatch.setattr(exp_bootstrap, "ResolveVehicleRef", lambda **kwargs: resolver_instance)
    monkeypatch.setattr(exp_bootstrap, "CarlaVehicleResolverAdapter", lambda _world: "resolver")
    got = exp_bootstrap._resolve_control_target_with_retry(
        world=world,
        control_target=VehicleRef(scheme="role", value="ego"),
        synchronous_mode=True,
        retries=3,
    )

    assert got == selected_vehicle
    assert events == ["tick", "resolve", "tick", "resolve"]


def test_resolve_control_target_with_retry_includes_vehicle_list_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResolver:
        def run(self, _control_target: VehicleRef) -> None:
            return None

    world = SimpleNamespace(
        tick=lambda: 1,
        wait_for_tick=lambda: SimpleNamespace(frame=1),
    )

    monkeypatch.setattr(exp_bootstrap, "ResolveVehicleRef", lambda **kwargs: FakeResolver())
    monkeypatch.setattr(exp_bootstrap, "CarlaVehicleResolverAdapter", lambda _world: "resolver")
    monkeypatch.setattr(
        exp_bootstrap,
        "_describe_current_vehicles",
        lambda _world: "(actor_id=11 type_id=vehicle.tesla.model3 role_name=ego)",
    )

    with pytest.raises(RuntimeError, match="vehicles=") as exc:
        exp_bootstrap._resolve_control_target_with_retry(
            world=world,
            control_target=VehicleRef(scheme="role", value="ego"),
            synchronous_mode=True,
            retries=1,
        )

    assert "actor_id=11" in str(exc.value)
