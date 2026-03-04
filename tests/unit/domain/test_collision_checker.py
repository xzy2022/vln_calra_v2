from vln_carla2.domain.model.path import Path
from vln_carla2.domain.model.planning_map import PlanningMap
from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.domain.services.planning.collision_checker import (
    is_path_colliding,
    is_pose_colliding,
    is_segment_colliding,
)


def _planning_map() -> PlanningMap:
    return PlanningMap(
        map_name="Town10HD_Opt",
        resolution_m=1.0,
        min_x=0.0,
        max_x=6.0,
        min_y=0.0,
        max_y=6.0,
        width=6,
        height=6,
        occupied_cells=((2, 2),),
    )


def test_is_pose_colliding_detects_occupied_world_point() -> None:
    planning_map = _planning_map()
    pose = Pose2D(x=2.1, y=2.1, yaw_deg=0.0)

    assert is_pose_colliding(pose=pose, planning_map=planning_map) is True


def test_is_segment_colliding_detects_collision_crossing_obstacle() -> None:
    planning_map = _planning_map()

    assert (
        is_segment_colliding(
            start=Pose2D(x=1.0, y=1.0, yaw_deg=0.0),
            end=Pose2D(x=4.0, y=4.0, yaw_deg=0.0),
            planning_map=planning_map,
            sample_step_m=0.25,
        )
        is True
    )


def test_is_path_colliding_returns_false_on_clear_path() -> None:
    planning_map = _planning_map()
    path = Path(
        poses=(
            Pose2D(x=0.5, y=0.5, yaw_deg=0.0),
            Pose2D(x=0.5, y=1.5, yaw_deg=90.0),
            Pose2D(x=0.5, y=4.5, yaw_deg=90.0),
        )
    )

    assert is_path_colliding(path=path, planning_map=planning_map, sample_step_m=0.25) is False

