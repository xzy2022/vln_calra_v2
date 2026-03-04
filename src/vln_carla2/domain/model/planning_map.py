"""Domain value objects for planning map representation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from vln_carla2.domain.model.obstacle import Obstacle


@dataclass(frozen=True, slots=True)
class PlanningMapSeed:
    """Raw map snapshot used to build planner-consumable occupancy map."""

    map_name: str
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    obstacles: tuple[Obstacle, ...] = ()

    def __post_init__(self) -> None:
        map_name = str(self.map_name).strip()
        if not map_name:
            raise ValueError("map_name must not be empty")

        min_x = float(self.min_x)
        max_x = float(self.max_x)
        min_y = float(self.min_y)
        max_y = float(self.max_y)
        if not all(math.isfinite(value) for value in (min_x, max_x, min_y, max_y)):
            raise ValueError("planning map seed bounds must be finite")
        if max_x <= min_x:
            raise ValueError("planning map seed requires max_x > min_x")
        if max_y <= min_y:
            raise ValueError("planning map seed requires max_y > min_y")

        object.__setattr__(self, "map_name", map_name)
        object.__setattr__(self, "min_x", min_x)
        object.__setattr__(self, "max_x", max_x)
        object.__setattr__(self, "min_y", min_y)
        object.__setattr__(self, "max_y", max_y)


@dataclass(frozen=True, slots=True)
class PlanningMap:
    """Grid occupancy map consumed by A* / Hybrid A* planners."""

    map_name: str
    resolution_m: float
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    width: int
    height: int
    occupied_cells: tuple[tuple[int, int], ...] = ()
    _occupied_set: frozenset[tuple[int, int]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        map_name = str(self.map_name).strip()
        if not map_name:
            raise ValueError("map_name must not be empty")

        resolution_m = float(self.resolution_m)
        min_x = float(self.min_x)
        max_x = float(self.max_x)
        min_y = float(self.min_y)
        max_y = float(self.max_y)
        width = int(self.width)
        height = int(self.height)

        if not math.isfinite(resolution_m) or resolution_m <= 0.0:
            raise ValueError("resolution_m must be > 0")
        if not all(math.isfinite(value) for value in (min_x, max_x, min_y, max_y)):
            raise ValueError("planning map bounds must be finite")
        if max_x <= min_x:
            raise ValueError("planning map requires max_x > min_x")
        if max_y <= min_y:
            raise ValueError("planning map requires max_y > min_y")
        if width <= 0 or height <= 0:
            raise ValueError("planning map width/height must be > 0")

        normalized_cells = sorted(
            {
                (int(cell_x), int(cell_y))
                for cell_x, cell_y in self.occupied_cells
                if 0 <= int(cell_x) < width and 0 <= int(cell_y) < height
            }
        )
        occupied_set = frozenset(normalized_cells)

        object.__setattr__(self, "map_name", map_name)
        object.__setattr__(self, "resolution_m", resolution_m)
        object.__setattr__(self, "min_x", min_x)
        object.__setattr__(self, "max_x", max_x)
        object.__setattr__(self, "min_y", min_y)
        object.__setattr__(self, "max_y", max_y)
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)
        object.__setattr__(self, "occupied_cells", tuple(normalized_cells))
        object.__setattr__(self, "_occupied_set", occupied_set)

    def in_bounds(self, *, cell_x: int, cell_y: int) -> bool:
        return 0 <= cell_x < self.width and 0 <= cell_y < self.height

    def contains_world(self, *, x: float, y: float) -> bool:
        x = float(x)
        y = float(y)
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y

    def world_to_grid(self, *, x: float, y: float) -> tuple[int, int]:
        x = float(x)
        y = float(y)
        if not self.contains_world(x=x, y=y):
            raise ValueError(f"world point out of bounds: x={x:.3f} y={y:.3f}")

        fx = (x - self.min_x) / self.resolution_m
        fy = (y - self.min_y) / self.resolution_m
        cell_x = min(self.width - 1, int(math.floor(fx)))
        cell_y = min(self.height - 1, int(math.floor(fy)))
        return (cell_x, cell_y)

    def grid_to_world(self, *, cell_x: int, cell_y: int) -> tuple[float, float]:
        if not self.in_bounds(cell_x=cell_x, cell_y=cell_y):
            raise ValueError(
                f"grid index out of bounds: cell_x={cell_x} cell_y={cell_y}"
            )
        x = self.min_x + (float(cell_x) + 0.5) * self.resolution_m
        y = self.min_y + (float(cell_y) + 0.5) * self.resolution_m
        return (x, y)

    def is_cell_occupied(self, *, cell_x: int, cell_y: int) -> bool:
        if not self.in_bounds(cell_x=cell_x, cell_y=cell_y):
            return True
        return (cell_x, cell_y) in self._occupied_set

    def is_world_occupied(self, *, x: float, y: float) -> bool:
        if not self.contains_world(x=x, y=y):
            return True
        cell_x, cell_y = self.world_to_grid(x=x, y=y)
        return self.is_cell_occupied(cell_x=cell_x, cell_y=cell_y)

