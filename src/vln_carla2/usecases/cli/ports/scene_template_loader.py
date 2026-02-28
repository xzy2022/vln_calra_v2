"""Outbound port for loading exp input metadata."""

from __future__ import annotations

from typing import Protocol


class SceneTemplateLoaderPort(Protocol):
    """Loads map metadata from exp input paths used by CLI orchestration."""

    def load_map_name(self, path: str) -> str:
        ...
