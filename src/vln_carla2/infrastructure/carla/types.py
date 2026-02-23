"""Centralized CARLA import boundary."""

from typing import Any

try:
    import carla as _carla # pyright: ignore[reportMissingTypeStubs]  # type: ignore[import-untyped]
except ModuleNotFoundError:
    _carla = None

carla = _carla
CarlaAny = Any


def require_carla() -> Any:
    """Return carla module or raise a clear runtime error."""
    if carla is None:
        raise ModuleNotFoundError("carla package is required. Install carla==0.9.16.")
    return carla

