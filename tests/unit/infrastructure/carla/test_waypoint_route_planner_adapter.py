from dataclasses import dataclass

import pytest

from vln_carla2.infrastructure.carla.waypoint_route_planner_adapter import (
    CarlaWaypointRoutePlannerAdapter,
)


@dataclass
class _FakeLocation:
    x: float
    y: float
    z: float


@dataclass
class _FakeRotation:
    yaw: float


@dataclass
class _FakeTransform:
    location: _FakeLocation
    rotation: _FakeRotation


class _FakeWaypoint:
    def __init__(
        self,
        *,
        x: float,
        y: float,
        yaw: float,
        road_id: int,
        section_id: int,
        lane_id: int,
        s: float,
    ) -> None:
        self.transform = _FakeTransform(
            location=_FakeLocation(x=x, y=y, z=0.0),
            rotation=_FakeRotation(yaw=yaw),
        )
        self.road_id = road_id
        self.section_id = section_id
        self.lane_id = lane_id
        self.s = s
        self._next: list[_FakeWaypoint] = []

    def next(self, _distance: float) -> list["_FakeWaypoint"]:
        return list(self._next)


class _FakeMap:
    def __init__(self, *, start_waypoint: _FakeWaypoint | None, goal_waypoint: _FakeWaypoint | None) -> None:
        self._start_waypoint = start_waypoint
        self._goal_waypoint = goal_waypoint

    def get_waypoint(self, location: _FakeLocation, project_to_road: bool = True):
        assert project_to_road is True
        if location.x <= 1.0:
            return self._start_waypoint
        return self._goal_waypoint


class _FakeWorld:
    def __init__(self, map_: _FakeMap) -> None:
        self._map = map_

    def get_map(self) -> _FakeMap:
        return self._map


class _FakeCarla:
    class Location(_FakeLocation):
        pass


@dataclass
class _Goal:
    x: float
    y: float
    yaw_deg: float


def test_waypoint_route_planner_builds_route_with_next_chain(monkeypatch) -> None:
    w0 = _FakeWaypoint(x=0.0, y=0.0, yaw=0.0, road_id=1, section_id=0, lane_id=1, s=0.0)
    w1 = _FakeWaypoint(x=1.0, y=0.0, yaw=0.0, road_id=1, section_id=0, lane_id=1, s=1.0)
    w2 = _FakeWaypoint(x=2.0, y=0.0, yaw=0.0, road_id=1, section_id=0, lane_id=1, s=2.0)
    w_goal = _FakeWaypoint(x=3.0, y=0.0, yaw=0.0, road_id=1, section_id=0, lane_id=1, s=3.0)
    w0._next = [w1]
    w1._next = [w2]
    w2._next = [w_goal]
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.waypoint_route_planner_adapter.require_carla",
        lambda: _FakeCarla,
    )

    adapter = CarlaWaypointRoutePlannerAdapter(
        world=_FakeWorld(_FakeMap(start_waypoint=w0, goal_waypoint=w_goal))
    )

    route = adapter.plan_route(
        start_x=0.0,
        start_y=0.0,
        start_yaw_deg=0.0,
        goal=_Goal(x=3.0, y=0.0, yaw_deg=0.0),
        route_step_m=1.0,
        route_max_points=10,
    )

    assert len(route) >= 3
    assert route[0].x == 0.0
    assert route[-1].x >= 2.0


def test_waypoint_route_planner_raises_when_no_next_waypoint(monkeypatch) -> None:
    w0 = _FakeWaypoint(x=0.0, y=0.0, yaw=0.0, road_id=1, section_id=0, lane_id=1, s=0.0)
    w_goal = _FakeWaypoint(x=10.0, y=0.0, yaw=0.0, road_id=1, section_id=0, lane_id=1, s=10.0)
    w0._next = []
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.waypoint_route_planner_adapter.require_carla",
        lambda: _FakeCarla,
    )

    adapter = CarlaWaypointRoutePlannerAdapter(
        world=_FakeWorld(_FakeMap(start_waypoint=w0, goal_waypoint=w_goal))
    )

    with pytest.raises(RuntimeError, match="failed to build waypoint route"):
        adapter.plan_route(
            start_x=0.0,
            start_y=0.0,
            start_yaw_deg=0.0,
            goal=_Goal(x=10.0, y=0.0, yaw_deg=0.0),
            route_step_m=1.0,
            route_max_points=5,
        )

