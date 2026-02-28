"""Compatibility shim for CLI app port type."""

from vln_carla2.usecases.cli.ports.inbound import CliApplicationUseCasePort

CliApplicationPort = CliApplicationUseCasePort

__all__ = ["CliApplicationPort"]

