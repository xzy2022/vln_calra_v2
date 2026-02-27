"""Use case for orchestrating operator + control closed-loop workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from vln_carla2.domain.model.simple_command import TargetSpeedCommand
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.usecases.operator.models import VehicleRefInput
from vln_carla2.usecases.control.run_control_loop import LoopResult, RunControlLoop
from vln_carla2.usecases.operator.ports.vehicle_dto import SpawnVehicleRequest, VehicleDescriptor
from vln_carla2.usecases.operator.resolve_vehicle_ref import ResolveVehicleRef
from vln_carla2.usecases.operator.run_operator_loop import RunOperatorLoop
from vln_carla2.usecases.operator.spawn_vehicle import SpawnVehicle

OperatorWorkflowStrategy = Literal["serial", "parallel"]
VehicleAcquireSource = Literal["resolved", "spawned"]


@dataclass(frozen=True, slots=True)
class OperatorWorkflowRequest:
    """Input for running one operator workflow."""

    vehicle_ref: VehicleRefInput
    spawn_request: SpawnVehicleRequest
    spawn_if_missing: bool = True
    strategy: OperatorWorkflowStrategy = "parallel"
    target_speed_mps: float = 5.0
    steps: int = 80
    operator_warmup_ticks: int = 1

    def __post_init__(self) -> None:
        if self.strategy not in {"serial", "parallel"}:
            raise ValueError("strategy must be 'serial' or 'parallel'")
        if self.target_speed_mps < 0:
            raise ValueError("target_speed_mps must be >= 0")
        if self.steps <= 0:
            raise ValueError("steps must be > 0")
        if self.operator_warmup_ticks < 0:
            raise ValueError("operator_warmup_ticks must be >= 0")


@dataclass(frozen=True, slots=True)
class OperatorWorkflowResult:
    """Summary of one completed operator workflow."""

    selected_vehicle: VehicleDescriptor
    vehicle_source: VehicleAcquireSource
    strategy: OperatorWorkflowStrategy
    operator_ticks: int
    control_loop_result: LoopResult


@dataclass(slots=True)
class RunOperatorWorkflow:
    """High-level workflow: resolve/spawn -> follow -> control loop."""

    resolve_vehicle_ref: ResolveVehicleRef
    spawn_vehicle: SpawnVehicle
    operator_runtime_factory: Callable[[int], RunOperatorLoop]
    control_loop_factory: Callable[[int], RunControlLoop]

    def run(self, request: OperatorWorkflowRequest) -> OperatorWorkflowResult:
        selected_vehicle, source = self._acquire_vehicle(request)
        actor_id = selected_vehicle.actor_id
        vehicle_id = VehicleId(actor_id)
        target = TargetSpeedCommand(request.target_speed_mps)

        operator_runtime = self.operator_runtime_factory(actor_id)
        control_loop = self.control_loop_factory(actor_id)

        operator_ticks = 0
        if request.strategy == "serial":
            if request.operator_warmup_ticks > 0:
                operator_ticks = operator_runtime.run(max_ticks=request.operator_warmup_ticks)
            control_result = control_loop.run(
                vehicle_id=vehicle_id,
                target=target,
                max_steps=request.steps,
            )
        else:

            def _before_step(_step: int) -> None:
                nonlocal operator_ticks
                operator_runtime.step(with_tick=False, with_sleep=False)
                operator_ticks += 1

            control_result = control_loop.run(
                vehicle_id=vehicle_id,
                target=target,
                max_steps=request.steps,
                before_step=_before_step,
            )

        return OperatorWorkflowResult(
            selected_vehicle=selected_vehicle,
            vehicle_source=source,
            strategy=request.strategy,
            operator_ticks=operator_ticks,
            control_loop_result=control_result,
        )

    def _acquire_vehicle(
        self,
        request: OperatorWorkflowRequest,
    ) -> tuple[VehicleDescriptor, VehicleAcquireSource]:
        descriptor = self.resolve_vehicle_ref.run(request.vehicle_ref)
        if descriptor is not None:
            return descriptor, "resolved"

        if not request.spawn_if_missing:
            raise RuntimeError(
                "vehicle not found from ref and spawn_if_missing=False: "
                f"scheme={request.vehicle_ref.scheme} value={request.vehicle_ref.value}"
            )

        spawned = self.spawn_vehicle.run(request.spawn_request)
        return spawned, "spawned"
