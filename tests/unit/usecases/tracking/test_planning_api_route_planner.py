from dataclasses import dataclass

from vln_carla2.domain.model.path import Path
from vln_carla2.domain.model.forbidden_zone import ForbiddenZone
from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.point2d import Point2D
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
    planning_map: PlanningMap

    def run(self, request: BuildPlanningMapRequest) -> PlanningMap:
        del request
        return self.planning_map


@dataclass
class _FakePlanRoute:
    def run(self, request: PlanRouteRequest) -> Path:
        return Path(poses=(request.start, request.goal))


def _planning_map(*, occupied_cells: tuple[tuple[int, int], ...] = ()) -> PlanningMap:
    return PlanningMap(
        map_name="Town10HD_Opt",
        resolution_m=1.0,
        min_x=0.0,
        max_x=5.0,
        min_y=0.0,
        max_y=5.0,
        width=5,
        height=5,
        occupied_cells=occupied_cells,
    )


def test_planning_api_route_planner_maps_domain_path_to_tracking_route_points() -> None:
    adapter = PlanningApiRoutePlannerAdapter(
        map_name="Town10HD_Opt",
        build_planning_map=_FakeBuildPlanningMap(planning_map=_planning_map()),
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
    assert adapter.last_planning_map is not None
    assert adapter.last_planning_map.map_name == "Town10HD_Opt"
    assert adapter.last_planning_map.resolution_m == 1.0


def test_planning_api_route_planner_embeds_forbidden_zone_into_occupied_cells() -> None:
    adapter = PlanningApiRoutePlannerAdapter(
        map_name="Town10HD_Opt",
        build_planning_map=_FakeBuildPlanningMap(
            planning_map=_planning_map(occupied_cells=((4, 4),))
        ),
        plan_route_usecase=_FakePlanRoute(),
        forbidden_zone=ForbiddenZone(
            vertices=(
                Point2D(x=1.0, y=1.0),
                Point2D(x=3.0, y=1.0),
                Point2D(x=3.0, y=3.0),
                Point2D(x=1.0, y=3.0),
            )
        ),
    )

    adapter.plan_route(
        start_x=0.5,
        start_y=0.5,
        start_yaw_deg=0.0,
        goal=TrackingGoal(x=4.5, y=4.5, yaw_deg=0.0),
        route_step_m=1.0,
        route_max_points=200,
    )

    assert adapter.last_planning_map is not None
    occupied = set(adapter.last_planning_map.occupied_cells)
    assert (4, 4) in occupied
    assert (1, 1) in occupied
    assert (1, 2) in occupied
    assert (2, 1) in occupied
    assert (2, 2) in occupied


def test_planning_api_route_planner_keeps_occupancy_when_zone_outside_map() -> None:
    source_map = _planning_map(occupied_cells=((0, 0), (4, 4)))
    adapter = PlanningApiRoutePlannerAdapter(
        map_name="Town10HD_Opt",
        build_planning_map=_FakeBuildPlanningMap(planning_map=source_map),
        plan_route_usecase=_FakePlanRoute(),
        forbidden_zone=ForbiddenZone(
            vertices=(
                Point2D(x=20.0, y=20.0),
                Point2D(x=30.0, y=20.0),
                Point2D(x=20.0, y=30.0),
            )
        ),
    )

    adapter.plan_route(
        start_x=1.0,
        start_y=1.0,
        start_yaw_deg=0.0,
        goal=TrackingGoal(x=4.0, y=4.0, yaw_deg=0.0),
        route_step_m=1.0,
        route_max_points=200,
    )

    assert adapter.last_planning_map is not None
    assert adapter.last_planning_map.occupied_cells == source_map.occupied_cells
