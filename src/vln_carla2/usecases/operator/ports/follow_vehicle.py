"""Port for optional spectator follow behavior in operator loop."""

from typing import Protocol


class FollowVehicleProtocol(Protocol):
    """Adjust spectator to follow the currently tracked vehicle."""

    def follow_once(self) -> bool:
        ...
