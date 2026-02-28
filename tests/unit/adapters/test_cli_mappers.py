from vln_carla2.adapters.cli.commands import ExpRunCommand, OperatorRunCommand
from vln_carla2.adapters.cli.dto import SpawnVehicleRequest, VehicleRefInput
from vln_carla2.adapters.cli.mappers import to_exp_run_request, to_operator_run_request


def test_to_operator_run_request_maps_nested_dtos() -> None:
    command = OperatorRunCommand(
        host="127.0.0.1",
        port=2000,
        timeout_seconds=10.0,
        map_name="Town10HD_Opt",
        mode="sync",
        fixed_delta_seconds=0.05,
        no_rendering=False,
        tick_sleep_seconds=0.05,
        offscreen=False,
        launch_carla=True,
        reuse_existing_carla=False,
        carla_exe="C:/CARLA/CarlaUE4.exe",
        carla_startup_timeout_seconds=45.0,
        quality_level="Epic",
        with_sound=False,
        keep_carla_server=False,
        follow=VehicleRefInput(scheme="role", value="ego"),
        z=20.0,
        spawn_request=SpawnVehicleRequest(
            blueprint_filter="vehicle.tesla.model3",
            spawn_x=1.0,
            spawn_y=2.0,
            spawn_z=0.1,
            spawn_yaw=180.0,
            role_name="ego",
        ),
        spawn_if_missing=True,
        strategy="parallel",
        steps=80,
        target_speed_mps=5.0,
        operator_warmup_ticks=1,
    )

    request = to_operator_run_request(command)

    assert request.follow.scheme == "role"
    assert request.follow.value == "ego"
    assert request.spawn_request.blueprint_filter == "vehicle.tesla.model3"
    assert request.spawn_request.spawn_x == 1.0
    assert request.strategy == "parallel"


def test_to_exp_run_request_maps_control_target() -> None:
    command = ExpRunCommand(
        host="127.0.0.1",
        port=2000,
        timeout_seconds=10.0,
        map_name="Town10HD_Opt",
        mode="sync",
        fixed_delta_seconds=0.05,
        no_rendering=False,
        tick_sleep_seconds=0.05,
        offscreen=False,
        launch_carla=False,
        reuse_existing_carla=False,
        carla_exe=None,
        carla_startup_timeout_seconds=45.0,
        quality_level="Epic",
        with_sound=False,
        keep_carla_server=False,
        scene_json="artifacts/scene.json",
        control_target=VehicleRefInput(scheme="actor", value="42"),
        forward_distance_m=20.0,
        target_speed_mps=5.0,
        max_steps=800,
    )

    request = to_exp_run_request(command)

    assert request.control_target.scheme == "actor"
    assert request.control_target.value == "42"
    assert request.scene_json == "artifacts/scene.json"

