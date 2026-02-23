"""Value object for vehicle identity."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VehicleId:
    """Domain identifier for a single vehicle actor."""

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            raise TypeError("VehicleId.value must be int")
        if self.value <= 0:
            raise ValueError("VehicleId.value must be positive")

