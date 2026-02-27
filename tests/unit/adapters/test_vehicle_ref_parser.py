import pytest

from vln_carla2.adapters.cli.vehicle_ref_parser import (
    VehicleRefParseError,
    parse_vehicle_ref,
)


def test_legacy_vehicle_ref_parser_raises_migration_error() -> None:
    with pytest.raises(VehicleRefParseError, match="moved"):
        parse_vehicle_ref("actor:7")
