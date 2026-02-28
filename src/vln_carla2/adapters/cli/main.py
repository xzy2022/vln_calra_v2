"""CLI adapter entrypoint helpers."""

from __future__ import annotations

from typing import Sequence

from vln_carla2.usecases.cli.ports.inbound import CliApplicationUseCasePort

from .dispatch import CliDispatchConfig, run_cli as _run_cli


def run_cli(
    argv: Sequence[str] | None,
    app: CliApplicationUseCasePort,
    *,
    config: CliDispatchConfig | None = None,
) -> int:
    """Run CLI with the given app port implementation."""
    return _run_cli(argv, app, config=config)
