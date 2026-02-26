from vln_carla2.domain.services.spawn_rules import spawn_z_from_ground


def test_spawn_z_from_ground_adds_offset() -> None:
    assert spawn_z_from_ground(ground_z=2.0, vehicle_offset=0.15) == 2.15


def test_spawn_z_from_ground_supports_negative_ground() -> None:
    assert spawn_z_from_ground(ground_z=-3.5, vehicle_offset=0.3) == -3.2
