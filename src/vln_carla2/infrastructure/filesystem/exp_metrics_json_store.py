"""JSON-backed store for experiment metrics artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from vln_carla2.usecases.exp.ports.metrics_store import ExpMetricsStorePort


@dataclass(slots=True)
class ExpMetricsJsonStore(ExpMetricsStorePort):
    """Persist one metrics payload into one JSON file."""

    cwd: Path = field(default_factory=Path.cwd)

    def save(self, metrics_payload: Mapping[str, object], path: str) -> str:
        if not path or not path.strip():
            raise ValueError("path must not be empty")

        target = Path(path)
        if not target.is_absolute():
            target = self.cwd / target

        target.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(dict(metrics_payload), ensure_ascii=False, indent=2)
        target.write_text(text + "\n", encoding="utf-8")
        return str(target)
