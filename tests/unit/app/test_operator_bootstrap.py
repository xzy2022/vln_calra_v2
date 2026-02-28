from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from vln_carla2.app.wiring import operator
from vln_carla2.usecases.control.run_control_loop import LoopResult
from vln_carla2.usecases.shared.vehicle_ref import VehicleRefInput
from vln_carla2.usecases.runtime.ports.vehicle_dto import VehicleDescriptor


def _result(actor_id: int = 7):
    return operator.OperatorWorkflowResult(
        selected_vehicle=VehicleDescriptor(
            actor_id=actor_id,
            type_id="vehicle.tesla.model3",
            role_name="ego",
            x=0.0,
            y=0.0,
            z=0.0,
        ),
        vehicle_source="resolved",
        strategy="parallel",
        operator_ticks=3,
        control_loop_result=LoopResult(
            executed_steps=3,
            last_speed_mps=1.2,
            avg_speed_mps=1.0,
            last_frame=3,
        ),
    )


def test_run_wires_session_containers_and_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {
        "container_calls": [],
        "control_calls": [],
    }
    fake_world = object()
    expected = _result(actor_id=42)

    @contextmanager
    def fake_managed_session(config: operator.CarlaSessionConfig):
        captured["session_config"] = config
        yield SimpleNamespace(world=fake_world)

    def fake_build_operator_container(**kwargs: Any):
        captured["container_calls"].append(kwargs)
        follow_vehicle_id = kwargs.get("follow_vehicle_id")
        return SimpleNamespace(
            resolve_vehicle_ref=f"resolve-{follow_vehicle_id}",
            spawn_vehicle=f"spawn-{follow_vehicle_id}",
            runtime=f"runtime-{follow_vehicle_id}",
        )

    def fake_build_control_loop_for_actor(world: Any, actor_id: int):
        captured["control_calls"].append((world, actor_id))
        return f"control-loop-{actor_id}"

    class FakeWorkflow:
        def __init__(self, **kwargs: Any) -> None:
            captured["workflow_init"] = kwargs
            self.operator_runtime_factory = kwargs["operator_runtime_factory"]
            self.control_loop_factory = kwargs["control_loop_factory"]

        def run(self, request: operator.OperatorWorkflowRequest):
            captured["workflow_request"] = request
            captured["runtime"] = self.operator_runtime_factory(42)
            captured["control_loop"] = self.control_loop_factory(42)
            return expected

    monkeypatch.setattr(operator, "managed_carla_session", fake_managed_session)
    monkeypatch.setattr(
        operator,
        "build_operator_container",
        fake_build_operator_container,
    )
    monkeypatch.setattr(
        operator,
        "_build_control_loop_for_actor",
        fake_build_control_loop_for_actor,
    )
    monkeypatch.setattr(operator, "RunOperatorWorkflow", FakeWorkflow)

    settings = operator.OperatorWorkflowSettings(
        host="127.0.0.1",
        port=2000,
        synchronous_mode=True,
        tick_sleep_seconds=0.01,
        vehicle_ref=VehicleRefInput(scheme="role", value="ego"),
        strategy="parallel",
        steps=3,
        target_speed_mps=4.0,
        operator_warmup_ticks=1,
        spectator_initial_z=35.0,
    )

    got = operator.run_operator_workflow(settings)

    session_config = captured["session_config"]
    assert got == expected
    assert session_config.host == "127.0.0.1"
    assert session_config.port == 2000
    assert session_config.synchronous_mode is True
    assert session_config.fixed_delta_seconds == settings.fixed_delta_seconds
    assert captured["container_calls"][0]["follow_vehicle_id"] is None
    assert captured["container_calls"][1]["follow_vehicle_id"] == 42
    assert captured["container_calls"][1]["spectator_initial_z"] == 35.0
    assert captured["workflow_init"]["resolve_vehicle_ref"] == "resolve-None"
    assert captured["workflow_init"]["spawn_vehicle"] == "spawn-None"
    assert captured["runtime"] == "runtime-42"
    assert captured["control_loop"] == "control-loop-42"
    assert captured["control_calls"] == [(fake_world, 42)]
    assert captured["workflow_request"].vehicle_ref == VehicleRefInput(scheme="role", value="ego")
    assert captured["workflow_request"].strategy == "parallel"
    assert captured["workflow_request"].steps == 3
    assert captured["workflow_request"].target_speed_mps == 4.0


def test_build_control_loop_for_actor_raises_when_actor_missing() -> None:
    world = SimpleNamespace(get_actor=lambda _actor_id: None)

    with pytest.raises(RuntimeError, match="Vehicle actor not found"):
        operator._build_control_loop_for_actor(world, 99)


def test_build_control_loop_for_actor_returns_run_control_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = object()
    world = SimpleNamespace(get_actor=lambda _actor_id: actor)
    sentinel_loop = object()

    def fake_build_control_container(_world: Any, _actor: Any):
        return SimpleNamespace(run_control_loop=sentinel_loop)

    monkeypatch.setattr(
        operator,
        "build_control_container",
        fake_build_control_container,
    )

    got = operator._build_control_loop_for_actor(world, 5)

    assert got is sentinel_loop


