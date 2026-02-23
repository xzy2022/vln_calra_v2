from dataclasses import dataclass

from vln_carla2.domain.model.simple_command import ControlCommand, TargetSpeedCommand
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.model.vehicle_state import VehicleState
from vln_carla2.usecases.run_control_loop import RunControlLoop


def _state(frame: int, speed_mps: float) -> VehicleState:
    return VehicleState(
        frame=frame,
        x=0.0,
        y=0.0,
        z=0.0,
        yaw_deg=0.0,
        vx=speed_mps,
        vy=0.0,
        vz=0.0,
        speed_mps=speed_mps,
    )


@dataclass
class FakeStateReader:
    states: list[VehicleState]
    events: list[str]
    index: int = 0

    def read(self, vehicle_id: VehicleId) -> VehicleState:
        self.events.append("read")
        state = self.states[self.index]
        if self.index < len(self.states) - 1:
            self.index += 1
        return state


@dataclass
class FakeController:
    events: list[str]

    def compute(self, state: VehicleState, target: TargetSpeedCommand) -> ControlCommand:
        self.events.append("compute")
        return ControlCommand(throttle=0.5, brake=0.0, steer=0.0)


@dataclass
class FakeMotionActuator:
    events: list[str]
    applied: list[ControlCommand]

    def apply(self, vehicle_id: VehicleId, command: ControlCommand) -> None:
        self.events.append("apply")
        self.applied.append(command)


@dataclass
class FakeClock:
    events: list[str]
    frame: int = 0

    def tick(self) -> int:
        self.events.append("tick")
        self.frame += 1
        return self.frame


@dataclass
class FakeLogger:
    messages: list[str]

    def info(self, message: str) -> None:
        self.messages.append(message)

    def warn(self, message: str) -> None:
        self.messages.append(message)

    def error(self, message: str) -> None:
        self.messages.append(message)


def test_run_control_loop_orders_calls_and_returns_stats() -> None:
    events: list[str] = []
    logger = FakeLogger(messages=[])
    actuator = FakeMotionActuator(events=events, applied=[])
    loop = RunControlLoop(
        state_reader=FakeStateReader(states=[_state(1, 0.0), _state(2, 1.5)], events=events),
        motion_actuator=actuator,
        clock=FakeClock(events=events),
        logger=logger,
        controller=FakeController(events=events),
    )

    result = loop.run(
        vehicle_id=VehicleId(42),
        target=TargetSpeedCommand(5.0),
        max_steps=2,
    )

    assert events == ["read", "compute", "apply", "tick", "read", "compute", "apply", "tick"]
    assert result.executed_steps == 2
    assert result.last_frame == 2
    assert result.last_speed_mps == 1.5
    assert result.avg_speed_mps == 0.75
    assert len(actuator.applied) == 2
    assert "step=1" in logger.messages[0]
    assert "throttle=0.500" in logger.messages[0]
