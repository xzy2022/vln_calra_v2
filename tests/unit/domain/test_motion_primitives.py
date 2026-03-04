import pytest

from vln_carla2.domain.model.pose2d import Pose2D
from vln_carla2.domain.services.planning.motion_primitives import (
    apply_forward_motion,
    build_forward_motion_primitives,
)


def test_build_forward_motion_primitives_returns_straight_left_right() -> None:
    primitives = build_forward_motion_primitives(step_m=1.0, turn_delta_deg=15.0)

    assert len(primitives) == 3
    assert [primitive.delta_yaw_deg for primitive in primitives] == [0.0, 15.0, -15.0]


def test_apply_forward_motion_moves_pose_forward() -> None:
    straight = build_forward_motion_primitives(step_m=1.0, turn_delta_deg=15.0)[0]
    pose = Pose2D(x=0.0, y=0.0, yaw_deg=0.0)

    next_pose = apply_forward_motion(pose=pose, primitive=straight)

    assert next_pose.x == pytest.approx(1.0)
    assert next_pose.y == pytest.approx(0.0)
    assert next_pose.yaw_deg == pytest.approx(0.0)


def test_apply_forward_motion_turns_with_heading_change() -> None:
    left = build_forward_motion_primitives(step_m=1.0, turn_delta_deg=30.0)[1]
    pose = Pose2D(x=0.0, y=0.0, yaw_deg=0.0)

    next_pose = apply_forward_motion(pose=pose, primitive=left)

    assert next_pose.x > 0.0
    assert next_pose.y > 0.0
    assert next_pose.yaw_deg == pytest.approx(30.0)

