"""Domain longitudinal PID controller used by tracking use case."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class LongitudinalPidController:
    """PID controller that outputs normalized acceleration command in [-1, 1]."""

    kp: float = 1.0
    ki: float = 0.05
    kd: float = 0.0
    integral_limit: float = 10.0
    _error_buffer: deque[float] = field(init=False, default_factory=lambda: deque(maxlen=10))
    _integral_error: float = field(init=False, default=0.0)
    _prev_error: float | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if self.integral_limit <= 0.0:
            raise ValueError("integral_limit must be > 0")

    def reset(self) -> None:
        """Reset internal integration/derivative state."""
        self._error_buffer.clear()
        self._integral_error = 0.0
        self._prev_error = None

    def compute(self, *, speed_mps: float, target_speed_mps: float, dt: float) -> float:
        """Compute normalized command in [-1, 1] from speed tracking error."""
        if dt <= 0.0:
            raise ValueError("dt must be > 0")

        error = float(target_speed_mps) - float(speed_mps)
        self._error_buffer.append(error)
        self._integral_error += error * dt
        self._integral_error = _clamp(
            self._integral_error,
            min_value=-self.integral_limit,
            max_value=self.integral_limit,
        )

        if self._prev_error is None:
            derivative_error = 0.0
        else:
            derivative_error = (error - self._prev_error) / dt
        self._prev_error = error

        output = (
            self.kp * error
            + self.ki * self._integral_error
            + self.kd * derivative_error
        )
        return _clamp(output, min_value=-1.0, max_value=1.0)


def _clamp(value: float, *, min_value: float, max_value: float) -> float:
    return min(max_value, max(min_value, value))

