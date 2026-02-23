"""Logger port used by application use cases."""

from typing import Protocol


class Logger(Protocol):
    """Minimal logging API for use cases."""

    def info(self, message: str) -> None:
        """Log info message."""

    def warn(self, message: str) -> None:
        """Log warning message."""

    def error(self, message: str) -> None:
        """Log error message."""

