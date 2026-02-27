"""Legacy parser module kept only for migration guidance."""

from __future__ import annotations


class VehicleRefParseError(ValueError):
    """Raised when legacy parser module is used after migration."""


def parse_vehicle_ref(raw: str):
    """Legacy shim that always instructs callers to use the new module."""
    del raw
    raise VehicleRefParseError(
        "vehicle ref parser moved to vln_carla2.app.vehicle_ref_parser"
    )
