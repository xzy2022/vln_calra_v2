from dataclasses import dataclass

from vln_carla2.domain.model.obstacle import Obstacle
from vln_carla2.domain.model.planning_map import PlanningMapSeed
from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.usecases.planning.build_planning_map import (
    BuildPlanningMap,
    BuildPlanningMapRequest,
)


@dataclass
class _FakeMapSource:
    seed: PlanningMapSeed

    def snapshot(self, *, map_name: str, start: Pose2D, goal: Pose2D) -> PlanningMapSeed:
        del map_name, start, goal
        return self.seed


def test_build_planning_map_rasterizes_obstacles() -> None:
    usecase = BuildPlanningMap(
        source=_FakeMapSource(
            seed=PlanningMapSeed(
                map_name="Town10HD_Opt",
                min_x=-1.0,
                max_x=1.0,
                min_y=-1.0,
                max_y=1.0,
                obstacles=(Obstacle(x=0.0, y=0.0, radius_m=0.5),),
            )
        ),
        grid_resolution_m=0.5,
        map_padding_m=0.0,
        obstacle_inflation_m=0.0,
    )

    planning_map = usecase.run(
        BuildPlanningMapRequest(
            map_name="Town10HD_Opt",
            start=Pose2D(x=-0.8, y=-0.8, yaw_deg=0.0),
            goal=Pose2D(x=0.8, y=0.8, yaw_deg=0.0),
        )
    )

    assert planning_map.width == 4
    assert planning_map.height == 4
    assert planning_map.is_world_occupied(x=0.0, y=0.0) is True

