"""Use case for building planner-consumable occupancy map."""

from __future__ import annotations

import math
from dataclasses import dataclass

from vln_carla2.domain.model.obstacle import Obstacle
from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.usecases.planning.ports.map_source import PlanningMapSourcePort


_MAX_GRID_CELLS = 2_000_000


@dataclass(frozen=True, slots=True)
class BuildPlanningMapRequest:
    """Input payload for planning map build."""

    map_name: str
    start: Pose2D
    goal: Pose2D


@dataclass(slots=True)
class BuildPlanningMap:
    """Build occupancy grid from map snapshot."""

    source: PlanningMapSourcePort
    grid_resolution_m: float = 0.5
    map_padding_m: float = 10.0
    obstacle_inflation_m: float = 1.6

    def __post_init__(self) -> None:
        if self.grid_resolution_m <= 0.0:
            raise ValueError("grid_resolution_m must be > 0")
        if self.map_padding_m < 0.0:
            raise ValueError("map_padding_m must be >= 0")
        if self.obstacle_inflation_m < 0.0:
            raise ValueError("obstacle_inflation_m must be >= 0")

    def run(self, request: BuildPlanningMapRequest) -> PlanningMap:
        seed = self.source.snapshot(
            map_name=request.map_name,
            start=request.start,
            goal=request.goal,
        )

        min_x = float(seed.min_x) - self.map_padding_m
        max_x = float(seed.max_x) + self.map_padding_m
        min_y = float(seed.min_y) - self.map_padding_m
        max_y = float(seed.max_y) + self.map_padding_m

        width = max(1, int(math.ceil((max_x - min_x) / self.grid_resolution_m)))
        height = max(1, int(math.ceil((max_y - min_y) / self.grid_resolution_m)))
        if width * height > _MAX_GRID_CELLS:
            raise RuntimeError(
                "planning map grid too large: "
                f"width={width} height={height} cells={width * height}"
            )

        occupied = _build_occupied_cells(
            obstacles=seed.obstacles,
            min_x=min_x,
            min_y=min_y,
            width=width,
            height=height,
            grid_resolution_m=self.grid_resolution_m,
            obstacle_inflation_m=self.obstacle_inflation_m,
        )
        return PlanningMap(
            map_name=seed.map_name,
            resolution_m=self.grid_resolution_m,
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
            width=width,
            height=height,
            occupied_cells=tuple(sorted(occupied)),
        )


def _build_occupied_cells(
    *,
    obstacles: tuple[Obstacle, ...],
    min_x: float,
    min_y: float,
    width: int,
    height: int,
    grid_resolution_m: float,
    obstacle_inflation_m: float,
) -> set[tuple[int, int]]:
    occupied: set[tuple[int, int]] = set()
    if not obstacles:
        return occupied

    for obstacle in obstacles:
        radius = obstacle.radius_m + obstacle_inflation_m
        min_cell_x = max(
            0,
            int(math.floor((obstacle.x - radius - min_x) / grid_resolution_m)),
        )
        max_cell_x = min(
            width - 1,
            int(math.ceil((obstacle.x + radius - min_x) / grid_resolution_m)),
        )
        min_cell_y = max(
            0,
            int(math.floor((obstacle.y - radius - min_y) / grid_resolution_m)),
        )
        max_cell_y = min(
            height - 1,
            int(math.ceil((obstacle.y + radius - min_y) / grid_resolution_m)),
        )

        for cell_x in range(min_cell_x, max_cell_x + 1):
            world_x = min_x + (float(cell_x) + 0.5) * grid_resolution_m
            for cell_y in range(min_cell_y, max_cell_y + 1):
                world_y = min_y + (float(cell_y) + 0.5) * grid_resolution_m
                if math.hypot(world_x - obstacle.x, world_y - obstacle.y) <= radius:
                    occupied.add((cell_x, cell_y))

    return occupied

