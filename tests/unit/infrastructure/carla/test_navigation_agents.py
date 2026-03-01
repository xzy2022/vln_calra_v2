from __future__ import annotations

import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from vln_carla2.infrastructure.carla import navigation_agents


@dataclass
class _FakeControl:
    throttle: float
    brake: float
    steer: float


class _FakeCarla:
    class Location:
        def __init__(self, *, x: float, y: float, z: float) -> None:
            self.x = x
            self.y = y
            self.z = z


class _FakeBasicAgent:
    def __init__(self, vehicle: Any) -> None:
        self.vehicle = vehicle
        self.target_speed_kmh: float | None = None
        self.destination = None
        self.done_result = False
        self.run_step_result = _FakeControl(throttle=0.7, brake=0.0, steer=-0.1)

    def set_target_speed(self, speed_kmh: float) -> None:
        self.target_speed_kmh = speed_kmh

    def set_destination(self, destination: Any) -> None:
        self.destination = destination

    def run_step(self) -> _FakeControl:
        return self.run_step_result

    def done(self) -> bool:
        return self.done_result


class _BehaviorState:
    def __init__(self, max_speed: float) -> None:
        self.max_speed = max_speed


class _FakeBehaviorAgent:
    def __init__(self, vehicle: Any, behavior: str) -> None:
        self.vehicle = vehicle
        self.behavior = behavior
        self._behavior = _BehaviorState(max_speed=40.0)
        self.destination = None
        self.done_result = False
        self.run_step_result = _FakeControl(throttle=1.0, brake=0.0, steer=0.2)

    def set_destination(self, destination: Any) -> None:
        self.destination = destination

    def run_step(self) -> _FakeControl:
        return self.run_step_result

    def done(self) -> bool:
        return self.done_result


def test_make_unit_vector_compat_for_epsilon_required_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Vector3D:
        def __init__(self) -> None:
            self.calls: list[float] = []

        def make_unit_vector(self, epsilon: float) -> tuple[str, float]:
            self.calls.append(float(epsilon))
            return ("eps", float(epsilon))

    fake_carla = types.SimpleNamespace(Vector3D=_Vector3D)
    monkeypatch.setattr(navigation_agents.carla_types, "carla", fake_carla)

    navigation_agents._ensure_make_unit_vector_compat()
    vec = fake_carla.Vector3D()

    assert vec.make_unit_vector() == ("eps", 1e-6)
    assert vec.make_unit_vector(0.2) == ("eps", 0.2)


def test_make_unit_vector_compat_for_noarg_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Vector3D:
        def __init__(self) -> None:
            self.calls = 0

        def make_unit_vector(self) -> str:
            self.calls += 1
            return "ok"

    fake_carla = types.SimpleNamespace(Vector3D=_Vector3D)
    monkeypatch.setattr(navigation_agents.carla_types, "carla", fake_carla)

    navigation_agents._ensure_make_unit_vector_compat()
    vec = fake_carla.Vector3D()

    assert vec.make_unit_vector() == "ok"
    assert vec.make_unit_vector(0.5) == "ok"
    assert vec.calls == 2


def test_basic_navigation_agent_adapter_maps_speed_destination_and_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_agents: list[_FakeBasicAgent] = []

    def _fake_import_navigation_class(module_name: str, class_name: str) -> Any:
        assert module_name == "agents.navigation.basic_agent"
        assert class_name == "BasicAgent"

        def _factory(vehicle: Any) -> _FakeBasicAgent:
            agent = _FakeBasicAgent(vehicle)
            created_agents.append(agent)
            return agent

        return _factory

    monkeypatch.setattr(
        navigation_agents,
        "_import_navigation_class",
        _fake_import_navigation_class,
    )
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.navigation_agents.require_carla",
        lambda: _FakeCarla,
    )

    adapter = navigation_agents.CarlaBasicNavigationAgentAdapter(vehicle=object())
    adapter.configure_target_speed_mps(5.0)
    adapter.set_destination(1.0, 2.0, 3.0)
    command = adapter.run_step()

    agent = created_agents[0]
    assert agent.target_speed_kmh == pytest.approx(18.0)
    assert isinstance(agent.destination, _FakeCarla.Location)
    assert (agent.destination.x, agent.destination.y, agent.destination.z) == (1.0, 2.0, 3.0)
    assert command.throttle == 0.7
    assert command.brake == 0.0
    assert command.steer == -0.1
    assert adapter.done() is False


def test_behavior_navigation_agent_adapter_caps_max_speed_to_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_agents: list[_FakeBehaviorAgent] = []

    def _fake_import_navigation_class(module_name: str, class_name: str) -> Any:
        assert module_name == "agents.navigation.behavior_agent"
        assert class_name == "BehaviorAgent"

        def _factory(vehicle: Any, behavior: str) -> _FakeBehaviorAgent:
            agent = _FakeBehaviorAgent(vehicle=vehicle, behavior=behavior)
            created_agents.append(agent)
            return agent

        return _factory

    monkeypatch.setattr(
        navigation_agents,
        "_import_navigation_class",
        _fake_import_navigation_class,
    )
    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.navigation_agents.require_carla",
        lambda: _FakeCarla,
    )

    adapter = navigation_agents.CarlaBehaviorNavigationAgentAdapter(
        vehicle=object(),
        behavior_profile="aggressive",
    )
    adapter.configure_target_speed_mps(5.0)
    adapter.set_destination(10.0, 20.0, 0.5)
    command = adapter.run_step()

    agent = created_agents[0]
    assert agent.behavior == "aggressive"
    assert agent._behavior.max_speed == pytest.approx(18.0)
    assert isinstance(agent.destination, _FakeCarla.Location)
    assert command.steer == 0.2
    assert adapter.done() is False


def test_behavior_navigation_agent_adapter_rejects_invalid_profile() -> None:
    with pytest.raises(ValueError, match="behavior_profile must be one of"):
        navigation_agents.CarlaBehaviorNavigationAgentAdapter(
            vehicle=object(),
            behavior_profile="invalid",  # type: ignore[arg-type]
        )


def test_import_navigation_class_uses_pythonapi_fallback_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    original_sys_path = list(navigation_agents.sys.path)
    imported_module = types.SimpleNamespace(BasicAgent=object())
    fallback_path = Path(".tmp_test_artifacts/agents_fallback_path")
    fallback_path.mkdir(parents=True, exist_ok=True)

    def _fake_import_module(name: str) -> Any:
        calls.append(name)
        if len(calls) == 1:
            raise ModuleNotFoundError(name)
        return imported_module

    monkeypatch.setattr(navigation_agents.importlib, "import_module", _fake_import_module)
    monkeypatch.setattr(
        navigation_agents,
        "_repo_pythonapi_agents_root",
        lambda: fallback_path,
    )

    got = navigation_agents._import_navigation_class(
        "agents.navigation.basic_agent",
        "BasicAgent",
    )

    assert got is imported_module.BasicAgent
    assert calls == ["agents.navigation.basic_agent", "agents.navigation.basic_agent"]
    assert str(fallback_path) in navigation_agents.sys.path
    navigation_agents.sys.path[:] = original_sys_path


def test_import_navigation_class_raises_clear_error_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        navigation_agents.importlib,
        "import_module",
        lambda _name: (_ for _ in ()).throw(ModuleNotFoundError("agents")),
    )
    monkeypatch.setattr(
        navigation_agents,
        "_repo_pythonapi_agents_root",
        lambda: Path("__missing_agents_root__"),
    )

    with pytest.raises(ModuleNotFoundError, match="Failed to import CARLA navigation agents"):
        navigation_agents._import_navigation_class(
            "agents.navigation.basic_agent",
            "BasicAgent",
        )
