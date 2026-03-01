"""Logger port for tracking use case."""

from typing import Protocol


class Logger(Protocol):
    """Minimal logger API."""

    def info(self, message: str) -> None:
        ...

    def warn(self, message: str) -> None:
        ...

    def error(self, message: str) -> None:
        ...

