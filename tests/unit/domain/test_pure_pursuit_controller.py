import pytest

from vln_carla2.domain.services.pure_pursuit_controller import PurePursuitController


def test_pure_pursuit_returns_zero_for_straight_ahead_target() -> None:
    controller = PurePursuitController(wheelbase_m=2.85, max_steer_angle_deg=70.0)

    steer = controller.compute_steer(
        ego_x=0.0,
        ego_y=0.0,
        ego_yaw_deg=0.0,
        target_x=10.0,
        target_y=0.0,
        lookahead_distance_m=5.0,
    )

    assert steer == pytest.approx(0.0, abs=1e-6)


def test_pure_pursuit_returns_positive_steer_for_left_target() -> None:
    controller = PurePursuitController()

    steer = controller.compute_steer(
        ego_x=0.0,
        ego_y=0.0,
        ego_yaw_deg=0.0,
        target_x=5.0,
        target_y=2.0,
        lookahead_distance_m=4.0,
    )

    assert steer > 0.0


def test_pure_pursuit_returns_negative_steer_for_right_target() -> None:
    controller = PurePursuitController()

    steer = controller.compute_steer(
        ego_x=0.0,
        ego_y=0.0,
        ego_yaw_deg=0.0,
        target_x=5.0,
        target_y=-2.0,
        lookahead_distance_m=4.0,
    )

    assert steer < 0.0


def test_pure_pursuit_clamps_steer_to_unit_interval() -> None:
    controller = PurePursuitController(wheelbase_m=3.0, max_steer_angle_deg=10.0)

    steer = controller.compute_steer(
        ego_x=0.0,
        ego_y=0.0,
        ego_yaw_deg=0.0,
        target_x=0.1,
        target_y=4.0,
        lookahead_distance_m=0.5,
    )

    assert -1.0 <= steer <= 1.0
    assert steer == pytest.approx(1.0)

