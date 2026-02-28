from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest

from vln_carla2.usecases.cli.dto import (
    ExpRunRequest,
    ExpWorkflowExecution,
    OperatorRunRequest,
    OperatorWorkflowExecution,
    RuntimeSessionRecord,
    SceneRunRequest,
    SpawnVehicleRequest,
    SpectatorFollowRequest,
    VehicleListRequest,
    VehicleRefInput,
    VehicleSpawnRequest,
)
from vln_carla2.usecases.cli.errors import CliRuntimeError, CliUsageError
from vln_carla2.usecases.cli.service import CliApplicationService
from vln_carla2.usecases.operator.ports.vehicle_dto import VehicleDescriptor


@dataclass
class _FakeWorkflows:
    spectator_follow_calls: list[tuple[SpectatorFollowRequest, int]] = field(default_factory=list)

    def run_scene_workflow(self, request: SceneRunRequest) -> None:
        del request

    def run_operator_workflow(self, request: OperatorRunRequest) -> OperatorWorkflowExecution:
        del request
        return OperatorWorkflowExecution(
            strategy="parallel",
            vehicle_source="resolved",
            actor_id=7,
            operator_ticks=2,
            control_steps=4,
        )

    def run_exp_workflow(self, request: ExpRunRequest) -> ExpWorkflowExecution:
        return ExpWorkflowExecution(
            control_target=request.control_target,
            actor_id=7,
            scene_map_name="Town10HD_Opt",
            imported_objects=1,
            forward_distance_m=request.forward_distance_m,
            traveled_distance_m=21.0,
            entered_forbidden_zone=False,
            control_steps=5,
        )

    def list_vehicles(self, request: VehicleListRequest) -> list[VehicleDescriptor]:
        del request
        return []

    def spawn_vehicle(self, request: VehicleSpawnRequest) -> VehicleDescriptor:
        del request
        return VehicleDescriptor(
            actor_id=1,
            type_id="vehicle.tesla.model3",
            role_name="ego",
            x=0.0,
            y=0.0,
            z=0.0,
        )

    def resolve_vehicle_ref(self, request: SpectatorFollowRequest) -> VehicleDescriptor | None:
        del request
        return VehicleDescriptor(
            actor_id=42,
            type_id="vehicle.tesla.model3",
            role_name="ego",
            x=0.0,
            y=0.0,
            z=0.0,
        )

    def run_spectator_follow_workflow(
        self,
        request: SpectatorFollowRequest,
        *,
        follow_vehicle_id: int,
    ) -> None:
        self.spectator_follow_calls.append((request, follow_vehicle_id))

    def format_vehicle_ref(self, ref: VehicleRefInput) -> str:
        if ref.scheme == "first":
            return "first"
        return f"{ref.scheme}:{ref.value}"


@dataclass
class _FakeServerControl:
    loopback: bool = True
    reachable: bool = False
    launched_process: Any = field(default_factory=lambda: SimpleNamespace(pid=321))
    launch_calls: int = 0
    wait_calls: int = 0
    terminate_calls: int = 0

    def is_loopback_host(self, host: str) -> bool:
        del host
        return self.loopback

    def is_server_reachable(
        self,
        host: str,
        port: int,
        timeout_seconds: float = 0.5,
    ) -> bool:
        del host, port, timeout_seconds
        return self.reachable

    def launch_server(self, request: Any) -> Any:
        del request
        self.launch_calls += 1
        return self.launched_process

    def wait_until_ready(
        self,
        host: str,
        port: int,
        timeout_seconds: float,
        *,
        process: Any | None = None,
    ) -> None:
        del host, port, timeout_seconds, process
        self.wait_calls += 1

    def terminate_server(self, process: Any) -> None:
        del process
        self.terminate_calls += 1

    def process_pid(self, process: Any) -> int:
        return int(process.pid)


@dataclass
class _FakeRuntimeRegistry:
    offscreen_mode: bool | None = None
    records: list[tuple[RuntimeSessionRecord, int | None]] = field(default_factory=list)
    clears: list[tuple[str, int]] = field(default_factory=list)

    def record_session(
        self,
        record: RuntimeSessionRecord,
        *,
        owner_pid: int | None = None,
    ) -> None:
        self.records.append((record, owner_pid))

    def read_offscreen_mode(self, host: str, port: int) -> bool | None:
        del host, port
        return self.offscreen_mode

    def clear_session(self, host: str, port: int) -> None:
        self.clears.append((host, port))


@dataclass
class _FakeSceneTemplateLoader:
    map_name: str = "Town10HD_Opt"
    error: Exception | None = None

    def load_map_name(self, path: str) -> str:
        del path
        if self.error is not None:
            raise self.error
        return self.map_name


def _build_service(
    *,
    workflows: _FakeWorkflows | None = None,
    server: _FakeServerControl | None = None,
    registry: _FakeRuntimeRegistry | None = None,
    loader: _FakeSceneTemplateLoader | None = None,
) -> CliApplicationService:
    return CliApplicationService(
        workflows=workflows or _FakeWorkflows(),
        server_control=server or _FakeServerControl(),
        runtime_registry=registry or _FakeRuntimeRegistry(),
        scene_template_loader=loader or _FakeSceneTemplateLoader(),
    )


def _scene_request(**overrides: Any) -> SceneRunRequest:
    payload = dict(
        host="127.0.0.1",
        port=2000,
        timeout_seconds=10.0,
        map_name="Town10HD_Opt",
        mode="sync",
        fixed_delta_seconds=0.05,
        no_rendering=False,
        tick_sleep_seconds=0.05,
        offscreen=False,
        launch_carla=False,
        reuse_existing_carla=False,
        carla_exe="C:/CARLA/CarlaUE4.exe",
        carla_startup_timeout_seconds=45.0,
        quality_level="Epic",
        with_sound=False,
        keep_carla_server=False,
        scene_import=None,
        scene_export_path=None,
    )
    payload.update(overrides)
    return SceneRunRequest(**payload)


def _exp_request(**overrides: Any) -> ExpRunRequest:
    payload = dict(
        host="127.0.0.1",
        port=2000,
        timeout_seconds=10.0,
        map_name="Town10HD_Opt",
        mode="sync",
        fixed_delta_seconds=0.05,
        no_rendering=False,
        tick_sleep_seconds=0.05,
        offscreen=False,
        launch_carla=False,
        reuse_existing_carla=False,
        carla_exe=None,
        carla_startup_timeout_seconds=45.0,
        quality_level="Epic",
        with_sound=False,
        keep_carla_server=False,
        scene_json="artifacts/scene.json",
        control_target=VehicleRefInput(scheme="role", value="ego"),
        forward_distance_m=20.0,
        target_speed_mps=5.0,
        max_steps=800,
    )
    payload.update(overrides)
    return ExpRunRequest(**payload)


def _spectator_request(**overrides: Any) -> SpectatorFollowRequest:
    payload = dict(
        host="127.0.0.1",
        port=2000,
        timeout_seconds=10.0,
        map_name="Town10HD_Opt",
        mode="sync",
        fixed_delta_seconds=0.05,
        no_rendering=False,
        follow=VehicleRefInput(scheme="role", value="ego"),
        z=20.0,
    )
    payload.update(overrides)
    return SpectatorFollowRequest(**payload)


def test_launch_with_non_loopback_host_raises_usage_error() -> None:
    server = _FakeServerControl(loopback=False)
    service = _build_service(server=server)

    with pytest.raises(CliUsageError, match="only supports local host"):
        service.run_scene(_scene_request(launch_carla=True, host="192.168.1.5"))


def test_server_reachable_without_reuse_raises_usage_error() -> None:
    server = _FakeServerControl(reachable=True)
    service = _build_service(server=server)

    with pytest.raises(CliUsageError, match="already reachable"):
        service.run_scene(_scene_request(launch_carla=True, reuse_existing_carla=False))


def test_launch_requested_without_executable_raises_usage_error() -> None:
    service = _build_service()

    with pytest.raises(CliUsageError, match="--carla-exe is required"):
        service.run_scene(_scene_request(launch_carla=True, carla_exe=None))


def test_launch_success_with_keep_false_terminates_server() -> None:
    server = _FakeServerControl()
    registry = _FakeRuntimeRegistry()
    service = _build_service(server=server, registry=registry)

    result = service.run_scene(_scene_request(launch_carla=True, keep_carla_server=False))

    assert result.launch_report.launched_server_pid == 321
    assert server.terminate_calls == 1
    assert registry.records
    assert registry.clears == [("127.0.0.1", 2000)]


def test_launch_success_with_keep_true_keeps_server_alive() -> None:
    server = _FakeServerControl()
    registry = _FakeRuntimeRegistry()
    service = _build_service(server=server, registry=registry)

    service.run_scene(_scene_request(launch_carla=True, keep_carla_server=True))

    assert server.terminate_calls == 0
    assert registry.records
    assert not registry.clears


def test_exp_scene_template_validation_error_maps_to_runtime_error() -> None:
    loader = _FakeSceneTemplateLoader(error=ValueError("broken scene json"))
    service = _build_service(loader=loader)

    with pytest.raises(CliRuntimeError, match="argument validation failed"):
        service.run_exp(_exp_request())


def test_spectator_follow_skips_when_session_is_offscreen() -> None:
    workflows = _FakeWorkflows()
    registry = _FakeRuntimeRegistry(offscreen_mode=True)
    service = _build_service(workflows=workflows, registry=registry)

    result = service.run_spectator_follow(_spectator_request())

    assert result.skipped_offscreen is True
    assert workflows.spectator_follow_calls == []

