"""Utilities for launching and managing a local CARLA server process."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Sequence

_QUALITY_LEVELS = {"Low", "Epic"}


def is_loopback_host(host: str) -> bool:
    """Return True when host points to the local machine."""
    return host.strip().lower() in {"127.0.0.1", "localhost", "::1"}


def build_carla_server_command(
    executable_path: str,
    rpc_port: int,
    *,
    offscreen: bool = False,
    no_rendering: bool = False,
    no_sound: bool = True,
    quality_level: str = "Epic",
    extra_args: Sequence[str] | None = None,
) -> list[str]:
    """Build a CarlaUE4 launch command with optional rendering flags."""
    if rpc_port <= 0:
        raise ValueError("rpc_port must be positive")
    if not executable_path:
        raise ValueError("executable_path must not be empty")

    executable = _resolve_server_executable(Path(executable_path).expanduser())
    if not executable.exists():
        raise FileNotFoundError(f"CARLA executable not found: {executable}")

    command = [str(executable), f"--carla-rpc-port={rpc_port}"]
    if offscreen:
        command.append("-RenderOffScreen")
    if no_rendering:
        command.append("--no-rendering")
    if no_sound:
        command.append("-nosound")
    normalized_quality = quality_level.strip().title()
    if normalized_quality not in _QUALITY_LEVELS:
        allowed = ", ".join(sorted(_QUALITY_LEVELS))
        raise ValueError(f"quality_level must be one of: {allowed}")
    command.append(f"-quality-level={normalized_quality}")
    if extra_args:
        command.extend(extra_args)
    return command


def _resolve_server_executable(executable: Path) -> Path:
    """Resolve a stable CARLA server binary when launcher path is provided."""
    if os.name != "nt":
        return executable

    if executable.name.lower() != "carlaue4.exe":
        return executable

    shipping_exe = (
        executable.parent
        / "CarlaUE4"
        / "Binaries"
        / "Win64"
        / "CarlaUE4-Win64-Shipping.exe"
    )
    if shipping_exe.exists():
        return shipping_exe
    return executable


def launch_carla_server(
    executable_path: str,
    rpc_port: int,
    *,
    offscreen: bool = False,
    no_rendering: bool = False,
    no_sound: bool = True,
    quality_level: str = "Epic",
    extra_args: Sequence[str] | None = None,
) -> subprocess.Popen[bytes]:
    """Start CarlaUE4 and return the process handle."""
    command = build_carla_server_command(
        executable_path=executable_path,
        rpc_port=rpc_port,
        offscreen=offscreen,
        no_rendering=no_rendering,
        no_sound=no_sound,
        quality_level=quality_level,
        extra_args=extra_args,
    )

    creationflags = 0
    if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    return subprocess.Popen(command, creationflags=creationflags)


def is_carla_server_reachable(
    host: str,
    port: int,
    timeout_seconds: float = 0.5,
) -> bool:
    """Check whether CARLA RPC endpoint is reachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def wait_for_carla_server(
    host: str,
    port: int,
    timeout_seconds: float,
    *,
    process: subprocess.Popen[bytes] | None = None,
    poll_interval_seconds: float = 0.5,
) -> None:
    """Wait until CARLA RPC endpoint is reachable or timeout is hit."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if poll_interval_seconds <= 0:
        raise ValueError("poll_interval_seconds must be positive")

    deadline = time.monotonic() + timeout_seconds
    while True:
        if is_carla_server_reachable(host, port):
            return

        if process is not None:
            exit_code = process.poll()
            if exit_code is not None:
                raise RuntimeError(f"CARLA process exited early with code {exit_code}")

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"Timed out waiting for CARLA server at {host}:{port} "
                f"after {timeout_seconds:.1f}s"
            )
        time.sleep(min(poll_interval_seconds, remaining))


def terminate_carla_server(
    process: subprocess.Popen[bytes],
    *,
    timeout_seconds: float = 8.0,
) -> None:
    """Terminate a launched CarlaUE4 process gracefully."""
    if process.poll() is not None:
        return

    if os.name == "nt":
        result = subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return

    process.terminate()
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2.0)
