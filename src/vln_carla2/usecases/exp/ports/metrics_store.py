"""Port for persisting exp metrics artifacts."""

from __future__ import annotations

from typing import Mapping, Protocol


class ExpMetricsStorePort(Protocol):
    """Persistence port for metrics payload JSON."""

    def save(self, metrics_payload: Mapping[str, object], path: str) -> str:
        ...
