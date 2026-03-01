"""CARLA navigation-agent adapters (BasicAgent / BehaviorAgent)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Literal

from vln_carla2.infrastructure.carla import types as carla_types
from vln_carla2.domain.model.simple_command import ControlCommand
from vln_carla2.infrastructure.carla.types import require_carla
from vln_carla2.usecases.control.ports.navigation_agent import NavigationAgent

BehaviorProfile = Literal["cautious", "normal", "aggressive"]

_BEHAVIOR_PROFILES: tuple[str, ...] = ("cautious", "normal", "aggressive")


def _meters_per_second_to_kmh(speed_mps: float) -> float:
    return max(0.0, float(speed_mps) * 3.6)


def _clamp(value: float, *, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _repo_pythonapi_agents_root() -> Path:
    return Path(__file__).resolve().parents[4] / "PythonAPI_Carla_UE4" / "carla"


def _ensure_make_unit_vector_compat() -> None:
    """
    Bridge CARLA API drift for Vector3D.make_unit_vector.

    Some builds require `make_unit_vector(float epsilon)` while others expose
    `make_unit_vector()`. Navigation agent code can call either form.
    """
    carla = carla_types.carla
    if carla is None:
        return

    vector3d_cls = getattr(carla, "Vector3D", None)
    if vector3d_cls is None:
        return

    marker = "__vln_make_unit_vector_compat_applied__"
    if bool(getattr(vector3d_cls, marker, False)):
        return

    original = getattr(vector3d_cls, "make_unit_vector", None)
    if original is None:
        return

    def _compat(self: Any, epsilon: float = 1e-6) -> Any:
        try:
            return original(self, float(epsilon))
        except TypeError:
            return original(self)

    setattr(vector3d_cls, "make_unit_vector", _compat)
    setattr(vector3d_cls, marker, True)


def _import_navigation_class(module_name: str, class_name: str) -> Any:
    try:
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    except ModuleNotFoundError as first_exc:
        agents_root = _repo_pythonapi_agents_root()
        if agents_root.is_dir():
            root_str = str(agents_root)
            if root_str not in sys.path:
                sys.path.append(root_str)
            try:
                module = importlib.import_module(module_name)
                return getattr(module, class_name)
            except ModuleNotFoundError as second_exc:
                raise ModuleNotFoundError(
                    "Failed to import CARLA navigation agents. "
                    "Install/package 'agents.navigation' or add "
                    "'PythonAPI_Carla_UE4/carla' to PYTHONPATH."
                ) from second_exc
        raise ModuleNotFoundError(
            "Failed to import CARLA navigation agents. "
            "Install/package 'agents.navigation' or add "
            "'PythonAPI_Carla_UE4/carla' to PYTHONPATH."
        ) from first_exc


class CarlaBasicNavigationAgentAdapter(NavigationAgent):
    """Adapter over CARLA BasicAgent."""

    def __init__(self, vehicle: Any) -> None:
        _ensure_make_unit_vector_compat()
        basic_agent_cls = _import_navigation_class(
            "agents.navigation.basic_agent",
            "BasicAgent",
        )
        self._agent = basic_agent_cls(vehicle)

    def configure_target_speed_mps(self, target_speed_mps: float) -> None:
        self._agent.set_target_speed(_meters_per_second_to_kmh(target_speed_mps))

    def set_destination(self, x: float, y: float, z: float) -> None:
        carla = require_carla()
        self._agent.set_destination(
            carla.Location(
                x=float(x),
                y=float(y),
                z=float(z),
            )
        )

    def run_step(self) -> ControlCommand:
        control = self._agent.run_step()
        return ControlCommand(
            throttle=_clamp(getattr(control, "throttle", 0.0), low=0.0, high=1.0),
            brake=_clamp(getattr(control, "brake", 0.0), low=0.0, high=1.0),
            steer=_clamp(getattr(control, "steer", 0.0), low=-1.0, high=1.0),
        )

    def done(self) -> bool:
        return bool(self._agent.done())


class CarlaBehaviorNavigationAgentAdapter(NavigationAgent):
    """Adapter over CARLA BehaviorAgent."""

    def __init__(self, vehicle: Any, *, behavior_profile: BehaviorProfile = "normal") -> None:
        if behavior_profile not in _BEHAVIOR_PROFILES:
            raise ValueError(
                "behavior_profile must be one of: "
                f"{','.join(_BEHAVIOR_PROFILES)}"
            )
        _ensure_make_unit_vector_compat()
        behavior_agent_cls = _import_navigation_class(
            "agents.navigation.behavior_agent",
            "BehaviorAgent",
        )
        self._agent = behavior_agent_cls(vehicle, behavior=behavior_profile)
        self._profile_max_speed_kmh = float(getattr(self._agent._behavior, "max_speed", 0.0))

    def configure_target_speed_mps(self, target_speed_mps: float) -> None:
        requested_kmh = _meters_per_second_to_kmh(target_speed_mps)
        max_speed_kmh = min(self._profile_max_speed_kmh, requested_kmh)
        if hasattr(self._agent, "_behavior"):
            setattr(self._agent._behavior, "max_speed", max_speed_kmh)

    def set_destination(self, x: float, y: float, z: float) -> None:
        carla = require_carla()
        self._agent.set_destination(
            carla.Location(
                x=float(x),
                y=float(y),
                z=float(z),
            )
        )

    def run_step(self) -> ControlCommand:
        control = self._agent.run_step()
        return ControlCommand(
            throttle=_clamp(getattr(control, "throttle", 0.0), low=0.0, high=1.0),
            brake=_clamp(getattr(control, "brake", 0.0), low=0.0, high=1.0),
            steer=_clamp(getattr(control, "steer", 0.0), low=-1.0, high=1.0),
        )

    def done(self) -> bool:
        return bool(self._agent.done())
