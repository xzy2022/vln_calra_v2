"""Outbound port for loading scene template metadata."""

from __future__ import annotations

from typing import Protocol


class SceneTemplateLoaderPort(Protocol):
    """Loads scene-template metadata used by CLI orchestration."""

    def load_map_name(self, path: str) -> str:
        ...

