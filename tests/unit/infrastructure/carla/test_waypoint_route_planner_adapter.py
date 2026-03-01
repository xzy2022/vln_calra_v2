from dataclasses import dataclass
from typing import Any

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
    def __init__(self, *, x: float, y: float, yaw: float) -> None:
        self.transform = _FakeTransform(
            location=_FakeLocation(x=x, y=y, z=0.0),
            rotation=_FakeRotation(yaw=yaw),
        )


class _FakeMap:
    def __init__(
        self,
        *,
        start_waypoint: _FakeWaypoint | None,
        goal_waypoint: _FakeWaypoint | None,
        trace_items: list[Any] | None = None,
    ) -> None:
        self._start_waypoint = start_waypoint
        self._goal_waypoint = goal_waypoint
        self._get_waypoint_calls = 0
        self.trace_items = list(trace_items or [])
        self.last_sampling_resolution: float | None = None
        self.last_trace_start: _FakeLocation | None = None
        self.last_trace_goal: _FakeLocation | None = None

    def get_waypoint(self, location: _FakeLocation, project_to_road: bool = True):
        assert project_to_road is True
        self._get_waypoint_calls += 1
        if self._get_waypoint_calls == 1:
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


class _FakeGlobalRoutePlanner:
    def __init__(self, world_map: _FakeMap, sampling_resolution: float) -> None:
        self._world_map = world_map
        self._sampling_resolution = float(sampling_resolution)

    def trace_route(
        self,
        start_location: _FakeLocation,
        goal_location: _FakeLocation,
    ) -> list[Any]:
        self._world_map.last_sampling_resolution = self._sampling_resolution
        self._world_map.last_trace_start = start_location
        self._world_map.last_trace_goal = goal_location
        return list(self._world_map.trace_items)


@dataclass
class _Goal:
    x: float
    y: float
    yaw_deg: float


def test_waypoint_route_planner_builds_route_with_global_trace(monkeypatch) -> None:
    w0 = _FakeWaypoint(x=0.0, y=0.0, yaw=0.0)
    w1 = _FakeWaypoint(x=1.0, y=0.0, yaw=0.0)
    w2 = _FakeWaypoint(x=2.0, y=0.0, yaw=5.0)
    map_ = _FakeMap(
        start_waypoint=w0,
        goal_waypoint=w2,
        trace_items=[(w0, "LANEFOLLOW"), (w1, "LANEFOLLOW"), (w2, "LANEFOLLOW")],
    )
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.waypoint_route_planner_adapter.require_carla",
        lambda: _FakeCarla,
    )
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.waypoint_route_planner_adapter._require_global_route_planner",
        lambda: _FakeGlobalRoutePlanner,
    )

    adapter = CarlaWaypointRoutePlannerAdapter(world=_FakeWorld(map_))
    route = adapter.plan_route(
        start_x=0.0,
        start_y=0.0,
        start_yaw_deg=0.0,
        goal=_Goal(x=2.0, y=0.0, yaw_deg=5.0),
        route_step_m=1.5,
        route_max_points=10,
    )

    assert len(route) == 3
    assert route[0].x == 0.0
    assert route[-1].x == 2.0
    assert map_.last_sampling_resolution == 1.5
    assert map_.last_trace_start is not None
    assert map_.last_trace_goal is not None


def test_waypoint_route_planner_raises_when_trace_empty(monkeypatch) -> None:
    w0 = _FakeWaypoint(x=0.0, y=0.0, yaw=0.0)
    w_goal = _FakeWaypoint(x=10.0, y=0.0, yaw=0.0)
    map_ = _FakeMap(start_waypoint=w0, goal_waypoint=w_goal, trace_items=[])
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.waypoint_route_planner_adapter.require_carla",
        lambda: _FakeCarla,
    )
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.waypoint_route_planner_adapter._require_global_route_planner",
        lambda: _FakeGlobalRoutePlanner,
    )

    adapter = CarlaWaypointRoutePlannerAdapter(world=_FakeWorld(map_))
    with pytest.raises(RuntimeError, match="failed to build waypoint route: points=0"):
        adapter.plan_route(
            start_x=0.0,
            start_y=0.0,
            start_yaw_deg=0.0,
            goal=_Goal(x=10.0, y=0.0, yaw_deg=0.0),
            route_step_m=1.0,
            route_max_points=5,
        )


def test_waypoint_route_planner_raises_when_route_exceeds_max_points(monkeypatch) -> None:
    w0 = _FakeWaypoint(x=0.0, y=0.0, yaw=0.0)
    w_goal = _FakeWaypoint(x=10.0, y=0.0, yaw=0.0)
    trace = [(_FakeWaypoint(x=float(idx), y=0.0, yaw=0.0), "LANEFOLLOW") for idx in range(6)]
    map_ = _FakeMap(start_waypoint=w0, goal_waypoint=w_goal, trace_items=trace)
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.waypoint_route_planner_adapter.require_carla",
        lambda: _FakeCarla,
    )
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.waypoint_route_planner_adapter._require_global_route_planner",
        lambda: _FakeGlobalRoutePlanner,
    )

    adapter = CarlaWaypointRoutePlannerAdapter(world=_FakeWorld(map_))
    with pytest.raises(RuntimeError, match="failed to build waypoint route: points=6"):
        adapter.plan_route(
            start_x=0.0,
            start_y=0.0,
            start_yaw_deg=0.0,
            goal=_Goal(x=10.0, y=0.0, yaw_deg=0.0),
            route_step_m=1.0,
            route_max_points=5,
        )


def test_waypoint_route_planner_fails_fast_when_global_route_planner_unavailable(
    monkeypatch,
) -> None:
    w0 = _FakeWaypoint(x=0.0, y=0.0, yaw=0.0)
    w_goal = _FakeWaypoint(x=10.0, y=0.0, yaw=0.0)
    map_ = _FakeMap(start_waypoint=w0, goal_waypoint=w_goal, trace_items=[])
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.waypoint_route_planner_adapter.require_carla",
        lambda: _FakeCarla,
    )

    def _raise_import_error() -> type[Any]:
        raise ModuleNotFoundError("No module named 'agents'")

    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.waypoint_route_planner_adapter._import_global_route_planner",
        _raise_import_error,
    )

    adapter = CarlaWaypointRoutePlannerAdapter(world=_FakeWorld(map_))
    with pytest.raises(ModuleNotFoundError, match="GlobalRoutePlanner is unavailable"):
        adapter.plan_route(
            start_x=0.0,
            start_y=0.0,
            start_yaw_deg=0.0,
            goal=_Goal(x=10.0, y=0.0, yaw_deg=0.0),
            route_step_m=1.0,
            route_max_points=10,
        )


def test_waypoint_route_planner_raises_when_start_waypoint_missing(monkeypatch) -> None:
    w_goal = _FakeWaypoint(x=10.0, y=0.0, yaw=0.0)
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.waypoint_route_planner_adapter.require_carla",
        lambda: _FakeCarla,
    )
    adapter = CarlaWaypointRoutePlannerAdapter(
        world=_FakeWorld(_FakeMap(start_waypoint=None, goal_waypoint=w_goal))
    )

    with pytest.raises(RuntimeError, match="start waypoint not found near"):
        adapter.plan_route(
            start_x=0.0,
            start_y=0.0,
            start_yaw_deg=0.0,
            goal=_Goal(x=10.0, y=0.0, yaw_deg=0.0),
            route_step_m=1.0,
            route_max_points=10,
        )


def test_waypoint_route_planner_raises_when_goal_waypoint_missing(monkeypatch) -> None:
    w0 = _FakeWaypoint(x=0.0, y=0.0, yaw=0.0)
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.waypoint_route_planner_adapter.require_carla",
        lambda: _FakeCarla,
    )
    adapter = CarlaWaypointRoutePlannerAdapter(
        world=_FakeWorld(_FakeMap(start_waypoint=w0, goal_waypoint=None))
    )

    with pytest.raises(RuntimeError, match="goal waypoint not found near"):
        adapter.plan_route(
            start_x=0.0,
            start_y=0.0,
            start_yaw_deg=0.0,
            goal=_Goal(x=10.0, y=0.0, yaw_deg=0.0),
            route_step_m=1.0,
            route_max_points=10,
        )
