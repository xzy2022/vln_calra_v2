"""Internal CARLA-to-usecase mapping helpers for vehicle adapters."""

from __future__ import annotations

from typing import Any, Iterable

from vln_carla2.usecases.operator.ports.vehicle_dto import VehicleDescriptor


def iter_vehicle_actors(world: Any) -> Iterable[Any]:
    """Yield vehicle actors from world with CARLA-list fallback support."""
    actors = world.get_actors()
    if hasattr(actors, "filter"):
        yield from actors.filter("vehicle.*")
        return

    for actor in actors:
        if is_vehicle_actor(actor):
            yield actor


def is_vehicle_actor(actor: Any) -> bool:
    """Return whether actor has a CARLA vehicle type id."""
    return str(getattr(actor, "type_id", "")).startswith("vehicle.")


def role_name(actor: Any, *, default: str = "") -> str:
    """Read actor role_name, returning default when missing."""
    attributes = getattr(actor, "attributes", {})
    if hasattr(attributes, "get"):
        return str(attributes.get("role_name", default))
    return str(default)


def to_vehicle_descriptor(actor: Any, *, default_role_name: str = "") -> VehicleDescriptor:
    """Project one CARLA actor into usecase-level VehicleDescriptor."""
    transform = actor.get_transform()
    return VehicleDescriptor(
        actor_id=int(actor.id),
        type_id=str(actor.type_id),
        role_name=role_name(actor, default=default_role_name),
        x=float(transform.location.x),
        y=float(transform.location.y),
        z=float(transform.location.z),
    )
