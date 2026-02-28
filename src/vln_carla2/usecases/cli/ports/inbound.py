"""Inbound port for CLI orchestration use cases."""

from __future__ import annotations

from typing import Protocol

from vln_carla2.usecases.cli.dto import (
    ExpRunRequest,
    ExpRunResult,
    OperatorRunRequest,
    OperatorRunResult,
    SceneRunRequest,
    SceneRunResult,
    SpectatorFollowRequest,
    SpectatorFollowResult,
    VehicleListRequest,
    VehicleSpawnRequest,
)
from vln_carla2.usecases.operator.ports.vehicle_dto import VehicleDescriptor


class CliApplicationUseCasePort(Protocol):
    """Use cases consumed by the CLI adapter."""

    def run_scene(self, request: SceneRunRequest) -> SceneRunResult:
        ...

    def run_operator(self, request: OperatorRunRequest) -> OperatorRunResult:
        ...

    def run_exp(self, request: ExpRunRequest) -> ExpRunResult:
        ...

    def list_vehicles(self, request: VehicleListRequest) -> list[VehicleDescriptor]:
        ...

    def spawn_vehicle(self, request: VehicleSpawnRequest) -> VehicleDescriptor:
        ...

    def run_spectator_follow(self, request: SpectatorFollowRequest) -> SpectatorFollowResult:
        ...

