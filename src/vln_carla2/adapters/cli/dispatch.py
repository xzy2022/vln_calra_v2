"""CLI command dispatch logic."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from .commands import (
    to_exp_run_command,
    to_operator_run_command,
    to_scene_run_command,
    to_spectator_follow_command,
    to_vehicle_list_command,
    to_vehicle_spawn_command,
)
from .parser import build_parser
from .ports import CliApplicationPort
from .presenter import print_vehicle, print_vehicle_list
from .vehicle_ref_parser import VehicleRefParseError


def run_cli(argv: Sequence[str] | None, app: CliApplicationPort) -> int:
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    parser = build_parser(app)
    args = parser.parse_args(raw_argv)
    return dispatch_args(args, app=app, parser=parser)


def dispatch_args(
    args: argparse.Namespace,
    *,
    app: CliApplicationPort,
    parser: argparse.ArgumentParser,
) -> int:
    command_id = getattr(args, "command_id", None)
    if command_id is None:
        parser.print_help()
        return 2

    if command_id == "scene_run":
        command = to_scene_run_command(args)
        return int(app.run_scene(command))

    if command_id == "operator_run":
        try:
            command = to_operator_run_command(args)
        except VehicleRefParseError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 2
        return int(app.run_operator(command))

    if command_id == "exp_run":
        try:
            command = to_exp_run_command(args)
        except VehicleRefParseError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 2
        return int(app.run_exp(command))

    if command_id == "vehicle_list":
        command = to_vehicle_list_command(args)
        try:
            vehicles = app.list_vehicles(command)
            print_vehicle_list(vehicles, output_format=command.output_format)
            return 0
        except Exception as exc:
            print(f"[ERROR] vehicle list failed: {exc}", file=sys.stderr)
            return 1

    if command_id == "vehicle_spawn":
        command = to_vehicle_spawn_command(args)
        try:
            vehicle = app.spawn_vehicle(command)
            print_vehicle(vehicle, output_format=command.output_format)
            return 0
        except Exception as exc:
            print(f"[ERROR] vehicle spawn failed: {exc}", file=sys.stderr)
            return 1

    if command_id == "spectator_follow":
        try:
            command = to_spectator_follow_command(args)
        except VehicleRefParseError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 2
        return int(app.run_spectator_follow(command))

    parser.print_help()
    return 2

