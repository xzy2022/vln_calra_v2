"""Spawn one vehicle at current spectator XY with fixed Z and yaw."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from vln_carla2.domain.model.scene_template import SceneObject, SceneObjectKind, ScenePose
from vln_carla2.domain.services.spawn_rules import spawn_z_from_ground
from vln_carla2.usecases.operator.ports.vehicle_dto import SpawnVehicleRequest, VehicleDescriptor
from vln_carla2.usecases.operator.spawn_vehicle import SpawnVehicle
from vln_carla2.usecases.scene_editor.ports.scene_object_recorder import (
    SceneObjectRecorderPort,
)
from vln_carla2.usecases.spectator.ports.spectator_camera import SpectatorCameraPort


class GroundZResolverPort(Protocol):
    """Resolve road-projected ground Z from XY."""

    def resolve_ground_z(self, x: float, y: float) -> float:
        ...


@dataclass(slots=True)
class SpawnVehicleAtSpectatorXY:
    """Read spectator XY and spawn one vehicle at road ground Z + offset."""

    spectator_camera: SpectatorCameraPort
    ground_z_resolver: GroundZResolverPort
    spawn_vehicle: SpawnVehicle
    blueprint_filter: str = "vehicle.tesla.model3"
    vehicle_z_offset: float = 0.05
    spawn_yaw: float = 180.0
    role_name: str = "ego"
    object_kind: SceneObjectKind = SceneObjectKind.VEHICLE
    recorder: SceneObjectRecorderPort | None = None

    def run(self) -> VehicleDescriptor:
        spectator_transform = self.spectator_camera.get_spectator_transform()
        spawn_x = float(spectator_transform.location.x)
        spawn_y = float(spectator_transform.location.y)
        ground_z = self.ground_z_resolver.resolve_ground_z(spawn_x, spawn_y)
        spawn_z = spawn_z_from_ground(ground_z=ground_z, vehicle_offset=self.vehicle_z_offset)
        request = SpawnVehicleRequest(
            blueprint_filter=self.blueprint_filter,
            spawn_x=spawn_x,
            spawn_y=spawn_y,
            spawn_z=spawn_z,
            spawn_yaw=float(self.spawn_yaw),
            role_name=self.role_name,
        )
        vehicle = self.spawn_vehicle.run(request)
        if self.recorder is not None:
            self.recorder.record(
                SceneObject(
                    kind=self.object_kind,
                    blueprint_id=vehicle.type_id,
                    role_name=vehicle.role_name,
                    pose=ScenePose(
                        x=float(request.spawn_x),
                        y=float(request.spawn_y),
                        z=float(request.spawn_z),
                        yaw=float(request.spawn_yaw),
                    ),
                )
            )
        return vehicle
