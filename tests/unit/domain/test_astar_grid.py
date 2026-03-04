import pytest

from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.domain.services.planning.astar_grid import GridAStarPlanner


def _map_with_gap() -> PlanningMap:
    occupied = tuple((4, y) for y in range(10) if y != 5)
    return PlanningMap(
        map_name="Town10HD_Opt",
        resolution_m=1.0,
        min_x=0.0,
        max_x=10.0,
        min_y=0.0,
        max_y=10.0,
        width=10,
        height=10,
        occupied_cells=occupied,
    )


def test_grid_astar_plans_path_around_obstacle_wall() -> None:
    planner = GridAStarPlanner(max_expansions=50000)
    planning_map = _map_with_gap()

    path = planner.plan(
        start=Pose2D(x=1.0, y=5.0, yaw_deg=0.0),
        goal=Pose2D(x=8.0, y=5.0, yaw_deg=0.0),
        planning_map=planning_map,
        route_step_m=1.0,
        route_max_points=500,
    )

    assert len(path.poses) >= 2
    assert path.poses[0].x == pytest.approx(1.0)
    assert path.poses[0].y == pytest.approx(5.0)
    assert path.poses[-1].x == pytest.approx(8.0)
    assert path.poses[-1].y == pytest.approx(5.0)


def test_grid_astar_raises_when_route_exceeds_max_points() -> None:
    planner = GridAStarPlanner(max_expansions=50000)
    planning_map = _map_with_gap()

    with pytest.raises(RuntimeError, match="route_max_points"):
        planner.plan(
            start=Pose2D(x=1.0, y=5.0, yaw_deg=0.0),
            goal=Pose2D(x=8.0, y=5.0, yaw_deg=0.0),
            planning_map=planning_map,
            route_step_m=1.0,
            route_max_points=2,
        )


def test_grid_astar_raises_when_no_path_exists() -> None:
    occupied = tuple((4, y) for y in range(10))
    planning_map = PlanningMap(
        map_name="Town10HD_Opt",
        resolution_m=1.0,
        min_x=0.0,
        max_x=10.0,
        min_y=0.0,
        max_y=10.0,
        width=10,
        height=10,
        occupied_cells=occupied,
    )
    planner = GridAStarPlanner(max_expansions=50000)

    with pytest.raises(RuntimeError, match="failed to find path"):
        planner.plan(
            start=Pose2D(x=1.0, y=5.0, yaw_deg=0.0),
            goal=Pose2D(x=8.0, y=5.0, yaw_deg=0.0),
            planning_map=planning_map,
            route_step_m=1.0,
            route_max_points=500,
        )

