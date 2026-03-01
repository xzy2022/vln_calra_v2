from dataclasses import dataclass

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.model.vehicle_state import VehicleState
from vln_carla2.usecases.tracking.models import RoutePoint
from vln_carla2.usecases.tracking.run_tracking_loop import RunTrackingLoop, TrackingRequest


def _state(*, frame: int, x: float, y: float, yaw_deg: float, speed_mps: float) -> VehicleState:
    return VehicleState(
        frame=frame,
        x=x,
        y=y,
        z=0.0,
        yaw_deg=yaw_deg,
        vx=speed_mps,
        vy=0.0,
        vz=0.0,
        speed_mps=speed_mps,
    )


@dataclass
class _FakeStateReader:
    states: list[VehicleState]
    fail_with_actor_missing: bool = False
    index: int = 0

    def read(self, _vehicle_id: VehicleId) -> VehicleState:
        if self.fail_with_actor_missing:
            raise RuntimeError("Vehicle actor not found: id=42")
        state = self.states[self.index]
        if self.index < len(self.states) - 1:
            self.index += 1
        return state


@dataclass
class _FakeMotionActuator:
    applied: list[object]

    def apply(self, _vehicle_id: VehicleId, command: object) -> None:
        self.applied.append(command)


@dataclass
class _FakeClock:
    frame: int = 0

    def tick(self) -> int:
        self.frame += 1
        return self.frame


@dataclass
class _FakeLogger:
    infos: list[str]
    warns: list[str]
    errors: list[str]

    def info(self, message: str) -> None:
        self.infos.append(message)

    def warn(self, message: str) -> None:
        self.warns.append(message)

    def error(self, message: str) -> None:
        self.errors.append(message)


@dataclass
class _FakeRoutePlanner:
    route: tuple[RoutePoint, ...]
    raise_error: bool = False

    def plan_route(
        self,
        *,
        start_x: float,
        start_y: float,
        start_yaw_deg: float,
        goal,
        route_step_m: float,
        route_max_points: int,
    ) -> tuple[RoutePoint, ...]:
        del start_x, start_y, start_yaw_deg, goal, route_step_m, route_max_points
        if self.raise_error:
            raise RuntimeError("route planner down")
        return self.route


def test_tracking_loop_reaches_goal_and_stops() -> None:
    route = (
        RoutePoint(x=0.0, y=0.0, yaw_deg=0.0),
        RoutePoint(x=5.0, y=0.0, yaw_deg=0.0),
        RoutePoint(x=10.0, y=0.0, yaw_deg=0.0),
    )
    actuator = _FakeMotionActuator(applied=[])
    loop = RunTrackingLoop(
        state_reader=_FakeStateReader(
            states=[
                _state(frame=1, x=0.0, y=0.0, yaw_deg=0.0, speed_mps=0.0),   # initial
                _state(frame=2, x=0.0, y=0.0, yaw_deg=0.0, speed_mps=2.0),   # step 1
                _state(frame=3, x=9.8, y=0.0, yaw_deg=0.0, speed_mps=1.0),   # step 2 -> reached
            ]
        ),
        motion_actuator=actuator,
        clock=_FakeClock(),
        logger=_FakeLogger(infos=[], warns=[], errors=[]),
        route_planner=_FakeRoutePlanner(route=route),
    )

    result = loop.run(
        TrackingRequest(
            vehicle_id=VehicleId(42),
            goal_x=10.0,
            goal_y=0.0,
            goal_yaw_deg=0.0,
            max_steps=20,
        )
    )

    assert result.reached_goal is True
    assert result.termination_reason == "goal_reached"
    assert result.executed_steps == 1
    assert len(actuator.applied) == 1
    assert len(result.step_traces) == 1
    trace = result.step_traces[0]
    assert trace.step == 1
    assert trace.frame == 1
    assert trace.actual_x == 0.0
    assert trace.actual_y == 0.0
    assert trace.target_x == 5.0
    assert trace.target_y == 0.0
    assert trace.distance_to_goal_m == 10.0


def test_tracking_loop_returns_no_progress_when_distance_not_improving() -> None:
    route = (
        RoutePoint(x=0.0, y=0.0, yaw_deg=0.0),
        RoutePoint(x=2.0, y=0.0, yaw_deg=0.0),
    )
    loop = RunTrackingLoop(
        state_reader=_FakeStateReader(
            states=[
                _state(frame=1, x=0.0, y=0.0, yaw_deg=0.0, speed_mps=0.0),
                _state(frame=2, x=0.0, y=0.0, yaw_deg=0.0, speed_mps=0.0),
                _state(frame=3, x=0.0, y=0.0, yaw_deg=0.0, speed_mps=0.0),
                _state(frame=4, x=0.0, y=0.0, yaw_deg=0.0, speed_mps=0.0),
            ]
        ),
        motion_actuator=_FakeMotionActuator(applied=[]),
        clock=_FakeClock(),
        logger=_FakeLogger(infos=[], warns=[], errors=[]),
        route_planner=_FakeRoutePlanner(route=route),
    )

    result = loop.run(
        TrackingRequest(
            vehicle_id=VehicleId(42),
            goal_x=50.0,
            goal_y=0.0,
            goal_yaw_deg=0.0,
            max_steps=20,
            no_progress_max_steps=3,
            no_progress_min_improvement_m=0.1,
        )
    )

    assert result.reached_goal is False
    assert result.termination_reason == "no_progress"
    assert result.executed_steps == 2
    assert len(result.step_traces) == 2


def test_tracking_loop_returns_actor_missing_when_vehicle_not_found() -> None:
    loop = RunTrackingLoop(
        state_reader=_FakeStateReader(states=[], fail_with_actor_missing=True),
        motion_actuator=_FakeMotionActuator(applied=[]),
        clock=_FakeClock(),
        logger=_FakeLogger(infos=[], warns=[], errors=[]),
        route_planner=_FakeRoutePlanner(route=()),
    )

    result = loop.run(
        TrackingRequest(
            vehicle_id=VehicleId(42),
            goal_x=10.0,
            goal_y=0.0,
            goal_yaw_deg=0.0,
        )
    )

    assert result.termination_reason == "actor_missing"
    assert result.route_points == ()
    assert result.step_traces == ()


def test_tracking_loop_returns_route_failed_when_route_planner_raises() -> None:
    loop = RunTrackingLoop(
        state_reader=_FakeStateReader(
            states=[_state(frame=1, x=0.0, y=0.0, yaw_deg=0.0, speed_mps=0.0)]
        ),
        motion_actuator=_FakeMotionActuator(applied=[]),
        clock=_FakeClock(),
        logger=_FakeLogger(infos=[], warns=[], errors=[]),
        route_planner=_FakeRoutePlanner(route=(), raise_error=True),
    )

    result = loop.run(
        TrackingRequest(
            vehicle_id=VehicleId(42),
            goal_x=10.0,
            goal_y=0.0,
            goal_yaw_deg=0.0,
        )
    )

    assert result.termination_reason == "route_failed"
    assert result.reached_goal is False
    assert result.step_traces == ()
