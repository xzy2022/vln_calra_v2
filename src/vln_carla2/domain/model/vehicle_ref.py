"""Value object for resilient vehicle references."""

from dataclasses import dataclass
from typing import Literal

VehicleRefScheme = Literal["actor", "role", "first"]


@dataclass(frozen=True, slots=True)
class VehicleRef:
    """Reference a target vehicle by actor id, role name, or first match."""

    scheme: VehicleRefScheme
    value: str | None = None

    def __post_init__(self) -> None:
        if self.scheme == "actor":
            if self.value is None or not self.value.isdigit():
                raise ValueError("VehicleRef(actor) requires positive integer text")
            if int(self.value) <= 0:
                raise ValueError("VehicleRef(actor) requires positive integer text")
            return

        if self.scheme == "role":
            if self.value is None or not self.value.strip():
                raise ValueError("VehicleRef(role) requires non-empty role text")
            return

        if self.scheme == "first":
            if self.value is not None:
                raise ValueError("VehicleRef(first) must use value=None")
            return

        raise ValueError(f"Unsupported VehicleRef scheme: {self.scheme}")
