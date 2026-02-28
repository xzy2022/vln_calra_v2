"""Typed CLI orchestration errors."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CliError(Exception):
    """Base class for user-facing CLI use-case errors."""

    message: str

    def __str__(self) -> str:
        return self.message


class CliUsageError(CliError):
    """Raised for CLI semantic/usage errors (maps to exit code 2)."""


class CliRuntimeError(CliError):
    """Raised for runtime failures (maps to exit code 1)."""

