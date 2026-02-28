"""Infrastructure adapter for CARLA server lifecycle control port."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any, cast

from vln_carla2.infrastructure.carla.server_launcher import (
    is_carla_server_reachable,
    is_loopback_host,
    launch_carla_server,
    terminate_carla_server,
    wait_for_carla_server,
)
from vln_carla2.usecases.cli.ports.server_control import CarlaServerControlPort


@dataclass(slots=True)
class CarlaServerControlAdapter(CarlaServerControlPort):
    """Adapter backed by infrastructure.carla.server_launcher utilities."""

    def is_loopback_host(self, host: str) -> bool:
        return is_loopback_host(host)

    def is_server_reachable(
        self,
        host: str,
        port: int,
        timeout_seconds: float = 0.5,
    ) -> bool:
        return is_carla_server_reachable(host, port, timeout_seconds)

    def launch_server(self, request: Any) -> Any:
        return launch_carla_server(
            executable_path=request.executable_path,
            rpc_port=request.rpc_port,
            offscreen=request.offscreen,
            no_rendering=request.no_rendering,
            no_sound=request.no_sound,
            quality_level=request.quality_level,
        )

    def wait_until_ready(
        self,
        host: str,
        port: int,
        timeout_seconds: float,
        *,
        process: Any | None = None,
    ) -> None:
        maybe_process = cast(subprocess.Popen[bytes] | None, process)
        wait_for_carla_server(
            host=host,
            port=port,
            timeout_seconds=timeout_seconds,
            process=maybe_process,
        )

    def terminate_server(self, process: Any) -> None:
        typed_process = cast(subprocess.Popen[bytes], process)
        terminate_carla_server(typed_process)

    def process_pid(self, process: Any) -> int:
        typed_process = cast(subprocess.Popen[bytes], process)
        return int(typed_process.pid)
