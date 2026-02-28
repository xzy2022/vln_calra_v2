"""Infrastructure adapter for runtime session registry port."""

from dataclasses import dataclass

from vln_carla2.infrastructure.carla.session_runtime import (
    CarlaSessionConfig,
    clear_runtime_session_config,
    read_runtime_offscreen_mode,
    record_runtime_session_config,
)
from vln_carla2.usecases.cli.ports.runtime_session_registry import RuntimeSessionRegistryPort


@dataclass(slots=True)
class RuntimeSessionRegistryAdapter(RuntimeSessionRegistryPort):
    """Persist/read runtime session metadata through session_runtime helpers."""

    def record_session(
        self,
        record: object,
        *,
        owner_pid: int | None = None,
    ) -> None:
        host = str(getattr(record, "host"))
        port = int(getattr(record, "port"))
        offscreen_mode = bool(getattr(record, "offscreen_mode"))
        record_runtime_session_config(
            CarlaSessionConfig(
                host=host,
                port=port,
                timeout_seconds=1.0,
                map_name="N/A",
                synchronous_mode=False,
                fixed_delta_seconds=0.05,
                no_rendering_mode=False,
                offscreen_mode=offscreen_mode,
            ),
            owner_pid=owner_pid,
        )

    def read_offscreen_mode(self, host: str, port: int) -> bool | None:
        return read_runtime_offscreen_mode(host, port)

    def clear_session(self, host: str, port: int) -> None:
        clear_runtime_session_config(host, port)
