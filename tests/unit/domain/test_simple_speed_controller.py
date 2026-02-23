from vln_carla2.domain.model.simple_command import TargetSpeedCommand
from vln_carla2.domain.model.vehicle_state import VehicleState
from vln_carla2.domain.services.simple_speed_controller import SimpleSpeedController


def _state_with_speed(speed_mps: float) -> VehicleState:
    return VehicleState(
        frame=1,
        x=0.0,
        y=0.0,
        z=0.0,
        yaw_deg=0.0,
        vx=speed_mps,
        vy=0.0,
        vz=0.0,
        speed_mps=speed_mps,
    )


def test_compute_accelerates_when_below_target() -> None:
    controller = SimpleSpeedController()
    state = _state_with_speed(1.0)
    command = controller.compute(state=state, target=TargetSpeedCommand(5.0))

    assert command.throttle > 0.0
    assert command.brake == 0.0
    assert command.steer == 0.0


def test_compute_brakes_when_above_target() -> None:
    controller = SimpleSpeedController()
    state = _state_with_speed(8.0)
    command = controller.compute(state=state, target=TargetSpeedCommand(5.0))

    assert command.brake > 0.0
    assert command.throttle == 0.0
    assert command.steer == 0.0

