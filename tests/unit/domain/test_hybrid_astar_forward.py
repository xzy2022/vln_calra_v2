import pytest

from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.domain.services.planning.hybrid_astar_forward import (
    HybridAStarForwardPlanner,
)


def _open_map() -> PlanningMap:
    return PlanningMap(
        map_name="Town10HD_Opt",
        resolution_m=1.0,
        min_x=0.0,
        max_x=10.0,
        min_y=0.0,
        max_y=10.0,
        width=10,
        height=10,
        occupied_cells=(),
    )


def test_hybrid_astar_forward_plans_path_in_open_space() -> None:
    planner = HybridAStarForwardPlanner(
        yaw_bin_deg=15.0,
        primitive_step_m=1.0,
        max_iterations=20000,
    )

    path = planner.plan(
        start=Pose2D(x=1.0, y=1.0, yaw_deg=0.0),
        goal=Pose2D(x=6.0, y=1.0, yaw_deg=0.0),
        planning_map=_open_map(),
        route_step_m=1.0,
        route_max_points=200,
    )

    assert len(path.poses) >= 2
    assert path.poses[0].x == pytest.approx(1.0)
    assert path.poses[-1].x == pytest.approx(6.0)
    assert path.poses[-1].y == pytest.approx(1.0)


def test_hybrid_astar_forward_raises_when_start_is_occupied() -> None:
    planning_map = PlanningMap(
        map_name="Town10HD_Opt",
        resolution_m=1.0,
        min_x=0.0,
        max_x=10.0,
        min_y=0.0,
        max_y=10.0,
        width=10,
        height=10,
        occupied_cells=((1, 1),),
    )
    planner = HybridAStarForwardPlanner()

    with pytest.raises(RuntimeError, match="start pose is occupied"):
        planner.plan(
            start=Pose2D(x=1.1, y=1.1, yaw_deg=0.0),
            goal=Pose2D(x=6.0, y=1.0, yaw_deg=0.0),
            planning_map=planning_map,
            route_step_m=1.0,
            route_max_points=200,
        )


def test_hybrid_astar_forward_raises_when_no_path_exists() -> None:
    occupied = tuple((3, y) for y in range(10))
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
    planner = HybridAStarForwardPlanner(max_iterations=15000)

    with pytest.raises(RuntimeError, match="failed"):
        planner.plan(
            start=Pose2D(x=1.0, y=1.0, yaw_deg=0.0),
            goal=Pose2D(x=6.0, y=1.0, yaw_deg=0.0),
            planning_map=planning_map,
            route_step_m=1.0,
            route_max_points=200,
        )

