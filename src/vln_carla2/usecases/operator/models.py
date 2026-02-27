"""Use-case-level input models for operator workflows."""

from dataclasses import dataclass
from typing import Literal


VehicleRefScheme = Literal["actor", "role", "first"]


@dataclass(frozen=True, slots=True)
class VehicleRefInput:
    """Use-case input DTO for selecting a vehicle target."""

    scheme: VehicleRefScheme
    value: str | None = None

    def __post_init__(self) -> None:
        if self.scheme == "actor":
            if self.value is None or not self.value.isdigit():
                raise ValueError("VehicleRefInput(actor) requires positive integer text")
            if int(self.value) <= 0:
                raise ValueError("VehicleRefInput(actor) requires positive integer text")
            return

        if self.scheme == "role":
            if self.value is None or not self.value.strip():
                raise ValueError("VehicleRefInput(role) requires non-empty role text")
            return

        if self.scheme == "first":
            if self.value is not None:
                raise ValueError("VehicleRefInput(first) must use value=None")
            return

        raise ValueError(f"Unsupported VehicleRefInput scheme: {self.scheme}")
