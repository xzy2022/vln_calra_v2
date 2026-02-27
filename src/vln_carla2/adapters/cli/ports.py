"""Protocols consumed by CLI adapter."""

from __future__ import annotations

from typing import Protocol

from vln_carla2.usecases.operator.ports.vehicle_dto import VehicleDescriptor

from .commands import (
    ExpRunCommand,
    OperatorRunCommand,
    SceneRunCommand,
    SpectatorFollowCommand,
    VehicleListCommand,
    VehicleSpawnCommand,
)


class CliApplicationPort(Protocol):
    """Application services used by CLI adapter."""

    def load_env_from_dotenv(self, path: str = ".env") -> None:
        ...

    def get_default_carla_exe(self) -> str | None:
        ...

    def run_scene(self, command: SceneRunCommand) -> int:
        ...

    def run_operator(self, command: OperatorRunCommand) -> int:
        ...

    def run_exp(self, command: ExpRunCommand) -> int:
        ...

    def list_vehicles(self, command: VehicleListCommand) -> list[VehicleDescriptor]:
        ...

    def spawn_vehicle(self, command: VehicleSpawnCommand) -> VehicleDescriptor:
        ...

    def run_spectator_follow(self, command: SpectatorFollowCommand) -> int:
        ...

