"""CARLA front RGB camera recorder for per-frame image logging."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any
import weakref

import numpy as np

from vln_carla2.infrastructure.carla.types import require_carla

_CAMERA_BLUEPRINT_ID = "sensor.camera.rgb"


def _load_pillow_image_class() -> Any:
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Pillow package is required for camera JPEG logging. "
            "Install Pillow in the runtime environment."
        ) from exc
    return Image


@dataclass(frozen=True, slots=True)
class FrontRgbCameraConfig:
    """Configuration for front RGB camera capture."""

    image_width: int
    image_height: int
    fov_deg: float
    sensor_tick_seconds: float
    jpeg_quality: int
    mount_x: float = 1.5
    mount_y: float = 0.0
    mount_z: float = 2.2
    mount_pitch_deg: float = 0.0
    mount_yaw_deg: float = 0.0
    mount_roll_deg: float = 0.0


@dataclass(slots=True, weakref_slot=True)
class CarlaFrontRgbCameraRecorder:
    """
    Spawn one front RGB camera on a vehicle and record aligned frame metadata.

    The recorder writes JPEG frames to:
      <base_output_dir>/front_rgb/{frame:08d}.jpg
    and writes one index file:
      <base_output_dir>/front_rgb/index.json
    """

    world: Any
    vehicle_actor: Any
    actor_id: int
    map_name: str
    base_output_dir: Path
    config: FrontRgbCameraConfig
    _camera_dir: Path = field(init=False)
    _sensor: Any | None = field(init=False, default=None)
    _frames: list[dict[str, object]] = field(init=False, default_factory=list)
    _last_error: str | None = field(init=False, default=None)
    _lock: Lock = field(init=False, default_factory=Lock)
    _image_cls: Any | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self._camera_dir = self.base_output_dir / "front_rgb"

    @property
    def output_dir(self) -> str:
        return str(self._camera_dir)

    @property
    def index_path(self) -> str:
        return str(self._camera_dir / "index.json")

    @property
    def frames_captured(self) -> int:
        with self._lock:
            return len(self._frames)

    @property
    def last_error(self) -> str | None:
        with self._lock:
            return self._last_error

    def start(self) -> None:
        carla = require_carla()
        self._image_cls = _load_pillow_image_class()
        self._camera_dir.mkdir(parents=True, exist_ok=True)

        blueprint = self.world.get_blueprint_library().find(_CAMERA_BLUEPRINT_ID)
        blueprint.set_attribute("image_size_x", str(self.config.image_width))
        blueprint.set_attribute("image_size_y", str(self.config.image_height))
        blueprint.set_attribute("fov", str(self.config.fov_deg))
        blueprint.set_attribute("sensor_tick", str(self.config.sensor_tick_seconds))

        transform = carla.Transform(
            carla.Location(
                x=self.config.mount_x,
                y=self.config.mount_y,
                z=self.config.mount_z,
            ),
            carla.Rotation(
                pitch=self.config.mount_pitch_deg,
                yaw=self.config.mount_yaw_deg,
                roll=self.config.mount_roll_deg,
            ),
        )
        self._sensor = self.world.spawn_actor(
            blueprint,
            transform,
            attach_to=self.vehicle_actor,
            attachment_type=carla.AttachmentType.Rigid,
        )
        weak_self = weakref.ref(self)
        self._sensor.listen(lambda image: self._on_image(weak_self, image))

    def stop(self) -> None:
        sensor = self._sensor
        if sensor is None:
            return
        sensor.stop()

    def destroy(self) -> None:
        sensor = self._sensor
        self._sensor = None
        if sensor is None:
            return
        sensor.destroy()

    def save_index(self) -> str:
        with self._lock:
            frames_snapshot = list(self._frames)
        first_frame = frames_snapshot[0]["frame"] if frames_snapshot else None
        last_frame = frames_snapshot[-1]["frame"] if frames_snapshot else None
        payload = {
            "map_name": self.map_name,
            "actor_id": int(self.actor_id),
            "camera": {
                "blueprint": _CAMERA_BLUEPRINT_ID,
                "type": "front_rgb",
                "image_width": int(self.config.image_width),
                "image_height": int(self.config.image_height),
                "fov_deg": float(self.config.fov_deg),
                "sensor_tick_seconds": float(self.config.sensor_tick_seconds),
                "jpeg_quality": int(self.config.jpeg_quality),
                "mount": {
                    "x": float(self.config.mount_x),
                    "y": float(self.config.mount_y),
                    "z": float(self.config.mount_z),
                    "pitch_deg": float(self.config.mount_pitch_deg),
                    "yaw_deg": float(self.config.mount_yaw_deg),
                    "roll_deg": float(self.config.mount_roll_deg),
                },
            },
            "summary": {
                "frames_captured": len(frames_snapshot),
                "first_frame": first_frame,
                "last_frame": last_frame,
            },
            "frames": frames_snapshot,
        }
        index_file = self._camera_dir / "index.json"
        index_file.parent.mkdir(parents=True, exist_ok=True)
        index_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(index_file)

    @staticmethod
    def _on_image(weak_self: "weakref.ReferenceType[CarlaFrontRgbCameraRecorder]", image: Any) -> None:
        owner = weak_self()
        if owner is None:
            return
        owner._handle_image(image)

    def _handle_image(self, image: Any) -> None:
        try:
            image_cls = self._image_cls
            if image_cls is None:
                raise RuntimeError("camera recorder was not started")

            frame = int(image.frame)
            timestamp = float(image.timestamp)
            width = int(image.width)
            height = int(image.height)
            array = np.frombuffer(image.raw_data, dtype=np.uint8)
            array = array.reshape((height, width, 4))
            rgb = array[:, :, :3][:, :, ::-1]
            image_name = f"{frame:08d}.jpg"
            image_path = self._camera_dir / image_name
            image_cls.fromarray(rgb).save(
                image_path,
                format="JPEG",
                quality=int(self.config.jpeg_quality),
            )

            vehicle_transform = self.vehicle_actor.get_transform()
            vehicle_velocity = self.vehicle_actor.get_velocity()
            vehicle_control = self.vehicle_actor.get_control()
            speed_mps = math.sqrt(
                float(vehicle_velocity.x) * float(vehicle_velocity.x)
                + float(vehicle_velocity.y) * float(vehicle_velocity.y)
                + float(vehicle_velocity.z) * float(vehicle_velocity.z)
            )
            frame_payload = {
                "frame": frame,
                "timestamp": timestamp,
                "image_path": image_name,
                "pose": {
                    "x": float(vehicle_transform.location.x),
                    "y": float(vehicle_transform.location.y),
                    "z": float(vehicle_transform.location.z),
                    "yaw_deg": float(vehicle_transform.rotation.yaw),
                },
                "speed_mps": float(speed_mps),
                "control": {
                    "throttle": float(getattr(vehicle_control, "throttle", 0.0)),
                    "brake": float(getattr(vehicle_control, "brake", 0.0)),
                    "steer": float(getattr(vehicle_control, "steer", 0.0)),
                },
            }
            with self._lock:
                self._frames.append(frame_payload)
        except Exception as exc:
            with self._lock:
                if self._last_error is None:
                    self._last_error = f"{type(exc).__name__}: {exc}"
