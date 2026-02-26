"""Application runtime settings."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class SpawnPoint:
    """Fixed spawn point for ego vehicle."""

    x: float = 0.038
    y: float = 15.320
    z: float = 0.15
    yaw: float = 180.0


@dataclass(slots=True)
class Settings:
    """Slice-0 runtime configuration."""

    host: str = "127.0.0.1"
    port: int = 2000
    timeout_seconds: float = 10.0
    map_name: str = "Town10HD_Opt"
    fixed_delta_seconds: float = 0.05
    no_rendering: bool = False
    offscreen: bool = False
    steps: int = 80
    target_speed_mps: float = 5.0
    vehicle_blueprint: str = "vehicle.tesla.model3"
    spawn: SpawnPoint = field(default_factory=SpawnPoint)

    def __post_init__(self) -> None:
        if self.port <= 0:
            raise ValueError("port must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.fixed_delta_seconds <= 0:
            raise ValueError("fixed_delta_seconds must be positive")
        if self.steps <= 0:
            raise ValueError("steps must be > 0")
        if self.target_speed_mps < 0:
            raise ValueError("target_speed_mps must be >= 0")
        if not self.map_name:
            raise ValueError("map_name must not be empty")
        if not self.vehicle_blueprint:
            raise ValueError("vehicle_blueprint must not be empty")

    @property
    def no_rendering_mode(self) -> bool:
        """Compatibility mapping for CARLA WorldSettings API."""
        return self.no_rendering

    @property
    def offscreen_mode(self) -> bool:
        """Compatibility mapping for CARLA server launch settings."""
        return self.offscreen
