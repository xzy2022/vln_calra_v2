from vln_carla2.adapters.cli.commands import (
    ExpRunCommand,
    OperatorRunCommand,
    SceneRunCommand,
    TrackingRunCommand,
)
from vln_carla2.adapters.cli.dto import SpawnVehicleRequest, VehicleRefInput
from vln_carla2.adapters.cli.mappers import (
    to_exp_run_request,
    to_operator_run_request,
    to_scene_run_request,
    to_tracking_run_request,
)


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
        episode_spec="datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
        control_target=VehicleRefInput(scheme="actor", value="42"),
        forward_distance_m=20.0,
        target_speed_mps=5.0,
        max_steps=800,
    )

    request = to_exp_run_request(command)

    assert request.control_target.scheme == "actor"
    assert request.control_target.value == "42"
    assert (
        request.episode_spec
        == "datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json"
    )


def test_to_scene_run_request_maps_export_episode_spec_flag() -> None:
    command = SceneRunCommand(
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
        scene_import="datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
        scene_export_path="artifacts/scene_out.json",
        export_episode_spec=True,
    )

    request = to_scene_run_request(command)

    assert request.scene_import == command.scene_import
    assert request.scene_export_path == command.scene_export_path
    assert request.export_episode_spec is True


def test_to_tracking_run_request_maps_tracking_parameters() -> None:
    command = TrackingRunCommand(
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
        episode_spec="datasets/town10hd_val_v1/episodes/ep_000001/episode_spec.json",
        control_target=VehicleRefInput(scheme="role", value="ego"),
        target_speed_mps=5.0,
        max_steps=None,
        route_step_m=2.0,
        route_max_points=2000,
        lookahead_base_m=3.0,
        lookahead_speed_gain=0.35,
        lookahead_min_m=2.5,
        lookahead_max_m=12.0,
        wheelbase_m=2.85,
        max_steer_angle_deg=70.0,
        pid_kp=1.0,
        pid_ki=0.05,
        pid_kd=0.0,
        max_throttle=0.75,
        max_brake=0.30,
        goal_distance_tolerance_m=1.5,
        goal_yaw_tolerance_deg=15.0,
        slowdown_distance_m=12.0,
        min_slow_speed_mps=0.8,
        steer_rate_limit_per_step=0.10,
    )

    request = to_tracking_run_request(command)

    assert request.episode_spec == command.episode_spec
    assert request.control_target.scheme == "role"
    assert request.control_target.value == "ego"
    assert request.max_steps is None
    assert request.route_step_m == 2.0
