"""CLI parser for VehicleRef input values."""

from dataclasses import dataclass

from vln_carla2.domain.model.vehicle_ref import VehicleRef


@dataclass(frozen=True, slots=True)
class VehicleRefParseError(ValueError):
    """Raised when CLI text cannot be parsed as a VehicleRef."""

    raw: str
    reason: str

    def __str__(self) -> str:
        return f"Invalid vehicle ref '{self.raw}': {self.reason}"


def parse_vehicle_ref(raw: str) -> VehicleRef:
    """Parse raw CLI vehicle reference text into a VehicleRef value object."""
    value = raw.strip()
    if not value:
        raise VehicleRefParseError(raw=raw, reason="empty input")

    if value == "first":
        return VehicleRef(scheme="first", value=None)

    if ":" in value:
        scheme, ref_value = value.split(":", 1)
        scheme = scheme.strip()
        ref_value = ref_value.strip()
        if scheme == "actor":
            _require_non_empty(raw, ref_value, "missing actor id")
            return _build_actor_ref(raw=raw, value=ref_value)
        if scheme == "role":
            _require_non_empty(raw, ref_value, "missing role name")
            return VehicleRef(scheme="role", value=ref_value)
        if scheme == "first":
            if ref_value:
                raise VehicleRefParseError(raw=raw, reason="first does not accept a value")
            return VehicleRef(scheme="first", value=None)
        raise VehicleRefParseError(
            raw=raw,
            reason="unsupported scheme (expected actor|role|first)",
        )

    if value.isdigit():
        return _build_actor_ref(raw=raw, value=value)

    raise VehicleRefParseError(
        raw=raw,
        reason="expected 'actor:<id>', 'role:<name>', 'first', or positive integer id",
    )


def _build_actor_ref(*, raw: str, value: str) -> VehicleRef:
    if not value.isdigit() or int(value) <= 0:
        raise VehicleRefParseError(raw=raw, reason="actor id must be positive integer text")
    return VehicleRef(scheme="actor", value=value)


def _require_non_empty(raw: str, value: str, reason: str) -> None:
    if value:
        return
    raise VehicleRefParseError(raw=raw, reason=reason)
