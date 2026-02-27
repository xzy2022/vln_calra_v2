"""CLI adapter entrypoint helpers."""

from __future__ import annotations

from typing import Sequence

from .dispatch import run_cli as _run_cli
from .ports import CliApplicationPort


def run_cli(argv: Sequence[str] | None, app: CliApplicationPort) -> int:
    """Run CLI with the given app port implementation."""
    return _run_cli(argv, app)

