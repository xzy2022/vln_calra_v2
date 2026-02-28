from dataclasses import dataclass

from vln_carla2.usecases.scene.input_snapshot import EditorInputSnapshot
from vln_carla2.usecases.scene.models import EditorMode, EditorState
from vln_carla2.usecases.scene.run_scene_editor_loop import RunSceneEditorLoop
from vln_carla2.usecases.shared.input_snapshot import InputSnapshot


@dataclass
class _Snapshot:
    frame: int


class _FakeWorld:
    def __init__(self) -> None:
        self.tick_calls = 0
        self.wait_for_tick_calls = 0

    def tick(self) -> int:
        self.tick_calls += 1
        return self.tick_calls

    def wait_for_tick(self) -> _Snapshot:
        self.wait_for_tick_calls += 1
        return _Snapshot(frame=100 + self.wait_for_tick_calls)


class _FakeKeyboard:
    def __init__(self, snapshots: list[EditorInputSnapshot]) -> None:
        self._snapshots = list(snapshots)
        self._index = 0

    def read_snapshot(self) -> EditorInputSnapshot:
        snapshot = self._snapshots[self._index]
        self._index += 1
        return snapshot


class _FakeMoveSpectator:
    def __init__(self) -> None:
        self.calls: list[InputSnapshot] = []

    def move(self, snapshot: InputSnapshot) -> None:
        self.calls.append(snapshot)


class _FakeFollower:
    def __init__(self, results: list[bool]) -> None:
        self.z = 0.0
        self._results = list(results)
        self.calls = 0
        self.z_per_call: list[float] = []

    def follow_once(self) -> bool:
        self.calls += 1
        self.z_per_call.append(self.z)
        if self._results:
            return self._results.pop(0)
        return True


class _FakeSpawnAction:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.calls = 0
        self.error = error

    def run(self) -> None:
        self.calls += 1
        if self.error is not None:
            raise self.error


class _FakeExportAction:
    def __init__(self, *, path: str = "scene.json", error: Exception | None = None) -> None:
        self.calls = 0
        self.path = path
        self.error = error

    def run(self) -> str:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.path


def _make_loop(
    *,
    state: EditorState,
    snapshots: list[EditorInputSnapshot],
    follower: _FakeFollower | None = None,
    move_spectator: _FakeMoveSpectator | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    infos: list[str] | None = None,
    spawn_vehicle: _FakeSpawnAction | None = None,
    spawn_barrel: _FakeSpawnAction | None = None,
    export_scene: _FakeExportAction | None = None,
    allow_spawn_vehicle_hotkey: bool = True,
) -> RunSceneEditorLoop:
    world = _FakeWorld()
    keyboard = _FakeKeyboard(snapshots)
    return RunSceneEditorLoop(
        world=world,
        synchronous_mode=True,
        sleep_seconds=0.0,
        state=state,
        min_follow_z=-20.0,
        max_follow_z=120.0,
        allow_mode_toggle=True,
        allow_spawn_vehicle_hotkey=allow_spawn_vehicle_hotkey,
        keyboard_input=keyboard,
        move_spectator=move_spectator,
        follow_vehicle_topdown=follower,
        spawn_vehicle_at_spectator_xy=spawn_vehicle,
        spawn_barrel_at_spectator_xy=spawn_barrel,
        export_scene=export_scene,
        info_fn=(infos.append if infos is not None else print),
        warn_fn=(warnings.append if warnings is not None else print),
        error_fn=(errors.append if errors is not None else print),
    )


def test_free_mode_applies_held_move_delta() -> None:
    move = _FakeMoveSpectator()
    loop = _make_loop(
        state=EditorState(mode=EditorMode.FREE, follow_vehicle_id=None, follow_z=20.0),
        snapshots=[EditorInputSnapshot(held_dx=1.0, held_dy=-2.0, held_dz=0.5)],
        move_spectator=move,
    )

    loop.step(with_tick=False, with_sleep=False)

    assert move.calls == [InputSnapshot(dx=1.0, dy=-2.0, dz=0.5)]


def test_toggle_free_to_follow_success_moves_immediately_and_skips_free_move() -> None:
    warnings: list[str] = []
    move = _FakeMoveSpectator()
    follower = _FakeFollower(results=[True])
    loop = _make_loop(
        state=EditorState(mode=EditorMode.FREE, follow_vehicle_id=7, follow_z=25.0),
        snapshots=[
            EditorInputSnapshot(
                held_dx=10.0,
                held_dy=10.0,
                held_dz=1.0,
                pressed_toggle_mode=True,
            )
        ],
        follower=follower,
        move_spectator=move,
        warnings=warnings,
    )

    loop.step(with_tick=False, with_sleep=False)

    assert loop.state.mode is EditorMode.FOLLOW
    assert follower.calls == 1
    assert follower.z_per_call == [25.0]
    assert move.calls == []
    assert warnings == []


def test_toggle_free_to_follow_warns_and_stays_free_when_target_not_configured() -> None:
    warnings: list[str] = []
    move = _FakeMoveSpectator()
    loop = _make_loop(
        state=EditorState(mode=EditorMode.FREE, follow_vehicle_id=None, follow_z=20.0),
        snapshots=[EditorInputSnapshot(held_dx=1.0, pressed_toggle_mode=True)],
        move_spectator=move,
        warnings=warnings,
    )

    loop.step(with_tick=False, with_sleep=False)

    assert loop.state.mode is EditorMode.FREE
    assert move.calls == []
    assert len(warnings) == 1
    assert warnings[0].startswith("[WARN]")


def test_toggle_free_to_follow_warns_when_vehicle_missing() -> None:
    warnings: list[str] = []
    move = _FakeMoveSpectator()
    follower = _FakeFollower(results=[False])
    loop = _make_loop(
        state=EditorState(mode=EditorMode.FREE, follow_vehicle_id=42, follow_z=20.0),
        snapshots=[EditorInputSnapshot(held_dx=1.0, held_dz=1.0, pressed_toggle_mode=True)],
        follower=follower,
        move_spectator=move,
        warnings=warnings,
    )

    loop.step(with_tick=False, with_sleep=False)

    assert loop.state.mode is EditorMode.FREE
    assert follower.calls == 1
    assert move.calls == []
    assert len(warnings) == 1
    assert "actor not found" in warnings[0]


def test_toggle_follow_to_free_stops_follow_for_current_tick() -> None:
    follower = _FakeFollower(results=[True])
    loop = _make_loop(
        state=EditorState(mode=EditorMode.FOLLOW, follow_vehicle_id=7, follow_z=20.0),
        snapshots=[EditorInputSnapshot(held_dz=1.0, pressed_toggle_mode=True)],
        follower=follower,
        move_spectator=_FakeMoveSpectator(),
    )

    loop.step(with_tick=False, with_sleep=False)

    assert loop.state.mode is EditorMode.FREE
    assert follower.calls == 0


def test_follow_mode_applies_dz_to_follow_z_with_clamp() -> None:
    follower = _FakeFollower(results=[True])
    loop = _make_loop(
        state=EditorState(mode=EditorMode.FOLLOW, follow_vehicle_id=7, follow_z=119.0),
        snapshots=[EditorInputSnapshot(held_dz=5.0)],
        follower=follower,
        move_spectator=_FakeMoveSpectator(),
    )

    loop.step(with_tick=False, with_sleep=False)

    assert loop.state.mode is EditorMode.FOLLOW
    assert loop.state.follow_z == 120.0
    assert follower.calls == 1
    assert follower.z_per_call == [120.0]


def test_follow_mode_stays_follow_when_vehicle_temporarily_missing() -> None:
    follower = _FakeFollower(results=[False])
    loop = _make_loop(
        state=EditorState(mode=EditorMode.FOLLOW, follow_vehicle_id=7, follow_z=20.0),
        snapshots=[EditorInputSnapshot(held_dz=0.0)],
        follower=follower,
    )

    loop.step(with_tick=False, with_sleep=False)

    assert loop.state.mode is EditorMode.FOLLOW
    assert follower.calls == 1


def test_spawn_hotkey_triggers_exactly_once_per_pressed_snapshot() -> None:
    spawn = _FakeSpawnAction()
    loop = _make_loop(
        state=EditorState(mode=EditorMode.FREE, follow_vehicle_id=None, follow_z=20.0),
        snapshots=[
            EditorInputSnapshot(pressed_spawn_vehicle=True),
            EditorInputSnapshot(pressed_spawn_vehicle=False),
            EditorInputSnapshot(pressed_spawn_vehicle=True),
        ],
        move_spectator=_FakeMoveSpectator(),
        spawn_vehicle=spawn,
    )

    loop.step(with_tick=False, with_sleep=False)
    loop.step(with_tick=False, with_sleep=False)
    loop.step(with_tick=False, with_sleep=False)

    assert spawn.calls == 2


def test_spawn_hotkey_errors_are_reported_without_retry() -> None:
    errors: list[str] = []
    spawn = _FakeSpawnAction(error=RuntimeError("blocked by collision"))
    loop = _make_loop(
        state=EditorState(mode=EditorMode.FREE, follow_vehicle_id=None, follow_z=20.0),
        snapshots=[EditorInputSnapshot(pressed_spawn_vehicle=True)],
        move_spectator=_FakeMoveSpectator(),
        spawn_vehicle=spawn,
        errors=errors,
    )

    loop.step(with_tick=False, with_sleep=False)

    assert spawn.calls == 1
    assert len(errors) == 1
    assert errors[0].startswith("[ERROR] spawn vehicle failed:")


def test_spawn_hotkey_can_be_disabled() -> None:
    spawn = _FakeSpawnAction()
    loop = _make_loop(
        state=EditorState(mode=EditorMode.FREE, follow_vehicle_id=None, follow_z=20.0),
        snapshots=[EditorInputSnapshot(pressed_spawn_vehicle=True)],
        move_spectator=_FakeMoveSpectator(),
        spawn_vehicle=spawn,
        allow_spawn_vehicle_hotkey=False,
    )

    loop.step(with_tick=False, with_sleep=False)

    assert spawn.calls == 0


def test_spawn_barrel_hotkey_triggers_once_per_pressed_snapshot() -> None:
    spawn_barrel = _FakeSpawnAction()
    loop = _make_loop(
        state=EditorState(mode=EditorMode.FREE, follow_vehicle_id=None, follow_z=20.0),
        snapshots=[
            EditorInputSnapshot(pressed_spawn_barrel=True),
            EditorInputSnapshot(pressed_spawn_barrel=False),
            EditorInputSnapshot(pressed_spawn_barrel=True),
        ],
        move_spectator=_FakeMoveSpectator(),
        spawn_barrel=spawn_barrel,
    )

    loop.step(with_tick=False, with_sleep=False)
    loop.step(with_tick=False, with_sleep=False)
    loop.step(with_tick=False, with_sleep=False)

    assert spawn_barrel.calls == 2


def test_spawn_hotkeys_error_messages_are_distinct() -> None:
    errors: list[str] = []
    loop = _make_loop(
        state=EditorState(mode=EditorMode.FREE, follow_vehicle_id=None, follow_z=20.0),
        snapshots=[
            EditorInputSnapshot(
                pressed_spawn_vehicle=True,
                pressed_spawn_barrel=True,
            )
        ],
        move_spectator=_FakeMoveSpectator(),
        spawn_vehicle=_FakeSpawnAction(error=RuntimeError("vehicle-collision")),
        spawn_barrel=_FakeSpawnAction(error=RuntimeError("barrel-collision")),
        errors=errors,
    )

    loop.step(with_tick=False, with_sleep=False)

    assert len(errors) == 2
    assert errors[0].startswith("[ERROR] spawn vehicle failed:")
    assert errors[1].startswith("[ERROR] spawn barrel failed:")


def test_export_hotkey_triggers_once_per_pressed_snapshot() -> None:
    export = _FakeExportAction(path="scene_a.json")
    infos: list[str] = []
    loop = _make_loop(
        state=EditorState(mode=EditorMode.FREE, follow_vehicle_id=None, follow_z=20.0),
        snapshots=[
            EditorInputSnapshot(pressed_export_scene=True),
            EditorInputSnapshot(pressed_export_scene=False),
            EditorInputSnapshot(pressed_export_scene=True),
        ],
        move_spectator=_FakeMoveSpectator(),
        export_scene=export,
        infos=infos,
    )

    loop.step(with_tick=False, with_sleep=False)
    loop.step(with_tick=False, with_sleep=False)
    loop.step(with_tick=False, with_sleep=False)

    assert export.calls == 2
    assert len(infos) == 2
    assert infos[0] == "[INFO] scene exported: scene_a.json"


def test_export_hotkey_errors_are_reported() -> None:
    export = _FakeExportAction(error=RuntimeError("permission denied"))
    errors: list[str] = []
    loop = _make_loop(
        state=EditorState(mode=EditorMode.FREE, follow_vehicle_id=None, follow_z=20.0),
        snapshots=[EditorInputSnapshot(pressed_export_scene=True)],
        move_spectator=_FakeMoveSpectator(),
        export_scene=export,
        errors=errors,
    )

    loop.step(with_tick=False, with_sleep=False)

    assert export.calls == 1
    assert len(errors) == 1
    assert errors[0].startswith("[ERROR] scene export failed:")


