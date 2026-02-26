"""Output presenter helpers for CLI commands."""

from __future__ import annotations

import json
from typing import Iterable

from vln_carla2.usecases.operator.models import VehicleDescriptor


def print_vehicle_list(vehicles: Iterable[VehicleDescriptor], *, output_format: str) -> None:
    """Print one vehicle list in requested format."""
    items = list(vehicles)
    if output_format == "json":
        payload = [_vehicle_to_dict(vehicle) for vehicle in items]
        print(json.dumps(payload, ensure_ascii=False))
        return
    print(_format_table(items))


def print_vehicle(vehicle: VehicleDescriptor, *, output_format: str) -> None:
    """Print one vehicle descriptor in requested format."""
    if output_format == "json":
        print(json.dumps(_vehicle_to_dict(vehicle), ensure_ascii=False))
        return
    print(_format_table([vehicle]))


def _vehicle_to_dict(vehicle: VehicleDescriptor) -> dict[str, object]:
    return {
        "actor_id": vehicle.actor_id,
        "type_id": vehicle.type_id,
        "role_name": vehicle.role_name,
        "x": vehicle.x,
        "y": vehicle.y,
        "z": vehicle.z,
    }


def _format_table(vehicles: list[VehicleDescriptor]) -> str:
    headers = ("actor_id", "type_id", "role_name", "x", "y", "z")
    if not vehicles:
        return "actor_id | type_id | role_name | x | y | z\n(no vehicles)"

    rows = [
        (
            str(vehicle.actor_id),
            vehicle.type_id,
            vehicle.role_name,
            f"{vehicle.x:.3f}",
            f"{vehicle.y:.3f}",
            f"{vehicle.z:.3f}",
        )
        for vehicle in vehicles
    ]
    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]
    header_line = " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    split_line = "-+-".join("-" * width for width in widths)
    body = [
        " | ".join(cell.ljust(widths[index]) for index, cell in enumerate(row))
        for row in rows
    ]
    return "\n".join([header_line, split_line, *body])
