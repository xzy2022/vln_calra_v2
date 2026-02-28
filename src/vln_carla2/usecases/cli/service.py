"""CLI orchestration service implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vln_carla2.usecases.cli.dto import (
    ExpRunRequest,
    ExpRunResult,
    LaunchCarlaServerRequest,
    LaunchReport,
    OperatorRunRequest,
    OperatorRunResult,
    RuntimeSessionRecord,
    SceneRunRequest,
    SceneRunResult,
    SpectatorFollowRequest,
    SpectatorFollowResult,
    VehicleListRequest,
    VehicleSpawnRequest,
)
from vln_carla2.usecases.cli.errors import CliRuntimeError, CliUsageError
from vln_carla2.usecases.cli.ports.inbound import CliApplicationUseCasePort
from vln_carla2.usecases.cli.ports.runtime_session_registry import RuntimeSessionRegistryPort
from vln_carla2.usecases.cli.ports.scene_template_loader import SceneTemplateLoaderPort
from vln_carla2.usecases.cli.ports.server_control import CarlaServerControlPort
from vln_carla2.usecases.cli.ports.workflows import CliWorkflowPort
from vln_carla2.usecases.shared.vehicle_dto import VehicleDescriptor

_WARN_OFFSCREEN = "--offscreen only affects launched CARLA server (enable --launch-carla)."
_WARN_NO_RENDERING = (
    "--no-rendering applies world settings, but window visibility depends on existing "
    "CARLA server startup flags."
)


@dataclass(slots=True)
class _LaunchDecision:
    launch_report: LaunchReport
    launched_process: Any | None = None


@dataclass(slots=True)
class CliApplicationService(CliApplicationUseCasePort):
    """Use-case facade consumed by CLI adapter."""

    workflows: CliWorkflowPort
    server_control: CarlaServerControlPort
    runtime_registry: RuntimeSessionRegistryPort
    scene_template_loader: SceneTemplateLoaderPort

    def run_scene(self, request: SceneRunRequest) -> SceneRunResult:
        warnings = self._collect_runtime_warnings(request)
        launch_decision = self._prepare_launch_if_needed(request)
        interrupted = False
        try:
            self.workflows.run_scene_workflow(request)
        except KeyboardInterrupt:
            interrupted = True
        except Exception as exc:
            raise CliRuntimeError(f"runtime failed: {exc}") from exc
        finally:
            self._cleanup_launch_if_needed(
                request=request,
                launch_decision=launch_decision,
                warnings=warnings,
            )

        return SceneRunResult(
            mode=request.mode,
            host=request.host,
            port=request.port,
            interrupted=interrupted,
            launch_report=launch_decision.launch_report,
            warnings=tuple(warnings),
        )

    def run_operator(self, request: OperatorRunRequest) -> OperatorRunResult:
        warnings = self._collect_runtime_warnings(request)
        launch_decision = self._prepare_launch_if_needed(request)
        interrupted = False
        execution = None
        try:
            execution = self.workflows.run_operator_workflow(request)
        except KeyboardInterrupt:
            interrupted = True
        except Exception as exc:
            raise CliRuntimeError(f"operator workflow failed: {exc}") from exc
        finally:
            self._cleanup_launch_if_needed(
                request=request,
                launch_decision=launch_decision,
                warnings=warnings,
            )

        return OperatorRunResult(
            host=request.host,
            port=request.port,
            execution=execution,
            interrupted=interrupted,
            launch_report=launch_decision.launch_report,
            warnings=tuple(warnings),
        )

    def run_exp(self, request: ExpRunRequest) -> ExpRunResult:
        warnings = self._collect_runtime_warnings(request)
        launch_decision = _LaunchDecision(launch_report=LaunchReport())
        try:
            # Validate scene JSON early so launch map override is deterministic.
            self.scene_template_loader.load_map_name(request.scene_json)
        except Exception as exc:
            raise CliRuntimeError(f"exp workflow argument validation failed: {exc}") from exc

        launch_decision = self._prepare_launch_if_needed(request)
        interrupted = False
        execution = None
        try:
            execution = self.workflows.run_exp_workflow(request)
        except KeyboardInterrupt:
            interrupted = True
        except Exception as exc:
            raise CliRuntimeError(f"exp workflow failed: {exc}") from exc
        finally:
            self._cleanup_launch_if_needed(
                request=request,
                launch_decision=launch_decision,
                warnings=warnings,
            )

        return ExpRunResult(
            host=request.host,
            port=request.port,
            execution=execution,
            interrupted=interrupted,
            launch_report=launch_decision.launch_report,
            warnings=tuple(warnings),
        )

    def list_vehicles(self, request: VehicleListRequest) -> list[VehicleDescriptor]:
        try:
            return self.workflows.list_vehicles(request)
        except Exception as exc:
            raise CliRuntimeError(f"vehicle list failed: {exc}") from exc

    def spawn_vehicle(self, request: VehicleSpawnRequest) -> VehicleDescriptor:
        try:
            return self.workflows.spawn_vehicle(request)
        except Exception as exc:
            raise CliRuntimeError(f"vehicle spawn failed: {exc}") from exc

    def run_spectator_follow(self, request: SpectatorFollowRequest) -> SpectatorFollowResult:
        try:
            if self._read_session_offscreen_mode(request):
                return SpectatorFollowResult(
                    mode=request.mode,
                    host=request.host,
                    port=request.port,
                    skipped_offscreen=True,
                )
        except Exception as exc:
            raise CliRuntimeError(f"failed to detect session screen mode: {exc}") from exc

        follow_vehicle_id = self._resolve_follow_vehicle_id(request)

        interrupted = False
        try:
            self.workflows.run_spectator_follow_workflow(
                request=request,
                follow_vehicle_id=follow_vehicle_id,
            )
        except KeyboardInterrupt:
            interrupted = True
        except Exception as exc:
            raise CliRuntimeError(f"spectator follow failed: {exc}") from exc

        return SpectatorFollowResult(
            mode=request.mode,
            host=request.host,
            port=request.port,
            interrupted=interrupted,
        )

    def _read_session_offscreen_mode(self, request: SpectatorFollowRequest) -> bool:
        offscreen_mode = self.runtime_registry.read_offscreen_mode(request.host, request.port)
        if offscreen_mode is None:
            return False
        return offscreen_mode

    def _resolve_follow_vehicle_id(self, request: SpectatorFollowRequest) -> int:
        if request.follow.scheme == "actor":
            return int(request.follow.value or "0")

        descriptor = self.workflows.resolve_vehicle_ref(request)
        if descriptor is None:
            raise CliUsageError(
                f"no vehicle matches follow ref '{self.workflows.format_vehicle_ref(request.follow)}'"
            )
        return descriptor.actor_id

    def _prepare_launch_if_needed(
        self,
        request: SceneRunRequest | OperatorRunRequest | ExpRunRequest,
    ) -> _LaunchDecision:
        if not request.launch_carla:
            return _LaunchDecision(launch_report=LaunchReport())
        return self._maybe_launch_carla(request)

    def _cleanup_launch_if_needed(
        self,
        *,
        request: SceneRunRequest | OperatorRunRequest | ExpRunRequest,
        launch_decision: _LaunchDecision,
        warnings: list[str],
    ) -> None:
        if launch_decision.launched_process is None:
            return
        if request.keep_carla_server:
            return

        try:
            self.server_control.terminate_server(launch_decision.launched_process)
            self.runtime_registry.clear_session(request.host, request.port)
        except Exception as exc:
            warnings.append(f"failed to terminate launched CARLA process: {exc}")

    def _collect_runtime_warnings(
        self,
        request: SceneRunRequest | OperatorRunRequest | ExpRunRequest,
    ) -> list[str]:
        warnings: list[str] = []
        if request.offscreen and not request.launch_carla:
            warnings.append(_WARN_OFFSCREEN)
        if request.no_rendering and not request.launch_carla:
            warnings.append(_WARN_NO_RENDERING)
        return warnings

    def _maybe_launch_carla(
        self,
        request: SceneRunRequest | OperatorRunRequest | ExpRunRequest,
    ) -> _LaunchDecision:
        if not self.server_control.is_loopback_host(request.host):
            raise CliUsageError(
                f"--launch-carla only supports local host, got host={request.host}"
            )

        if self.server_control.is_server_reachable(request.host, request.port):
            if not request.reuse_existing_carla:
                raise CliUsageError(
                    "CARLA already reachable on "
                    f"{request.host}:{request.port}. "
                    "Stop existing CARLA or add --reuse-existing-carla."
                )
            return _LaunchDecision(
                launch_report=LaunchReport(reused_existing_server=True),
            )

        if not request.carla_exe:
            raise CliUsageError(
                "--carla-exe is required when --launch-carla is set "
                "(or set CARLA_UE4_EXE)"
            )

        launched_process: Any | None = None
        try:
            launched_process = self.server_control.launch_server(
                LaunchCarlaServerRequest(
                    executable_path=request.carla_exe,
                    rpc_port=request.port,
                    offscreen=request.offscreen,
                    no_rendering=request.no_rendering,
                    no_sound=not request.with_sound,
                    quality_level=request.quality_level,
                )
            )
            self.server_control.wait_until_ready(
                host=request.host,
                port=request.port,
                timeout_seconds=request.carla_startup_timeout_seconds,
                process=launched_process,
            )
            owner_pid = self.server_control.process_pid(launched_process)
            self.runtime_registry.record_session(
                RuntimeSessionRecord(
                    host=request.host,
                    port=request.port,
                    offscreen_mode=bool(request.offscreen),
                ),
                owner_pid=owner_pid,
            )
            return _LaunchDecision(
                launch_report=LaunchReport(launched_server_pid=owner_pid),
                launched_process=launched_process,
            )
        except Exception as exc:
            if launched_process is not None:
                try:
                    self.server_control.terminate_server(launched_process)
                except Exception:
                    pass
            raise CliRuntimeError(f"failed to launch CARLA server: {exc}") from exc


