"""CLI command dispatch logic."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Sequence

from vln_carla2.usecases.cli.dto import ExpRunResult, OperatorRunResult, SceneRunResult
from vln_carla2.usecases.cli.errors import CliRuntimeError, CliUsageError
from vln_carla2.usecases.cli.ports.inbound import CliApplicationUseCasePort

from .commands import (
    to_exp_run_command,
    to_operator_run_command,
    to_scene_run_command,
    to_spectator_follow_command,
    to_tracking_run_command,
    to_vehicle_list_command,
    to_vehicle_spawn_command,
)
from .mappers import (
    to_exp_run_request,
    to_operator_run_request,
    to_scene_run_request,
    to_spectator_follow_request,
    to_tracking_run_request,
    to_vehicle_list_request,
    to_vehicle_spawn_request,
)
from .parser import build_parser
from .presenter import print_vehicle, print_vehicle_list
from .vehicle_ref_parser import VehicleRefParseError


@dataclass(frozen=True, slots=True)
class CliDispatchConfig:
    default_carla_exe: str | None = None


def run_cli(
    argv: Sequence[str] | None,
    app: CliApplicationUseCasePort,
    *,
    config: CliDispatchConfig | None = None,
) -> int:
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    dispatch_config = config or CliDispatchConfig()
    parser = build_parser(default_carla_exe=dispatch_config.default_carla_exe)
    args = parser.parse_args(raw_argv)
    return dispatch_args(args, app=app, parser=parser)


def dispatch_args(
    args: argparse.Namespace,
    *,
    app: CliApplicationUseCasePort,
    parser: argparse.ArgumentParser,
) -> int:
    command_id = getattr(args, "command_id", None)
    if command_id is None:
        parser.print_help()
        return 2

    if command_id == "scene_run":
        command = to_scene_run_command(args)
        request = to_scene_run_request(command)
        try:
            result = app.run_scene(request)
        except (CliUsageError, CliRuntimeError) as exc:
            return _print_cli_error(exc)
        _print_scene_result(result)
        return 0

    if command_id == "operator_run":
        try:
            command = to_operator_run_command(args)
        except VehicleRefParseError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 2
        request = to_operator_run_request(command)
        try:
            result = app.run_operator(request)
        except (CliUsageError, CliRuntimeError) as exc:
            return _print_cli_error(exc)
        _print_operator_result(result)
        return 0

    if command_id == "exp_run":
        try:
            command = to_exp_run_command(args)
        except VehicleRefParseError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 2
        request = to_exp_run_request(command)
        try:
            result = app.run_exp(request)
        except (CliUsageError, CliRuntimeError) as exc:
            return _print_cli_error(exc)
        _print_exp_result(result)
        return 0

    if command_id == "tracking_run":
        try:
            command = to_tracking_run_command(args)
        except VehicleRefParseError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 2
        request = to_tracking_run_request(command)
        try:
            result = app.run_tracking(request)
        except (CliUsageError, CliRuntimeError) as exc:
            return _print_cli_error(exc)
        _print_tracking_result(result)
        return 0

    if command_id == "vehicle_list":
        command = to_vehicle_list_command(args)
        request = to_vehicle_list_request(command)
        try:
            vehicles = app.list_vehicles(request)
        except (CliUsageError, CliRuntimeError) as exc:
            return _print_cli_error(exc)
        print_vehicle_list(vehicles, output_format=command.output_format)
        return 0

    if command_id == "vehicle_spawn":
        command = to_vehicle_spawn_command(args)
        request = to_vehicle_spawn_request(command)
        try:
            vehicle = app.spawn_vehicle(request)
        except (CliUsageError, CliRuntimeError) as exc:
            return _print_cli_error(exc)
        print_vehicle(vehicle, output_format=command.output_format)
        return 0

    if command_id == "spectator_follow":
        try:
            command = to_spectator_follow_command(args)
        except VehicleRefParseError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 2
        request = to_spectator_follow_request(command)
        try:
            result = app.run_spectator_follow(request)
        except (CliUsageError, CliRuntimeError) as exc:
            return _print_cli_error(exc)

        if result.skipped_offscreen:
            print("[WARN] spectator follow skipped in offscreen mode.")
            return 0
        if result.interrupted:
            print("[INFO] interrupted by Ctrl+C")
        print(
            f"[INFO] spectator follow stopped mode={result.mode} "
            f"host={result.host} port={result.port}"
        )
        return 0

    parser.print_help()
    return 2


def _print_scene_result(result: SceneRunResult) -> None:
    _print_launch_report(
        host=result.host,
        port=result.port,
        reused_existing_server=result.launch_report.reused_existing_server,
        launched_server_pid=result.launch_report.launched_server_pid,
    )
    _print_warnings(result.warnings)
    if result.interrupted:
        print("[INFO] interrupted by Ctrl+C")
    print(f"[INFO] runtime stopped mode={result.mode} host={result.host} port={result.port}")


def _print_operator_result(result: OperatorRunResult) -> None:
    _print_launch_report(
        host=result.host,
        port=result.port,
        reused_existing_server=result.launch_report.reused_existing_server,
        launched_server_pid=result.launch_report.launched_server_pid,
    )
    _print_warnings(result.warnings)
    if result.interrupted:
        print("[INFO] interrupted by Ctrl+C")
        return

    if result.execution is None:
        raise RuntimeError("operator run result missing execution payload")

    execution = result.execution
    print(
        "[INFO] operator workflow finished "
        f"strategy={execution.strategy} vehicle_source={execution.vehicle_source} "
        f"actor_id={execution.actor_id} "
        f"operator_ticks={execution.operator_ticks} "
        f"control_steps={execution.control_steps} "
        f"host={result.host} port={result.port}"
    )


def _print_exp_result(result: ExpRunResult) -> None:
    _print_launch_report(
        host=result.host,
        port=result.port,
        reused_existing_server=result.launch_report.reused_existing_server,
        launched_server_pid=result.launch_report.launched_server_pid,
    )
    _print_warnings(result.warnings)
    if result.interrupted:
        print("[INFO] interrupted by Ctrl+C")
        return

    if result.execution is None:
        raise RuntimeError("exp run result missing execution payload")

    execution = result.execution
    print(
        "[INFO] exp workflow finished "
        f"control_target={_format_vehicle_ref(execution.control_target.scheme, execution.control_target.value)} "
        f"actor_id={execution.actor_id} "
        f"map_name={execution.scene_map_name} "
        f"imported_objects={execution.imported_objects} "
        f"forward_distance_m={execution.forward_distance_m:.3f} "
        f"traveled_distance_m={execution.traveled_distance_m:.3f} "
        f"entered_forbidden_zone={execution.entered_forbidden_zone} "
        f"control_steps={execution.control_steps} "
        f"host={result.host} port={result.port}"
    )
    if execution.start_transform is not None and execution.goal_transform is not None:
        start = execution.start_transform
        goal = execution.goal_transform
        print(
            "[INFO] episode transforms "
            f"start=(x={start.x:.3f},y={start.y:.3f},z={start.z:.3f},yaw={start.yaw:.3f}) "
            f"goal=(x={goal.x:.3f},y={goal.y:.3f},z={goal.z:.3f},yaw={goal.yaw:.3f})"
        )
    status = "ENTERED" if execution.entered_forbidden_zone else "CLEAR"
    print(
        "[RESULT] forbidden_zone="
        f"{status} entered_forbidden_zone={execution.entered_forbidden_zone}"
    )
    if execution.metrics_path is not None:
        print(f"[INFO] metrics saved path={execution.metrics_path}")


def _print_tracking_result(result) -> None:
    _print_launch_report(
        host=result.host,
        port=result.port,
        reused_existing_server=result.launch_report.reused_existing_server,
        launched_server_pid=result.launch_report.launched_server_pid,
    )
    _print_warnings(result.warnings)
    if result.interrupted:
        print("[INFO] interrupted by Ctrl+C")
        return

    if result.execution is None:
        raise RuntimeError("tracking run result missing execution payload")

    execution = result.execution
    print(
        "[INFO] tracking workflow finished "
        f"control_target={_format_vehicle_ref(execution.control_target.scheme, execution.control_target.value)} "
        f"actor_id={execution.actor_id} "
        f"map_name={execution.scene_map_name} "
        f"imported_objects={execution.imported_objects} "
        f"reached_goal={execution.reached_goal} "
        f"termination_reason={execution.termination_reason} "
        f"executed_steps={execution.executed_steps} "
        f"final_distance_to_goal_m={execution.final_distance_to_goal_m:.3f} "
        f"final_yaw_error_deg={execution.final_yaw_error_deg:.3f} "
        f"route_points={execution.route_points} "
        f"host={result.host} port={result.port}"
    )
    if execution.start_transform is not None and execution.goal_transform is not None:
        start = execution.start_transform
        goal = execution.goal_transform
        print(
            "[INFO] episode transforms "
            f"start=(x={start.x:.3f},y={start.y:.3f},z={start.z:.3f},yaw={start.yaw:.3f}) "
            f"goal=(x={goal.x:.3f},y={goal.y:.3f},z={goal.z:.3f},yaw={goal.yaw:.3f})"
        )


def _print_launch_report(
    *,
    host: str,
    port: int,
    reused_existing_server: bool,
    launched_server_pid: int | None,
) -> None:
    if reused_existing_server:
        print(f"[INFO] reusing existing CARLA on {host}:{port}")
    if launched_server_pid is not None:
        print(f"[INFO] launched CARLA pid={launched_server_pid} on {host}:{port}")


def _print_warnings(warnings: tuple[str, ...]) -> None:
    for warning in warnings:
        print(f"[WARN] {warning}")


def _print_cli_error(exc: CliUsageError | CliRuntimeError) -> int:
    print(f"[ERROR] {exc}", file=sys.stderr)
    if isinstance(exc, CliUsageError):
        return 2
    return 1


def _format_vehicle_ref(scheme: str, value: str | None) -> str:
    if scheme == "first":
        return "first"
    return f"{scheme}:{value}"
