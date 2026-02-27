"""Application composition root."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from vln_carla2.adapters.cli.commands import (
    ExpRunCommand,
    OperatorRunCommand,
    SceneRunCommand,
    SpectatorFollowCommand,
    VehicleListCommand,
    VehicleSpawnCommand,
)
from vln_carla2.adapters.cli.ports import CliApplicationPort
from vln_carla2.app.settings import Settings
from vln_carla2.app.wiring.control import build_control_container
from vln_carla2.app.wiring.exp import ExpRunSettings, run_exp_workflow
from vln_carla2.app.wiring.operator import (
    OperatorContainer,
    OperatorWorkflowSettings,
    build_operator_container,
    run_operator_workflow,
)
from vln_carla2.app.wiring.scene import SceneEditorSettings, run_scene_editor
from vln_carla2.app.wiring.session import (
    CarlaSessionConfig,
    clear_runtime_session_config,
    managed_carla_session,
    read_runtime_offscreen_mode,
    record_runtime_session_config,
)
from vln_carla2.domain.model.scene_template import SceneTemplate
from vln_carla2.domain.model.simple_command import TargetSpeedCommand
from vln_carla2.infrastructure.carla.server_launcher import (
    is_carla_server_reachable,
    is_loopback_host,
    launch_carla_server,
    terminate_carla_server,
    wait_for_carla_server,
)
from vln_carla2.infrastructure.carla.spawner import spawn_vehicle
from vln_carla2.infrastructure.filesystem.scene_template_json_store import SceneTemplateJsonStore
from vln_carla2.usecases.control.run_control_loop import LoopResult

T = TypeVar("T")


def run(settings: Settings) -> LoopResult:
    """Create runtime, execute closed-loop control, and cleanup resources."""
    ego_vehicle: Any | None = None
    session_config = CarlaSessionConfig(
        host=settings.host,
        port=settings.port,
        timeout_seconds=settings.timeout_seconds,
        map_name=settings.map_name,
        synchronous_mode=True,
        fixed_delta_seconds=settings.fixed_delta_seconds,
        no_rendering_mode=settings.no_rendering_mode,
        offscreen_mode=settings.offscreen_mode,
    )

    with managed_carla_session(session_config) as session:
        ego_vehicle = spawn_vehicle(
            world=session.world,
            blueprint_filter=settings.vehicle_blueprint,
            spawn_x=settings.spawn.x,
            spawn_y=settings.spawn.y,
            spawn_z=settings.spawn.z,
            spawn_yaw=settings.spawn.yaw,
            role_name="ego",
        )
        try:
            container = build_control_container(session.world, ego_vehicle)
            target = TargetSpeedCommand(target_speed_mps=settings.target_speed_mps)
            return container.run_control_loop.run(
                vehicle_id=container.vehicle_id,
                target=target,
                max_steps=settings.steps,
            )
        finally:
            if ego_vehicle is not None:
                try:
                    ego_vehicle.destroy()
                except Exception as exc:  # pragma: no cover - best effort cleanup
                    print(f"[WARN] failed to destroy ego vehicle: {exc}")


def build_cli_application() -> CliApplicationPort:
    """Build concrete CLI application port implementation."""
    return _CliApplication()


@dataclass(slots=True)
class _CliApplication:
    """CLI app service implementation."""

    def load_env_from_dotenv(self, path: str = ".env") -> None:
        if not os.path.exists(path):
            return

        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue

                    key, value = line.split("=", 1)
                    key = key.strip()
                    if not key or key in os.environ:
                        continue

                    value = value.strip()
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                        value = value[1:-1]
                    os.environ[key] = value
        except OSError:
            return

    def get_default_carla_exe(self) -> str | None:
        return os.getenv("CARLA_UE4_EXE")

    def run_scene(self, command: SceneRunCommand) -> int:
        launched_process: subprocess.Popen[bytes] | None = None
        session_config = self._build_session_config(
            host=command.host,
            port=command.port,
            timeout_seconds=command.timeout_seconds,
            map_name=command.map_name,
            mode=command.mode,
            fixed_delta_seconds=command.fixed_delta_seconds,
            no_rendering=command.no_rendering,
            offscreen=command.offscreen,
        )
        settings = SceneEditorSettings(
            host=command.host,
            port=command.port,
            timeout_seconds=command.timeout_seconds,
            map_name=command.map_name,
            synchronous_mode=command.mode == "sync",
            fixed_delta_seconds=command.fixed_delta_seconds,
            no_rendering_mode=command.no_rendering,
            offscreen_mode=command.offscreen,
            tick_sleep_seconds=command.tick_sleep_seconds,
            scene_import_path=command.scene_import,
            scene_export_path=command.scene_export_path,
            follow_vehicle_id=None,
            start_in_follow_mode=False,
            allow_mode_toggle=True,
            allow_spawn_vehicle_hotkey=True,
        )

        if settings.offscreen_mode and not command.launch_carla:
            print(
                "[WARN] --offscreen only affects launched CARLA server "
                "(enable --launch-carla)."
            )
        if settings.no_rendering_mode and not command.launch_carla:
            print(
                "[WARN] --no-rendering applies world settings, but window "
                "visibility depends on existing CARLA server startup flags."
            )

        if command.launch_carla:
            launch_result = self._maybe_launch_carla(
                command,
                session_config=session_config,
            )
            if isinstance(launch_result, int):
                if launch_result != 0:
                    return launch_result
            else:
                launched_process = launch_result

        try:
            run_scene_editor(settings)
        except KeyboardInterrupt:
            print("[INFO] interrupted by Ctrl+C")
        except Exception as exc:
            print(f"[ERROR] runtime failed: {exc}", file=sys.stderr)
            return 1
        finally:
            if launched_process is not None and not command.keep_carla_server:
                try:
                    terminate_carla_server(launched_process)
                    clear_runtime_session_config(command.host, command.port)
                except Exception as exc:
                    print(
                        f"[WARN] failed to terminate launched CARLA process: {exc}",
                        file=sys.stderr,
                    )

        print(
            f"[INFO] runtime stopped mode={command.mode} host={command.host} port={command.port}"
        )
        return 0

    def run_operator(self, command: OperatorRunCommand) -> int:
        launched_process: subprocess.Popen[bytes] | None = None
        session_config = self._build_session_config(
            host=command.host,
            port=command.port,
            timeout_seconds=command.timeout_seconds,
            map_name=command.map_name,
            mode=command.mode,
            fixed_delta_seconds=command.fixed_delta_seconds,
            no_rendering=command.no_rendering,
            offscreen=command.offscreen,
        )
        settings = OperatorWorkflowSettings(
            host=command.host,
            port=command.port,
            timeout_seconds=command.timeout_seconds,
            map_name=command.map_name,
            synchronous_mode=command.mode == "sync",
            fixed_delta_seconds=command.fixed_delta_seconds,
            no_rendering_mode=command.no_rendering,
            offscreen_mode=command.offscreen,
            tick_sleep_seconds=command.tick_sleep_seconds,
            spectator_initial_z=command.z,
            vehicle_ref=command.follow,
            spawn_request=command.spawn_request,
            spawn_if_missing=command.spawn_if_missing,
            strategy=command.strategy,
            steps=command.steps,
            target_speed_mps=command.target_speed_mps,
            operator_warmup_ticks=command.operator_warmup_ticks,
        )

        if settings.offscreen_mode and not command.launch_carla:
            print(
                "[WARN] --offscreen only affects launched CARLA server "
                "(enable --launch-carla)."
            )
        if settings.no_rendering_mode and not command.launch_carla:
            print(
                "[WARN] --no-rendering applies world settings, but window "
                "visibility depends on existing CARLA server startup flags."
            )

        if command.launch_carla:
            launch_result = self._maybe_launch_carla(
                command,
                session_config=session_config,
            )
            if isinstance(launch_result, int):
                if launch_result != 0:
                    return launch_result
            else:
                launched_process = launch_result

        try:
            result = run_operator_workflow(settings)
        except KeyboardInterrupt:
            print("[INFO] interrupted by Ctrl+C")
            return 0
        except Exception as exc:
            print(f"[ERROR] operator workflow failed: {exc}", file=sys.stderr)
            return 1
        finally:
            if launched_process is not None and not command.keep_carla_server:
                try:
                    terminate_carla_server(launched_process)
                    clear_runtime_session_config(command.host, command.port)
                except Exception as exc:
                    print(
                        f"[WARN] failed to terminate launched CARLA process: {exc}",
                        file=sys.stderr,
                    )

        print(
            "[INFO] operator workflow finished "
            f"strategy={result.strategy} vehicle_source={result.vehicle_source} "
            f"actor_id={result.selected_vehicle.actor_id} "
            f"operator_ticks={result.operator_ticks} "
            f"control_steps={result.control_loop_result.executed_steps} "
            f"host={command.host} port={command.port}"
        )
        return 0

    def run_exp(self, command: ExpRunCommand) -> int:
        launched_process: subprocess.Popen[bytes] | None = None
        try:
            scene_template = self._load_scene_template(command.scene_json)
        except Exception as exc:
            print(f"[ERROR] exp workflow argument validation failed: {exc}", file=sys.stderr)
            return 1

        session_config = self._build_session_config(
            host=command.host,
            port=command.port,
            timeout_seconds=command.timeout_seconds,
            map_name=command.map_name,
            mode=command.mode,
            fixed_delta_seconds=command.fixed_delta_seconds,
            no_rendering=command.no_rendering,
            offscreen=command.offscreen,
            map_name_override=scene_template.map_name,
        )
        settings = ExpRunSettings(
            scene_json_path=command.scene_json,
            host=command.host,
            port=command.port,
            timeout_seconds=command.timeout_seconds,
            synchronous_mode=command.mode == "sync",
            fixed_delta_seconds=command.fixed_delta_seconds,
            no_rendering_mode=command.no_rendering,
            offscreen_mode=command.offscreen,
            control_target=command.control_target,
            forward_distance_m=command.forward_distance_m,
            target_speed_mps=command.target_speed_mps,
            follow_z=20.0,
            max_steps=command.max_steps,
        )

        if settings.offscreen_mode and not command.launch_carla:
            print(
                "[WARN] --offscreen only affects launched CARLA server "
                "(enable --launch-carla)."
            )
        if settings.no_rendering_mode and not command.launch_carla:
            print(
                "[WARN] --no-rendering applies world settings, but window "
                "visibility depends on existing CARLA server startup flags."
            )

        if command.launch_carla:
            launch_result = self._maybe_launch_carla(
                command,
                session_config=session_config,
            )
            if isinstance(launch_result, int):
                if launch_result != 0:
                    return launch_result
            else:
                launched_process = launch_result

        try:
            result = run_exp_workflow(settings)
        except KeyboardInterrupt:
            print("[INFO] interrupted by Ctrl+C")
            return 0
        except Exception as exc:
            print(f"[ERROR] exp workflow failed: {exc}", file=sys.stderr)
            return 1
        finally:
            if launched_process is not None and not command.keep_carla_server:
                try:
                    terminate_carla_server(launched_process)
                    clear_runtime_session_config(command.host, command.port)
                except Exception as exc:
                    print(
                        f"[WARN] failed to terminate launched CARLA process: {exc}",
                        file=sys.stderr,
                    )

        print(
            "[INFO] exp workflow finished "
            f"control_target={_format_vehicle_ref(result.control_target)} "
            f"actor_id={result.selected_vehicle.actor_id} "
            f"map_name={result.scene_map_name} "
            f"imported_objects={result.imported_objects} "
            f"forward_distance_m={result.forward_distance_m:.3f} "
            f"traveled_distance_m={result.exp_workflow_result.traveled_distance_m:.3f} "
            f"entered_forbidden_zone={result.exp_workflow_result.entered_forbidden_zone} "
            f"control_steps={result.exp_workflow_result.control_loop_result.executed_steps} "
            f"host={command.host} port={command.port}"
        )
        entered = result.exp_workflow_result.entered_forbidden_zone
        status = "ENTERED" if entered else "CLEAR"
        print(f"[RESULT] forbidden_zone={status} entered_forbidden_zone={entered}")
        return 0

    def list_vehicles(self, command: VehicleListCommand):
        return self._with_operator_container(
            command,
            operation=lambda container, _world: container.list_vehicles.run(),
        )

    def spawn_vehicle(self, command: VehicleSpawnCommand):
        return self._with_operator_container(
            command,
            operation=lambda container, _world: container.spawn_vehicle.run(command.spawn_request),
        )

    def run_spectator_follow(self, command: SpectatorFollowCommand) -> int:
        try:
            if self._read_session_offscreen_mode(command):
                print("[WARN] spectator follow skipped in offscreen mode.")
                return 0
        except Exception as exc:
            print(f"[ERROR] failed to detect session screen mode: {exc}", file=sys.stderr)
            return 1

        try:
            follow_vehicle_id = self._resolve_follow_vehicle_id(command)
        except CliUsageError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 2
        except Exception as exc:
            print(f"[ERROR] failed to resolve follow ref: {exc}", file=sys.stderr)
            return 1

        if follow_vehicle_id is None:
            print("[ERROR] --follow is required", file=sys.stderr)
            return 2

        session_config = self._build_session_config(
            host=command.host,
            port=command.port,
            timeout_seconds=command.timeout_seconds,
            map_name=command.map_name,
            mode=command.mode,
            fixed_delta_seconds=command.fixed_delta_seconds,
            no_rendering=command.no_rendering,
            offscreen=False,
        )
        settings = SceneEditorSettings(
            host=session_config.host,
            port=session_config.port,
            timeout_seconds=session_config.timeout_seconds,
            map_name=session_config.map_name,
            synchronous_mode=session_config.synchronous_mode,
            fixed_delta_seconds=session_config.fixed_delta_seconds,
            no_rendering_mode=session_config.no_rendering_mode,
            offscreen_mode=session_config.offscreen_mode,
            follow_vehicle_id=follow_vehicle_id,
            spectator_initial_z=command.z,
            start_in_follow_mode=True,
            allow_mode_toggle=False,
            allow_spawn_vehicle_hotkey=False,
        )

        try:
            run_scene_editor(settings)
        except KeyboardInterrupt:
            print("[INFO] interrupted by Ctrl+C")
        except Exception as exc:
            print(f"[ERROR] spectator follow failed: {exc}", file=sys.stderr)
            return 1

        print(
            f"[INFO] spectator follow stopped mode={command.mode} "
            f"host={command.host} port={command.port}"
        )
        return 0

    def _read_session_offscreen_mode(self, command: SpectatorFollowCommand) -> bool:
        offscreen_mode = read_runtime_offscreen_mode(command.host, command.port)
        if offscreen_mode is None:
            return False
        return offscreen_mode

    def _resolve_follow_vehicle_id(self, command: SpectatorFollowCommand) -> int | None:
        if command.follow.scheme == "actor":
            return int(command.follow.value or "0")

        descriptor = self._with_operator_container(
            command,
            operation=lambda container, _world: container.resolve_vehicle_ref.run(command.follow),
            sleep_seconds=0.0,
        )
        if descriptor is None:
            raise CliUsageError(
                f"no vehicle matches follow ref '{_format_vehicle_ref(command.follow)}'"
            )
        return descriptor.actor_id

    def _with_operator_container(
        self,
        command: VehicleListCommand | VehicleSpawnCommand | SpectatorFollowCommand,
        *,
        operation: Callable[[OperatorContainer, Any], T],
        sleep_seconds: float = 0.0,
    ) -> T:
        session_config = self._build_session_config(
            host=command.host,
            port=command.port,
            timeout_seconds=command.timeout_seconds,
            map_name=command.map_name,
            mode=command.mode,
            fixed_delta_seconds=command.fixed_delta_seconds,
            no_rendering=command.no_rendering,
            offscreen=False,
        )
        with managed_carla_session(session_config) as session:
            container = build_operator_container(
                world=session.world,
                synchronous_mode=session_config.synchronous_mode,
                sleep_seconds=sleep_seconds,
            )
            return operation(container, session.world)

    def _build_session_config(
        self,
        *,
        host: str,
        port: int,
        timeout_seconds: float,
        map_name: str,
        mode: str,
        fixed_delta_seconds: float,
        no_rendering: bool,
        offscreen: bool,
        map_name_override: str | None = None,
    ) -> CarlaSessionConfig:
        map_name_value = map_name if map_name_override is None else map_name_override
        return CarlaSessionConfig(
            host=host,
            port=port,
            timeout_seconds=timeout_seconds,
            map_name=map_name_value,
            synchronous_mode=mode == "sync",
            fixed_delta_seconds=fixed_delta_seconds,
            no_rendering_mode=no_rendering,
            offscreen_mode=offscreen,
        )

    def _maybe_launch_carla(
        self,
        command: SceneRunCommand | OperatorRunCommand | ExpRunCommand,
        *,
        session_config: CarlaSessionConfig,
    ) -> subprocess.Popen[bytes] | int:
        if not is_loopback_host(session_config.host):
            print(
                "[ERROR] --launch-carla only supports local host, "
                f"got host={session_config.host}",
                file=sys.stderr,
            )
            return 2
        if is_carla_server_reachable(session_config.host, session_config.port):
            if not command.reuse_existing_carla:
                print(
                    "[ERROR] CARLA already reachable on "
                    f"{session_config.host}:{session_config.port}. "
                    "Stop existing CARLA or add --reuse-existing-carla.",
                    file=sys.stderr,
                )
                return 2
            print(
                f"[INFO] reusing existing CARLA on "
                f"{session_config.host}:{session_config.port}"
            )
            return 0

        if not command.carla_exe:
            print(
                "[ERROR] --carla-exe is required when --launch-carla is set "
                "(or set CARLA_UE4_EXE)",
                file=sys.stderr,
            )
            return 2

        launched_process: subprocess.Popen[bytes] | None = None
        try:
            launched_process = launch_carla_server(
                executable_path=command.carla_exe,
                rpc_port=session_config.port,
                offscreen=session_config.offscreen_mode,
                no_rendering=session_config.no_rendering_mode,
                no_sound=not command.with_sound,
                quality_level=command.quality_level,
            )
            print(
                f"[INFO] launched CARLA pid={launched_process.pid} "
                f"on {session_config.host}:{session_config.port}"
            )
            wait_for_carla_server(
                host=session_config.host,
                port=session_config.port,
                timeout_seconds=command.carla_startup_timeout_seconds,
                process=launched_process,
            )
            record_runtime_session_config(
                session_config,
                owner_pid=launched_process.pid,
            )
            return launched_process
        except Exception as exc:
            if launched_process is not None:
                try:
                    terminate_carla_server(launched_process)
                except Exception:
                    pass
            print(f"[ERROR] failed to launch CARLA server: {exc}", file=sys.stderr)
            return 1

    def _load_scene_template(self, path: str) -> SceneTemplate:
        return SceneTemplateJsonStore().load(path)


class CliUsageError(ValueError):
    """Raised when CLI arguments are semantically invalid."""


def _format_vehicle_ref(ref: Any) -> str:
    if ref.scheme == "first":
        return "first"
    return f"{ref.scheme}:{ref.value}"
