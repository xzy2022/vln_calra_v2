from dataclasses import dataclass

import pytest

from vln_carla2.domain.model.path import Path
from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.usecases.planning.plan_route import PlanRoute, PlanRouteRequest


@dataclass
class _FakePlanner:
    should_fail: bool = False

    def plan(
        self,
        *,
        start: Pose2D,
        goal: Pose2D,
        planning_map: PlanningMap,
        route_step_m: float,
        route_max_points: int,
    ) -> Path:
        del planning_map, route_step_m, route_max_points
        if self.should_fail:
            raise RuntimeError("planner failed")
        return Path(poses=(start, goal))


def _planning_map() -> PlanningMap:
    return PlanningMap(
        map_name="Town10HD_Opt",
        resolution_m=1.0,
        min_x=0.0,
        max_x=10.0,
        min_y=0.0,
        max_y=10.0,
        width=10,
        height=10,
    )


def test_plan_route_returns_path_from_planner() -> None:
    usecase = PlanRoute(planner=_FakePlanner())
    request = PlanRouteRequest(
        start=Pose2D(x=1.0, y=2.0, yaw_deg=0.0),
        goal=Pose2D(x=8.0, y=2.0, yaw_deg=0.0),
        planning_map=_planning_map(),
        route_step_m=1.0,
        route_max_points=200,
    )

    path = usecase.run(request)

    assert path.poses[0].x == pytest.approx(1.0)
    assert path.poses[-1].x == pytest.approx(8.0)


def test_plan_route_propagates_planner_error() -> None:
    usecase = PlanRoute(planner=_FakePlanner(should_fail=True))
    request = PlanRouteRequest(
        start=Pose2D(x=1.0, y=2.0, yaw_deg=0.0),
        goal=Pose2D(x=8.0, y=2.0, yaw_deg=0.0),
        planning_map=_planning_map(),
        route_step_m=1.0,
        route_max_points=200,
    )

    with pytest.raises(RuntimeError, match="planner failed"):
        usecase.run(request)

