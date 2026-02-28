"""Outbound port for local CARLA server lifecycle control."""

from __future__ import annotations

from typing import Any, Protocol

from vln_carla2.usecases.cli.dto import LaunchCarlaServerRequest


class CarlaServerControlPort(Protocol):
    """Abstract local CARLA server process operations."""

    def is_loopback_host(self, host: str) -> bool:
        ...

    def is_server_reachable(
        self,
        host: str,
        port: int,
        timeout_seconds: float = 0.5,
    ) -> bool:
        ...

    def launch_server(self, request: LaunchCarlaServerRequest) -> Any:
        ...

    def wait_until_ready(
        self,
        host: str,
        port: int,
        timeout_seconds: float,
        *,
        process: Any | None = None,
    ) -> None:
        ...

    def terminate_server(self, process: Any) -> None:
        ...

    def process_pid(self, process: Any) -> int:
        ...

