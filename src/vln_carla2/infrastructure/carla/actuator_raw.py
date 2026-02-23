"""Raw VehicleControl actuator for CARLA."""

from typing import Any

from vln_carla2.domain.model.simple_command import ControlCommand
from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.infrastructure.carla.types import require_carla
from vln_carla2.usecases.ports.motion_actuator import MotionActuator


class CarlaRawMotionActuator(MotionActuator):
    """Apply domain ControlCommand via carla.VehicleControl."""

    def __init__(self, world: Any) -> None:
        self._world = world

    def apply(self, vehicle_id: VehicleId, command: ControlCommand) -> None:
        vehicle = self._require_vehicle(vehicle_id)
        carla = require_carla()
        vehicle.apply_control(
            carla.VehicleControl(
                throttle=command.throttle,
                brake=command.brake,
                steer=command.steer,
                hand_brake=False,
                reverse=False,
                manual_gear_shift=False,
            )
        )

    def _require_vehicle(self, vehicle_id: VehicleId) -> Any:
        actor = self._world.get_actor(vehicle_id.value)
        if actor is None:
            raise RuntimeError(f"Vehicle actor not found: id={vehicle_id.value}")
        return actor

