from dataclasses import dataclass

import pytest

from vln_carla2.domain.model.simple_command import ControlCommand
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.model.vehicle_state import VehicleState
from vln_carla2.usecases.control.run_agent_control_loop import RunAgentControlLoop


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
        del vehicle_id
        self.events.append("read")
        state = self.states[self.index]
        if self.index < len(self.states) - 1:
            self.index += 1
        return state


@dataclass
class FakeNavigationAgent:
    events: list[str]
    done_after_checks: int = 9999
    done_checks: int = 0
    configured_target_speed_mps: float | None = None
    destination: tuple[float, float, float] | None = None

    def configure_target_speed_mps(self, target_speed_mps: float) -> None:
        self.events.append("configure")
        self.configured_target_speed_mps = target_speed_mps

    def set_destination(self, x: float, y: float, z: float) -> None:
        self.events.append("set_destination")
        self.destination = (x, y, z)

    def run_step(self) -> ControlCommand:
        self.events.append("run_step")
        return ControlCommand(throttle=0.4, brake=0.0, steer=0.1)

    def done(self) -> bool:
        self.events.append("done")
        self.done_checks += 1
        return self.done_checks > self.done_after_checks


@dataclass
class FakeMotionActuator:
    events: list[str]
    applied: list[ControlCommand]

    def apply(self, vehicle_id: VehicleId, command: ControlCommand) -> None:
        del vehicle_id
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


def test_run_agent_control_loop_orders_calls_and_returns_stats() -> None:
    events: list[str] = []
    logger = FakeLogger(messages=[])
    agent = FakeNavigationAgent(events=events)
    actuator = FakeMotionActuator(events=events, applied=[])
    loop = RunAgentControlLoop(
        state_reader=FakeStateReader(states=[_state(1, 0.0), _state(2, 1.5)], events=events),
        motion_actuator=actuator,
        clock=FakeClock(events=events),
        logger=logger,
        navigation_agent=agent,
    )

    result = loop.run(
        vehicle_id=VehicleId(42),
        target_speed_mps=5.0,
        destination_x=10.0,
        destination_y=20.0,
        destination_z=0.5,
        max_steps=2,
    )

    assert agent.configured_target_speed_mps == 5.0
    assert agent.destination == (10.0, 20.0, 0.5)
    assert events == [
        "configure",
        "set_destination",
        "read",
        "done",
        "run_step",
        "apply",
        "tick",
        "read",
        "done",
        "run_step",
        "apply",
        "tick",
    ]
    assert result.executed_steps == 2
    assert result.last_frame == 2
    assert result.last_speed_mps == 1.5
    assert result.avg_speed_mps == 0.75
    assert len(actuator.applied) == 2
    assert "step=1" in logger.messages[0]


def test_run_agent_control_loop_stops_when_agent_done() -> None:
    events: list[str] = []
    logger = FakeLogger(messages=[])
    loop = RunAgentControlLoop(
        state_reader=FakeStateReader(states=[_state(1, 0.0), _state(2, 1.0)], events=events),
        motion_actuator=FakeMotionActuator(events=events, applied=[]),
        clock=FakeClock(events=events),
        logger=logger,
        navigation_agent=FakeNavigationAgent(events=events, done_after_checks=1),
    )

    result = loop.run(
        vehicle_id=VehicleId(9),
        target_speed_mps=3.0,
        destination_x=1.0,
        destination_y=2.0,
        destination_z=0.0,
        max_steps=3,
    )

    assert result.executed_steps == 1
    assert result.last_frame == 1
    assert "agent_done=true" in logger.messages[-1]


def test_run_agent_control_loop_calls_hooks() -> None:
    events: list[str] = []
    sampled_frames: list[int] = []
    hook_steps: list[int] = []
    loop = RunAgentControlLoop(
        state_reader=FakeStateReader(states=[_state(1, 0.0), _state(2, 1.0)], events=events),
        motion_actuator=FakeMotionActuator(events=events, applied=[]),
        clock=FakeClock(events=events),
        logger=FakeLogger(messages=[]),
        navigation_agent=FakeNavigationAgent(events=events),
    )

    def _before(step: int) -> None:
        hook_steps.append(step)
        events.append("before")

    def _on_state(state: VehicleState) -> None:
        sampled_frames.append(state.frame)
        events.append("on_state")

    result = loop.run(
        vehicle_id=VehicleId(5),
        target_speed_mps=3.0,
        destination_x=7.0,
        destination_y=8.0,
        destination_z=0.1,
        max_steps=2,
        before_step=_before,
        on_state=_on_state,
    )

    assert result.executed_steps == 2
    assert hook_steps == [1, 2]
    assert sampled_frames == [1, 2]
    assert events.count("before") == 2
    assert events.count("on_state") == 2


def test_run_agent_control_loop_validates_parameters() -> None:
    loop = RunAgentControlLoop(
        state_reader=FakeStateReader(states=[_state(1, 0.0)], events=[]),
        motion_actuator=FakeMotionActuator(events=[], applied=[]),
        clock=FakeClock(events=[]),
        logger=FakeLogger(messages=[]),
        navigation_agent=FakeNavigationAgent(events=[]),
    )

    with pytest.raises(ValueError, match="max_steps must be > 0"):
        loop.run(
            vehicle_id=VehicleId(1),
            target_speed_mps=1.0,
            destination_x=0.0,
            destination_y=0.0,
            destination_z=0.0,
            max_steps=0,
        )

    with pytest.raises(ValueError, match="target_speed_mps must be >= 0"):
        loop.run(
            vehicle_id=VehicleId(1),
            target_speed_mps=-1.0,
            destination_x=0.0,
            destination_y=0.0,
            destination_z=0.0,
            max_steps=1,
        )

