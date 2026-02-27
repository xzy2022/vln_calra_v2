"""Shared CARLA session lifecycle for composition roots."""

from __future__ import annotations

import json
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, cast

from vln_carla2.infrastructure.carla.client_factory import restore_world_settings
from vln_carla2.infrastructure.carla.types import require_carla

_RUNTIME_SESSION_REGISTRY = Path(tempfile.gettempdir()) / "vln_carla2_carla_runtime_session.json"


@dataclass(slots=True)
class CarlaSessionConfig:
    """Configuration for one CARLA world session."""

    host: str
    port: int
    timeout_seconds: float
    map_name: str
    synchronous_mode: bool
    fixed_delta_seconds: float
    no_rendering_mode: bool = False
    offscreen_mode: bool = False
    force_reload_map: bool = False


@dataclass(slots=True)
class CarlaSession:
    """Opened CARLA session with world and original settings handle."""

    client: Any
    world: Any
    original_settings: Any
    offscreen_mode: bool = False

    def restore(self) -> None:
        """Restore world settings captured when the session was opened."""
        restore_world_settings(self.world, self.original_settings)


def is_offscreen_session(session: CarlaSession) -> bool:
    """Return True when opened CARLA session runs in offscreen mode."""
    return session.offscreen_mode


def open_carla_session(config: CarlaSessionConfig) -> CarlaSession:
    """Connect, ensure map, apply runtime settings, and return session handle."""
    carla = require_carla()

    client = carla.Client(config.host, config.port)
    client.set_timeout(config.timeout_seconds)
    world = client.get_world()

    current_map = world.get_map().name.split("/")[-1]
    if config.force_reload_map or current_map != config.map_name:
        world = client.load_world(config.map_name)

    original_settings = world.get_settings()
    runtime_settings = world.get_settings()
    runtime_settings.synchronous_mode = config.synchronous_mode
    runtime_settings.no_rendering_mode = config.no_rendering_mode
    runtime_settings.fixed_delta_seconds = (
        config.fixed_delta_seconds if config.synchronous_mode else None
    )
    world.apply_settings(runtime_settings)
    if config.synchronous_mode:
        world.tick()

    return CarlaSession(
        client=client,
        world=world,
        original_settings=original_settings,
        offscreen_mode=_detect_world_offscreen_mode(
            world=world,
            configured_offscreen_mode=config.offscreen_mode,
        ),
    )


def _detect_world_offscreen_mode(*, world: Any, configured_offscreen_mode: bool) -> bool:
    """
    Detect offscreen mode from CARLA world settings when possible.

    CARLA Python API does not consistently expose a dedicated offscreen field
    across versions, so this falls back to configured value when unavailable.
    """
    try:
        settings = world.get_settings()
    except Exception:
        return configured_offscreen_mode

    for attr_name in (
        "offscreen_mode",
        "off_screen_mode",
        "render_offscreen",
        "render_off_screen",
    ):
        value = getattr(settings, attr_name, None)
        if isinstance(value, bool):
            return value
    return configured_offscreen_mode


@contextmanager
def managed_carla_session(config: CarlaSessionConfig) -> Iterator[CarlaSession]:
    """Context manager that always restores world settings on exit."""
    session = open_carla_session(config)
    try:
        yield session
    finally:
        session.restore()


def record_runtime_session_config(
    config: CarlaSessionConfig,
    *,
    owner_pid: int | None = None,
) -> None:
    """Persist runtime session config for cross-process lookup by host:port."""
    registry = _load_runtime_registry()
    key = _runtime_registry_key(config.host, config.port)
    registry[key] = {
        "host": config.host,
        "port": config.port,
        "offscreen_mode": bool(config.offscreen_mode),
        "owner_pid": owner_pid,
        "updated_at": time.time(),
    }
    _save_runtime_registry(registry)


def read_runtime_offscreen_mode(host: str, port: int) -> bool | None:
    """Read persisted offscreen mode for a CARLA runtime if available."""
    registry = _load_runtime_registry()
    key = _runtime_registry_key(host, port)
    payload = registry.get(key)
    if not isinstance(payload, dict):
        return None
    payload_dict = cast(dict[str, Any], payload)
    offscreen_mode = payload_dict.get("offscreen_mode")
    if not isinstance(offscreen_mode, bool):
        return None
    return offscreen_mode


def clear_runtime_session_config(host: str, port: int) -> None:
    """Remove persisted runtime session config by host:port."""
    registry = _load_runtime_registry()
    key = _runtime_registry_key(host, port)
    if key in registry:
        del registry[key]
        _save_runtime_registry(registry)


def _runtime_registry_key(host: str, port: int) -> str:
    return f"{host}:{port}"


def _load_runtime_registry() -> dict[str, Any]:
    if not _RUNTIME_SESSION_REGISTRY.exists():
        return {}
    try:
        content = _RUNTIME_SESSION_REGISTRY.read_text(encoding="utf-8")
        payload = json.loads(content)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    # json.loads returns a dynamically typed object; normalize to the declared mapping type.
    return cast(dict[str, Any], payload)


def _save_runtime_registry(registry: dict[str, Any]) -> None:
    try:
        _RUNTIME_SESSION_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
        temp_path = _RUNTIME_SESSION_REGISTRY.with_suffix(".tmp")
        temp_path.write_text(json.dumps(registry, ensure_ascii=True), encoding="utf-8")
        temp_path.replace(_RUNTIME_SESSION_REGISTRY)
    except OSError:
        return

