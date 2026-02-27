from __future__ import annotations

from dataclasses import dataclass

import pytest

from vln_carla2.domain.model.vehicle_ref import VehicleRef
from vln_carla2.usecases.control.run_control_loop import LoopResult
from vln_carla2.usecases.operator.models import VehicleRefInput
from vln_carla2.usecases.operator.ports.vehicle_dto import SpawnVehicleRequest, VehicleDescriptor
from vln_carla2.usecases.operator.resolve_vehicle_ref import ResolveVehicleRef
from vln_carla2.usecases.operator.run_operator_workflow import (
    OperatorWorkflowRequest,
    RunOperatorWorkflow,
)
from vln_carla2.usecases.operator.spawn_vehicle import SpawnVehicle


def _spawn_request() -> SpawnVehicleRequest:
    return SpawnVehicleRequest(
        blueprint_filter="vehicle.tesla.model3",
        spawn_x=0.038,
        spawn_y=15.320,
        spawn_z=0.15,
        spawn_yaw=180.0,
        role_name="ego",
    )


@dataclass
class _FakeResolverPort:
    resolved: VehicleDescriptor | None
    calls: list[VehicleRef]

    def resolve(self, ref: VehicleRef) -> VehicleDescriptor | None:
        self.calls.append(ref)
        return self.resolved


@dataclass
class _FakeSpawnerPort:
    spawned: VehicleDescriptor
    calls: list[SpawnVehicleRequest]

    def spawn(self, request: SpawnVehicleRequest) -> VehicleDescriptor:
        self.calls.append(request)
        return self.spawned


@dataclass
class _FakeOperatorRuntime:
    run_calls: list[int | None]
    step_calls: list[tuple[bool, bool]]
    events: list[str]

    def run(self, *, max_ticks: int | None = None) -> int:
        self.run_calls.append(max_ticks)
        return int(max_ticks or 0)

    def step(self, *, with_tick: bool = True, with_sleep: bool = True) -> int | None:
        self.step_calls.append((with_tick, with_sleep))
        self.events.append("operator")
        return None


@dataclass
class _FakeControlLoop:
    events: list[str]
    calls: list[tuple[int, float, int, bool]]

    def run(
        self,
        *,
        vehicle_id,
        target,
        max_steps: int,
        before_step=None,
    ) -> LoopResult:
        self.calls.append((vehicle_id.value, target.target_speed_mps, max_steps, before_step is not None))
        for step in range(1, max_steps + 1):
            if before_step is not None:
                before_step(step)
            self.events.append("control")
        return LoopResult(
            executed_steps=max_steps,
            last_speed_mps=1.0,
            avg_speed_mps=1.0,
            last_frame=max_steps,
        )


def test_run_operator_workflow_serial_uses_resolved_vehicle_without_spawn() -> None:
    resolved = VehicleDescriptor(
        actor_id=7,
        type_id="vehicle.tesla.model3",
        role_name="ego",
        x=0.0,
        y=0.0,
        z=0.0,
    )
    resolver = _FakeResolverPort(resolved=resolved, calls=[])
    spawner = _FakeSpawnerPort(spawned=resolved, calls=[])
    operator_runtime = _FakeOperatorRuntime(run_calls=[], step_calls=[], events=[])
    control_loop = _FakeControlLoop(events=[], calls=[])
    usecase = RunOperatorWorkflow(
        resolve_vehicle_ref=ResolveVehicleRef(resolver=resolver),
        spawn_vehicle=SpawnVehicle(spawner=spawner),
        operator_runtime_factory=lambda _actor_id: operator_runtime,
        control_loop_factory=lambda _actor_id: control_loop,
    )

    result = usecase.run(
        OperatorWorkflowRequest(
            vehicle_ref=VehicleRefInput(scheme="role", value="ego"),
            spawn_request=_spawn_request(),
            strategy="serial",
            steps=2,
            target_speed_mps=5.5,
            operator_warmup_ticks=3,
        )
    )

    assert result.selected_vehicle == resolved
    assert result.vehicle_source == "resolved"
    assert result.operator_ticks == 3
    assert resolver.calls == [VehicleRef(scheme="role", value="ego")]
    assert spawner.calls == []
    assert operator_runtime.run_calls == [3]
    assert operator_runtime.step_calls == []
    assert control_loop.calls == [(7, 5.5, 2, False)]


def test_run_operator_workflow_parallel_spawns_when_ref_missing() -> None:
    spawned = VehicleDescriptor(
        actor_id=9,
        type_id="vehicle.audi.tt",
        role_name="ego",
        x=1.0,
        y=2.0,
        z=0.1,
    )
    resolver = _FakeResolverPort(resolved=None, calls=[])
    spawner = _FakeSpawnerPort(spawned=spawned, calls=[])
    events: list[str] = []
    operator_runtime = _FakeOperatorRuntime(run_calls=[], step_calls=[], events=events)
    control_loop = _FakeControlLoop(events=events, calls=[])
    usecase = RunOperatorWorkflow(
        resolve_vehicle_ref=ResolveVehicleRef(resolver=resolver),
        spawn_vehicle=SpawnVehicle(spawner=spawner),
        operator_runtime_factory=lambda _actor_id: operator_runtime,
        control_loop_factory=lambda _actor_id: control_loop,
    )

    result = usecase.run(
        OperatorWorkflowRequest(
            vehicle_ref=VehicleRefInput(scheme="first", value=None),
            spawn_request=_spawn_request(),
            strategy="parallel",
            steps=3,
            target_speed_mps=4.0,
        )
    )

    assert result.selected_vehicle == spawned
    assert result.vehicle_source == "spawned"
    assert result.operator_ticks == 3
    assert resolver.calls == [VehicleRef(scheme="first", value=None)]
    assert spawner.calls == [_spawn_request()]
    assert operator_runtime.run_calls == []
    assert operator_runtime.step_calls == [(False, False), (False, False), (False, False)]
    assert control_loop.calls == [(9, 4.0, 3, True)]
    assert events == ["operator", "control", "operator", "control", "operator", "control"]


def test_run_operator_workflow_raises_when_ref_missing_and_spawn_disabled() -> None:
    resolver = _FakeResolverPort(resolved=None, calls=[])
    spawner = _FakeSpawnerPort(
        spawned=VehicleDescriptor(
            actor_id=1,
            type_id="vehicle.tesla.model3",
            role_name="ego",
            x=0.0,
            y=0.0,
            z=0.0,
        ),
        calls=[],
    )
    operator_runtime = _FakeOperatorRuntime(run_calls=[], step_calls=[], events=[])
    control_loop = _FakeControlLoop(events=[], calls=[])
    usecase = RunOperatorWorkflow(
        resolve_vehicle_ref=ResolveVehicleRef(resolver=resolver),
        spawn_vehicle=SpawnVehicle(spawner=spawner),
        operator_runtime_factory=lambda _actor_id: operator_runtime,
        control_loop_factory=lambda _actor_id: control_loop,
    )

    with pytest.raises(RuntimeError, match="spawn_if_missing=False"):
        usecase.run(
            OperatorWorkflowRequest(
                vehicle_ref=VehicleRefInput(scheme="role", value="missing"),
                spawn_request=_spawn_request(),
                spawn_if_missing=False,
            )
        )

    assert spawner.calls == []
