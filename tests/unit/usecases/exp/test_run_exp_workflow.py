from dataclasses import dataclass

import pytest

from vln_carla2.domain.model.forbidden_zone import ForbiddenZone
from vln_carla2.domain.model.point2d import Point2D
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.model.vehicle_state import VehicleState
from vln_carla2.usecases.control.run_control_loop import LoopResult
from vln_carla2.usecases.exp.run_exp_workflow import ExpWorkflowRequest, RunExpWorkflow


def _state(
    *,
    frame: int,
    x: float,
    y: float,
    probe_points_xy: tuple[tuple[float, float], ...] = (),
) -> VehicleState:
    return VehicleState(
        frame=frame,
        x=x,
        y=y,
        z=0.0,
        yaw_deg=0.0,
        vx=0.0,
        vy=0.0,
        vz=0.0,
        speed_mps=1.0,
        forbidden_zone_probe_points_xy=probe_points_xy,
    )


def _zone(*, min_x: float, max_x: float) -> ForbiddenZone:
    return ForbiddenZone(
        vertices=(
            Point2D(x=min_x, y=-1.0),
            Point2D(x=max_x, y=-1.0),
            Point2D(x=max_x, y=1.0),
            Point2D(x=min_x, y=1.0),
        )
    )


@dataclass
class _FakeFollow:
    calls: int = 0
    should_follow: bool = True

    def follow_once(self) -> bool:
        self.calls += 1
        return self.should_follow


@dataclass
class _FakeControlLoop:
    states: list[VehicleState]

    def run(
        self,
        *,
        vehicle_id,
        target,
        max_steps,
        before_step=None,
        on_state=None,
        stop_before_apply=None,
    ) -> LoopResult:
        del vehicle_id, target, max_steps
        executed_steps = 0
        last_frame = -1
        last_speed = 0.0
        speed_samples: list[float] = []

        for step, state in enumerate(self.states, start=1):
            if before_step is not None:
                before_step(step)
            if on_state is not None:
                on_state(state)
            if stop_before_apply is not None and stop_before_apply(step, state):
                break
            executed_steps += 1
            last_frame = state.frame
            last_speed = state.speed_mps
            speed_samples.append(state.speed_mps)

        avg_speed = sum(speed_samples) / len(speed_samples) if speed_samples else 0.0
        return LoopResult(
            executed_steps=executed_steps,
            last_speed_mps=last_speed,
            avg_speed_mps=avg_speed,
            last_frame=last_frame,
        )


def test_run_exp_workflow_stops_on_forward_distance_and_detects_zone_entry() -> None:
    follow = _FakeFollow()
    usecase = RunExpWorkflow(
        control_loop=_FakeControlLoop(
            states=[
                _state(frame=1, x=0.0, y=0.0),
                _state(frame=2, x=10.0, y=0.0),
                _state(frame=3, x=21.0, y=0.0),
            ]
        ),
        follow_vehicle_topdown=follow,
    )

    result = usecase.run(
        ExpWorkflowRequest(
            vehicle_id=VehicleId(7),
            forbidden_zone=_zone(min_x=20.0, max_x=22.0),
            target_speed_mps=5.0,
            forward_distance_m=20.0,
            max_steps=800,
        )
    )

    assert result.control_loop_result.executed_steps == 2
    assert result.sampled_states == 3
    assert result.traveled_distance_m == pytest.approx(21.0)
    assert result.entered_forbidden_zone is True
    assert follow.calls == 3


def test_run_exp_workflow_returns_false_when_log_never_enters_zone() -> None:
    usecase = RunExpWorkflow(
        control_loop=_FakeControlLoop(
            states=[
                _state(frame=1, x=0.0, y=0.0),
                _state(frame=2, x=5.0, y=0.0),
                _state(frame=3, x=8.0, y=0.0),
            ]
        ),
        follow_vehicle_topdown=_FakeFollow(),
    )

    result = usecase.run(
        ExpWorkflowRequest(
            vehicle_id=VehicleId(7),
            forbidden_zone=_zone(min_x=20.0, max_x=22.0),
            forward_distance_m=20.0,
            max_steps=800,
        )
    )

    assert result.entered_forbidden_zone is False


def test_run_exp_workflow_raises_when_follow_target_missing() -> None:
    usecase = RunExpWorkflow(
        control_loop=_FakeControlLoop(states=[_state(frame=1, x=0.0, y=0.0)]),
        follow_vehicle_topdown=_FakeFollow(should_follow=False),
    )

    with pytest.raises(RuntimeError, match="follow target actor not found"):
        usecase.run(
            ExpWorkflowRequest(
                vehicle_id=VehicleId(7),
                forbidden_zone=_zone(min_x=20.0, max_x=22.0),
            )
        )


def test_run_exp_workflow_detects_zone_entry_when_corner_only_hits() -> None:
    usecase = RunExpWorkflow(
        control_loop=_FakeControlLoop(
            states=[
                _state(frame=1, x=19.0, y=0.0),
                _state(
                    frame=2,
                    x=19.6,
                    y=0.0,
                    probe_points_xy=((20.2, 0.0),),  # actor origin outside, probe inside zone
                ),
                _state(frame=3, x=19.8, y=0.0),
            ]
        ),
        follow_vehicle_topdown=_FakeFollow(),
    )

    result = usecase.run(
        ExpWorkflowRequest(
            vehicle_id=VehicleId(7),
            forbidden_zone=_zone(min_x=20.0, max_x=22.0),
            forward_distance_m=20.0,
            max_steps=800,
        )
    )

    assert result.entered_forbidden_zone is True
