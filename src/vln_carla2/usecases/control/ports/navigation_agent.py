"""Navigation-agent port used by control use cases."""

from typing import Protocol

from vln_carla2.domain.model.simple_command import ControlCommand


class NavigationAgent(Protocol):
    """Wrapper over agent-style planners that output low-level controls."""

    def configure_target_speed_mps(self, target_speed_mps: float) -> None:
        """Configure target speed in m/s."""

    def set_destination(self, x: float, y: float, z: float) -> None:
        """Configure destination in world coordinates."""

    def run_step(self) -> ControlCommand:
        """Compute one low-level control command."""

    def done(self) -> bool:
        """Return True when destination is reached."""

