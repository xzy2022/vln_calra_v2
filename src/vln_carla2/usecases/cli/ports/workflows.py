"""Outbound ports for workflow execution gateways used by CLI service."""

from __future__ import annotations

from typing import Protocol

from vln_carla2.usecases.cli.dto import (
    ExpRunRequest,
    ExpWorkflowExecution,
    OperatorRunRequest,
    OperatorWorkflowExecution,
    SceneRunRequest,
    SpectatorFollowRequest,
    TrackingRunRequest,
    TrackingWorkflowExecution,
    VehicleListRequest,
    VehicleRefInput,
    VehicleSpawnRequest,
)
from vln_carla2.usecases.shared.vehicle_dto import VehicleDescriptor


class CliWorkflowPort(Protocol):
    """Facade over app-level composition/wiring execution helpers."""

    def run_scene_workflow(self, request: SceneRunRequest) -> None:
        ...

    def run_operator_workflow(self, request: OperatorRunRequest) -> OperatorWorkflowExecution:
        ...

    def run_exp_workflow(self, request: ExpRunRequest) -> ExpWorkflowExecution:
        ...

    def run_tracking_workflow(self, request: TrackingRunRequest) -> TrackingWorkflowExecution:
        ...

    def list_vehicles(self, request: VehicleListRequest) -> list[VehicleDescriptor]:
        ...

    def spawn_vehicle(self, request: VehicleSpawnRequest) -> VehicleDescriptor:
        ...

    def resolve_vehicle_ref(self, request: SpectatorFollowRequest) -> VehicleDescriptor | None:
        ...

    def run_spectator_follow_workflow(
        self,
        request: SpectatorFollowRequest,
        *,
        follow_vehicle_id: int,
    ) -> None:
        ...

    def format_vehicle_ref(self, ref: VehicleRefInput) -> str:
        ...


