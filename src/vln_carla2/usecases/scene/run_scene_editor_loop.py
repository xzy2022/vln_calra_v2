"""Use case for scene editor runtime orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from vln_carla2.domain.services.spectator_rules import clamp_z
from vln_carla2.usecases.scene.input_snapshot import EditorInputSnapshot
from vln_carla2.usecases.scene.models import EditorMode, EditorState
from vln_carla2.usecases.shared.input_snapshot import InputSnapshot


class SceneEditorKeyboardInputProtocol(Protocol):
    """Read one scene editor input snapshot per loop iteration."""

    def read_snapshot(self) -> EditorInputSnapshot:
        ...


class SceneEditorMoveSpectatorProtocol(Protocol):
    """Move spectator based on free-mode held input."""

    def move(self, snapshot: InputSnapshot) -> None:
        ...


class SceneEditorFollowVehicleProtocol(Protocol):
    """Follow target vehicle with mutable follow height."""

    z: float

    def follow_once(self) -> bool:
        ...


class SceneEditorSpawnVehicleProtocol(Protocol):
    """Spawn one vehicle based on current scene-editor context."""

    def run(self) -> Any:
        ...


class SceneEditorExportSceneProtocol(Protocol):
    """Export current scene template and return saved path."""

    def run(self) -> str:
        ...


@dataclass(slots=True)
class RunSceneEditorLoop:
    """
    Scene editor loop orchestration.

    Per iteration:
    1) read editor input snapshot
    2) apply mode transition or mode-specific behavior
    3) tick / wait_for_tick
    """

    world: Any
    synchronous_mode: bool
    sleep_seconds: float
    state: EditorState
    min_follow_z: float
    max_follow_z: float
    allow_mode_toggle: bool = True
    allow_spawn_vehicle_hotkey: bool = True
    keyboard_input: SceneEditorKeyboardInputProtocol | None = None
    move_spectator: SceneEditorMoveSpectatorProtocol | None = None
    follow_vehicle_topdown: SceneEditorFollowVehicleProtocol | None = None
    spawn_vehicle_at_spectator_xy: SceneEditorSpawnVehicleProtocol | None = None
    spawn_barrel_at_spectator_xy: SceneEditorSpawnVehicleProtocol | None = None
    spawn_goal_at_spectator_xy: SceneEditorSpawnVehicleProtocol | None = None
    export_scene: SceneEditorExportSceneProtocol | None = None
    info_fn: Callable[[str], None] = print
    warn_fn: Callable[[str], None] = print
    error_fn: Callable[[str], None] = print
    _warned_missing_follow_runtime: bool = field(
        init=False,
        default=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if self.max_follow_z < self.min_follow_z:
            raise ValueError("max_follow_z must be >= min_follow_z")
        self.state.follow_z = self._clamp_follow_z(self.state.follow_z)

    def step(self, *, with_tick: bool = True, with_sleep: bool = True) -> int | None:
        """Execute one scene editor iteration and optionally tick/sleep."""
        input_snapshot = self._read_input_snapshot()
        self._handle_spawn_hotkeys(input_snapshot)
        self._handle_export_hotkey(input_snapshot)

        if self.allow_mode_toggle and input_snapshot.pressed_toggle_mode:
            self._handle_toggle_mode()
        elif self.state.mode is EditorMode.FREE:
            self._handle_free_mode(input_snapshot)
        else:
            self._handle_follow_mode(input_snapshot)

        if not with_tick:
            return None

        frame = self._tick_once()
        if self.synchronous_mode and with_sleep:
            time.sleep(self.sleep_seconds)
        return frame

    def run(self, *, max_ticks: int | None = None) -> int:
        """Run until interrupted or until max_ticks is reached."""
        executed_ticks = 0

        while True:
            if max_ticks is not None and executed_ticks >= max_ticks:
                break
            self.step(with_tick=True, with_sleep=True)
            executed_ticks += 1

        return executed_ticks

    def _read_input_snapshot(self) -> EditorInputSnapshot:
        if self.keyboard_input is None:
            return EditorInputSnapshot.zero()
        return self.keyboard_input.read_snapshot()

    def _handle_toggle_mode(self) -> None:
        if self.state.mode is EditorMode.FOLLOW:
            self.state.mode = EditorMode.FREE
            return

        if self.state.follow_vehicle_id is None or self.follow_vehicle_topdown is None:
            self._warn("follow target is not configured; stay in FREE mode.")
            return

        self.state.follow_z = self._clamp_follow_z(self.state.follow_z)
        self.follow_vehicle_topdown.z = self.state.follow_z
        if not self.follow_vehicle_topdown.follow_once():
            self._warn(
                f"follow target actor not found: id={self.state.follow_vehicle_id}; "
                "stay in FREE mode."
            )
            return

        self.state.mode = EditorMode.FOLLOW

    def _handle_free_mode(self, input_snapshot: EditorInputSnapshot) -> None:
        if self.move_spectator is None:
            return
        self.move_spectator.move(
            snapshot=InputSnapshot(
                dx=input_snapshot.held_dx,
                dy=input_snapshot.held_dy,
                dz=input_snapshot.held_dz,
            )
        )

    def _handle_follow_mode(self, input_snapshot: EditorInputSnapshot) -> None:
        if self.follow_vehicle_topdown is None:
            self._warn_once_missing_follow_runtime()
            return

        self.state.follow_z = self._clamp_follow_z(self.state.follow_z + input_snapshot.held_dz)
        self.follow_vehicle_topdown.z = self.state.follow_z
        followed = self.follow_vehicle_topdown.follow_once()
        if followed:
            self._warned_missing_follow_runtime = False

    def _handle_spawn_hotkeys(self, input_snapshot: EditorInputSnapshot) -> None:
        if not self.allow_spawn_vehicle_hotkey:
            return

        if input_snapshot.pressed_spawn_vehicle:
            if self.spawn_vehicle_at_spectator_xy is None:
                self._error("spawn vehicle hotkey is unavailable in current runtime.")
            else:
                try:
                    self.spawn_vehicle_at_spectator_xy.run()
                except Exception as exc:
                    self._error(f"spawn vehicle failed: {exc}")

        if input_snapshot.pressed_spawn_barrel:
            if self.spawn_barrel_at_spectator_xy is None:
                self._error("spawn barrel hotkey is unavailable in current runtime.")
            else:
                try:
                    self.spawn_barrel_at_spectator_xy.run()
                except Exception as exc:
                    self._error(f"spawn barrel failed: {exc}")

        if input_snapshot.pressed_spawn_goal:
            if self.spawn_goal_at_spectator_xy is None:
                self._error("spawn goal hotkey is unavailable in current runtime.")
            else:
                try:
                    self.spawn_goal_at_spectator_xy.run()
                except Exception as exc:
                    self._error(f"spawn goal failed: {exc}")

    def _handle_export_hotkey(self, input_snapshot: EditorInputSnapshot) -> None:
        if not input_snapshot.pressed_export_scene:
            return
        if self.export_scene is None:
            self._error("scene export hotkey is unavailable in current runtime.")
            return
        try:
            path = self.export_scene.run()
            self._info(f"scene exported: {path}")
        except Exception as exc:
            self._error(f"scene export failed: {exc}")

    def _warn_once_missing_follow_runtime(self) -> None:
        if self._warned_missing_follow_runtime:
            return
        self._warn("follow mode active but follow target is unavailable.")
        self._warned_missing_follow_runtime = True

    def _clamp_follow_z(self, value: float) -> float:
        return clamp_z(value, self.min_follow_z, self.max_follow_z)

    def _tick_once(self) -> int:
        if self.synchronous_mode:
            return int(self.world.tick())

        snapshot = self.world.wait_for_tick()
        return int(snapshot.frame)

    def _warn(self, message: str) -> None:
        self.warn_fn(f"[WARN] {message}")

    def _info(self, message: str) -> None:
        self.info_fn(f"[INFO] {message}")

    def _error(self, message: str) -> None:
        self.error_fn(f"[ERROR] {message}")


