from dataclasses import dataclass

from vln_carla2.domain.model.path import Path
from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.usecases.planning.api import (
    BuildPlanningMapRequest,
    PlanRouteRequest,
)
from vln_carla2.usecases.tracking.models import TrackingGoal
from vln_carla2.usecases.tracking.planning_api_route_planner import (
    PlanningApiRoutePlannerAdapter,
)


@dataclass
class _FakeBuildPlanningMap:
    def run(self, request: BuildPlanningMapRequest) -> PlanningMap:
        del request
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


@dataclass
class _FakePlanRoute:
    def run(self, request: PlanRouteRequest) -> Path:
        return Path(poses=(request.start, request.goal))


def test_planning_api_route_planner_maps_domain_path_to_tracking_route_points() -> None:
    adapter = PlanningApiRoutePlannerAdapter(
        map_name="Town10HD_Opt",
        build_planning_map=_FakeBuildPlanningMap(),
        plan_route_usecase=_FakePlanRoute(),
    )

    route = adapter.plan_route(
        start_x=1.0,
        start_y=2.0,
        start_yaw_deg=0.0,
        goal=TrackingGoal(x=8.0, y=2.0, yaw_deg=10.0),
        route_step_m=1.0,
        route_max_points=200,
    )

    assert len(route) == 2
    assert route[0].x == 1.0
    assert route[-1].x == 8.0
    assert route[-1].yaw_deg == 10.0

