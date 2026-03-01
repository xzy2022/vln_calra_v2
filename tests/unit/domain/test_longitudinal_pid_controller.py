import pytest

from vln_carla2.domain.services.longitudinal_pid_controller import LongitudinalPidController


def test_longitudinal_pid_outputs_positive_when_below_target_speed() -> None:
    controller = LongitudinalPidController(kp=1.0, ki=0.0, kd=0.0)

    command = controller.compute(speed_mps=1.0, target_speed_mps=5.0, dt=0.05)

    assert command > 0.0
    assert command <= 1.0


def test_longitudinal_pid_outputs_negative_when_above_target_speed() -> None:
    controller = LongitudinalPidController(kp=1.0, ki=0.0, kd=0.0)

    command = controller.compute(speed_mps=7.0, target_speed_mps=5.0, dt=0.05)

    assert command < 0.0
    assert command >= -1.0


def test_longitudinal_pid_clamps_integral_accumulation() -> None:
    controller = LongitudinalPidController(kp=0.0, ki=5.0, kd=0.0, integral_limit=0.2)

    for _ in range(50):
        controller.compute(speed_mps=0.0, target_speed_mps=10.0, dt=0.1)
    command = controller.compute(speed_mps=0.0, target_speed_mps=10.0, dt=0.1)

    assert command == pytest.approx(1.0)


def test_longitudinal_pid_rejects_non_positive_dt() -> None:
    controller = LongitudinalPidController()

    with pytest.raises(ValueError, match="dt must be > 0"):
        controller.compute(speed_mps=0.0, target_speed_mps=1.0, dt=0.0)

