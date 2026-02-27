"""Domain value object for planar coordinates."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Point2D:
    """Immutable 2D point used in forbidden-zone geometry."""

    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", float(self.x))
        object.__setattr__(self, "y", float(self.y))
