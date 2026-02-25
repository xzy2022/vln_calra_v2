"""Dependency wiring for the control-track runtime."""

from dataclasses import dataclass
from typing import Any

from vln_carla2.domain.model.vehicle_id import VehicleId
from vln_carla2.domain.services.simple_speed_controller import SimpleSpeedController
from vln_carla2.infrastructure.carla.actuator_raw import CarlaRawMotionActuator
from vln_carla2.infrastructure.carla.clock import CarlaClock
from vln_carla2.infrastructure.carla.state_reader import CarlaVehicleStateReader
from vln_carla2.usecases.run_control_loop import RunControlLoop


class StdoutLogger:
    """Small logger adapter for CLI usage."""

    def info(self, message: str) -> None:
        print(f"[INFO] {message}")

    def warn(self, message: str) -> None:
        print(f"[WARN] {message}")

    def error(self, message: str) -> None:
        print(f"[ERROR] {message}")


@dataclass(slots=True)
class ControlContainer:
    """Built runtime dependencies for the control use case."""

    run_control_loop: RunControlLoop
    vehicle_id: VehicleId


def build_control_container(world: Any, ego_vehicle: Any) -> ControlContainer:
    """Compose control-track use case with CARLA adapters and domain service."""
    vehicle_id = VehicleId(value=int(ego_vehicle.id))
    state_reader = CarlaVehicleStateReader(world)
    motion_actuator = CarlaRawMotionActuator(world)
    clock = CarlaClock(world)
    logger = StdoutLogger()
    controller = SimpleSpeedController()

    run_control_loop = RunControlLoop(
        state_reader=state_reader,
        motion_actuator=motion_actuator,
        clock=clock,
        logger=logger,
        controller=controller,
    )
    return ControlContainer(run_control_loop=run_control_loop, vehicle_id=vehicle_id)
