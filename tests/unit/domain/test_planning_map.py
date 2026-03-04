import pytest

from vln_carla2.domain.model.planning_map import PlanningMap


def test_planning_map_world_grid_mapping_and_occupancy() -> None:
    planning_map = PlanningMap(
        map_name="Town10HD_Opt",
        resolution_m=1.0,
        min_x=0.0,
        max_x=4.0,
        min_y=0.0,
        max_y=4.0,
        width=4,
        height=4,
        occupied_cells=((1, 2), (1, 2)),
    )

    assert planning_map.world_to_grid(x=0.2, y=2.9) == (0, 2)
    assert planning_map.grid_to_world(cell_x=1, cell_y=2) == pytest.approx((1.5, 2.5))
    assert planning_map.is_cell_occupied(cell_x=1, cell_y=2) is True
    assert planning_map.is_cell_occupied(cell_x=0, cell_y=0) is False
    assert planning_map.is_cell_occupied(cell_x=-1, cell_y=0) is True
    assert planning_map.is_world_occupied(x=10.0, y=10.0) is True
    assert planning_map.occupied_cells == ((1, 2),)


def test_planning_map_rejects_out_of_bounds_world_to_grid() -> None:
    planning_map = PlanningMap(
        map_name="Town10HD_Opt",
        resolution_m=1.0,
        min_x=0.0,
        max_x=2.0,
        min_y=0.0,
        max_y=2.0,
        width=2,
        height=2,
    )

    with pytest.raises(ValueError, match="out of bounds"):
        planning_map.world_to_grid(x=3.0, y=1.0)

