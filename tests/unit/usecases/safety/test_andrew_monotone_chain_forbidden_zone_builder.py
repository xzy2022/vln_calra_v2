import pytest

from vln_carla2.domain.model.point2d import Point2D
from vln_carla2.usecases.scene.andrew_monotone_chain_forbidden_zone_builder import (
    AndrewMonotoneChainForbiddenZoneBuilder,
)


def test_build_constructs_convex_hull_and_removes_inner_points() -> None:
    builder = AndrewMonotoneChainForbiddenZoneBuilder()
    zone = builder.build(
        [
            Point2D(x=0.0, y=0.0),
            Point2D(x=1.0, y=0.0),
            Point2D(x=1.0, y=1.0),
            Point2D(x=0.0, y=1.0),
            Point2D(x=0.5, y=0.5),
            Point2D(x=1.0, y=0.0),
        ]
    )

    assert {(point.x, point.y) for point in zone.vertices} == {
        (0.0, 0.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (0.0, 1.0),
    }


def test_build_rejects_less_than_three_unique_points() -> None:
    builder = AndrewMonotoneChainForbiddenZoneBuilder()

    with pytest.raises(ValueError, match="at least 3 unique obstacle points"):
        builder.build(
            [
                Point2D(x=0.0, y=0.0),
                Point2D(x=1.0, y=1.0),
            ]
        )


def test_build_rejects_collinear_points() -> None:
    builder = AndrewMonotoneChainForbiddenZoneBuilder()

    with pytest.raises(ValueError, match="collinear"):
        builder.build(
            [
                Point2D(x=0.0, y=0.0),
                Point2D(x=1.0, y=1.0),
                Point2D(x=2.0, y=2.0),
                Point2D(x=3.0, y=3.0),
            ]
        )

