"""Outbound port for cross-process runtime session registry."""

from __future__ import annotations

from typing import Protocol

from vln_carla2.usecases.cli.dto import RuntimeSessionRecord


class RuntimeSessionRegistryPort(Protocol):
    """Persist/read runtime session metadata for host:port lookups."""

    def record_session(
        self,
        record: RuntimeSessionRecord,
        *,
        owner_pid: int | None = None,
    ) -> None:
        ...

    def read_offscreen_mode(self, host: str, port: int) -> bool | None:
        ...

    def clear_session(self, host: str, port: int) -> None:
        ...

