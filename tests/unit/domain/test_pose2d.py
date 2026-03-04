import pytest

from vln_carla2.domain.model.pose2d import Pose2D


def test_pose2d_normalizes_yaw_to_minus180_180() -> None:
    pose = Pose2D(x=1.0, y=2.0, yaw_deg=190.0)

    assert pose.yaw_deg == pytest.approx(-170.0)


def test_pose2d_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        Pose2D(x=float("nan"), y=0.0, yaw_deg=0.0)

    with pytest.raises(ValueError, match="finite"):
        Pose2D(x=0.0, y=0.0, yaw_deg=float("inf"))

