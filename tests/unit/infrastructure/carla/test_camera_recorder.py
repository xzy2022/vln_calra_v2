from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

import numpy as np

from vln_carla2.infrastructure.carla import camera_recorder

_CASE_ROOT = Path(".tmp_test_artifacts") / "camera_recorder"


def _case_dir(name: str) -> Path:
    case_dir = _CASE_ROOT / name
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


class _FakeBlueprint:
    def __init__(self) -> None:
        self.attrs: dict[str, str] = {}

    def set_attribute(self, key: str, value: str) -> None:
        self.attrs[key] = value


class _FakeBlueprintLibrary:
    def __init__(self, blueprint: _FakeBlueprint) -> None:
        self._blueprint = blueprint

    def find(self, _blueprint_id: str) -> _FakeBlueprint:
        return self._blueprint


class _FakeSensor:
    def __init__(self) -> None:
        self._callback: Any | None = None
        self.stop_calls = 0
        self.destroy_calls = 0

    def listen(self, callback: Any) -> None:
        self._callback = callback

    def emit(self, image: Any) -> None:
        if self._callback is None:
            raise RuntimeError("callback not registered")
        self._callback(image)

    def stop(self) -> None:
        self.stop_calls += 1

    def destroy(self) -> None:
        self.destroy_calls += 1


class _FakeWorld:
    def __init__(self, sensor: _FakeSensor, blueprint: _FakeBlueprint) -> None:
        self._sensor = sensor
        self._blueprint = blueprint

    def get_blueprint_library(self) -> _FakeBlueprintLibrary:
        return _FakeBlueprintLibrary(self._blueprint)

    def spawn_actor(self, *args: Any, **kwargs: Any) -> _FakeSensor:
        del args, kwargs
        return self._sensor


class _FakeLocation:
    def __init__(self, *, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z


class _FakeRotation:
    def __init__(self, *, pitch: float, yaw: float, roll: float) -> None:
        self.pitch = pitch
        self.yaw = yaw
        self.roll = roll


class _FakeTransform:
    def __init__(self, location: _FakeLocation, rotation: _FakeRotation) -> None:
        self.location = location
        self.rotation = rotation


class _FakeAttachmentType:
    Rigid = "Rigid"


class _FakeVehicleActor:
    def __init__(self) -> None:
        self._transform = _FakeTransform(
            _FakeLocation(x=1.0, y=2.0, z=0.3),
            _FakeRotation(pitch=0.0, yaw=90.0, roll=0.0),
        )
        self._velocity = _FakeLocation(x=3.0, y=4.0, z=0.0)
        self._control = type("Control", (), {"throttle": 0.2, "brake": 0.0, "steer": 0.1})()

    def get_transform(self) -> _FakeTransform:
        return self._transform

    def get_velocity(self) -> _FakeLocation:
        return self._velocity

    def get_control(self) -> Any:
        return self._control


def test_camera_recorder_records_jpeg_and_index(monkeypatch) -> None:
    save_calls: list[dict[str, Any]] = []

    case_dir = _case_dir("records_jpeg_and_index")
    class _FakePillowImage:
        @staticmethod
        def fromarray(array: np.ndarray) -> Any:
            class _Writer:
                def save(self, path: Path, *, format: str, quality: int) -> None:
                    save_calls.append(
                        {
                            "shape": tuple(array.shape),
                            "path": str(path),
                            "format": format,
                            "quality": quality,
                        }
                    )
                    Path(path).write_bytes(b"jpeg")

            return _Writer()

    fake_carla = type(
        "FakeCarla",
        (),
        {
            "Location": _FakeLocation,
            "Rotation": _FakeRotation,
            "Transform": _FakeTransform,
            "AttachmentType": _FakeAttachmentType,
        },
    )
    monkeypatch.setattr(camera_recorder, "require_carla", lambda: fake_carla)
    monkeypatch.setattr(camera_recorder, "_load_pillow_image_class", lambda: _FakePillowImage)

    blueprint = _FakeBlueprint()
    sensor = _FakeSensor()
    world = _FakeWorld(sensor=sensor, blueprint=blueprint)
    vehicle_actor = _FakeVehicleActor()
    recorder = camera_recorder.CarlaFrontRgbCameraRecorder(
        world=world,
        vehicle_actor=vehicle_actor,
        actor_id=42,
        map_name="Town10HD_Opt",
        base_output_dir=case_dir / "camera",
        config=camera_recorder.FrontRgbCameraConfig(
            image_width=2,
            image_height=1,
            fov_deg=100.0,
            sensor_tick_seconds=0.05,
            jpeg_quality=90,
        ),
    )
    recorder.start()

    class _FakeImage:
        frame = 10
        timestamp = 1.5
        width = 2
        height = 1
        # BGRA pixels: red and green
        raw_data = bytes([0, 0, 255, 255, 0, 255, 0, 255])

    sensor.emit(_FakeImage())
    index_path = recorder.save_index()

    assert blueprint.attrs["image_size_x"] == "2"
    assert blueprint.attrs["image_size_y"] == "1"
    assert blueprint.attrs["fov"] == "100.0"
    assert blueprint.attrs["sensor_tick"] == "0.05"
    assert save_calls
    assert save_calls[0]["quality"] == 90
    assert save_calls[0]["format"] == "JPEG"
    assert recorder.frames_captured == 1
    assert recorder.last_error is None
    assert Path(index_path).exists()
    index_payload = Path(index_path).read_text(encoding="utf-8")
    assert '"frames_captured": 1' in index_payload
    assert '"frame": 10' in index_payload
    assert '"image_path": "00000010.jpg"' in index_payload


def test_camera_recorder_stop_destroy_are_safe_to_repeat(monkeypatch) -> None:
    case_dir = _case_dir("stop_destroy_are_safe")
    class _FakePillowImage:
        @staticmethod
        def fromarray(_array: np.ndarray) -> Any:
            class _Writer:
                def save(self, path: Path, *, format: str, quality: int) -> None:
                    del format, quality
                    Path(path).write_bytes(b"jpeg")

            return _Writer()

    fake_carla = type(
        "FakeCarla",
        (),
        {
            "Location": _FakeLocation,
            "Rotation": _FakeRotation,
            "Transform": _FakeTransform,
            "AttachmentType": _FakeAttachmentType,
        },
    )
    monkeypatch.setattr(camera_recorder, "require_carla", lambda: fake_carla)
    monkeypatch.setattr(camera_recorder, "_load_pillow_image_class", lambda: _FakePillowImage)

    sensor = _FakeSensor()
    recorder = camera_recorder.CarlaFrontRgbCameraRecorder(
        world=_FakeWorld(sensor=sensor, blueprint=_FakeBlueprint()),
        vehicle_actor=_FakeVehicleActor(),
        actor_id=1,
        map_name="Town10HD_Opt",
        base_output_dir=case_dir / "camera",
        config=camera_recorder.FrontRgbCameraConfig(
            image_width=2,
            image_height=1,
            fov_deg=90.0,
            sensor_tick_seconds=0.05,
            jpeg_quality=90,
        ),
    )
    recorder.start()

    recorder.stop()
    recorder.stop()
    recorder.destroy()
    recorder.destroy()

    assert sensor.stop_calls >= 1
    assert sensor.destroy_calls == 1


def test_camera_recorder_records_callback_error(monkeypatch) -> None:
    case_dir = _case_dir("records_callback_error")
    class _FailingPillowImage:
        @staticmethod
        def fromarray(_array: np.ndarray) -> Any:
            class _Writer:
                def save(self, path: Path, *, format: str, quality: int) -> None:
                    del path, format, quality
                    raise RuntimeError("encode failed")

            return _Writer()

    fake_carla = type(
        "FakeCarla",
        (),
        {
            "Location": _FakeLocation,
            "Rotation": _FakeRotation,
            "Transform": _FakeTransform,
            "AttachmentType": _FakeAttachmentType,
        },
    )
    monkeypatch.setattr(camera_recorder, "require_carla", lambda: fake_carla)
    monkeypatch.setattr(camera_recorder, "_load_pillow_image_class", lambda: _FailingPillowImage)

    sensor = _FakeSensor()
    recorder = camera_recorder.CarlaFrontRgbCameraRecorder(
        world=_FakeWorld(sensor=sensor, blueprint=_FakeBlueprint()),
        vehicle_actor=_FakeVehicleActor(),
        actor_id=1,
        map_name="Town10HD_Opt",
        base_output_dir=case_dir / "camera",
        config=camera_recorder.FrontRgbCameraConfig(
            image_width=2,
            image_height=1,
            fov_deg=90.0,
            sensor_tick_seconds=0.05,
            jpeg_quality=90,
        ),
    )
    recorder.start()

    class _FakeImage:
        frame = 1
        timestamp = 1.0
        width = 2
        height = 1
        raw_data = bytes([0, 0, 0, 255, 0, 0, 0, 255])

    sensor.emit(_FakeImage())
    assert recorder.last_error is not None
    assert "encode failed" in recorder.last_error
