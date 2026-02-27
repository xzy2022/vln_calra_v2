"""Domain aggregate for one forbidden traffic zone polygon."""

from dataclasses import dataclass

from vln_carla2.domain.model.point2d import Point2D


@dataclass(frozen=True, slots=True)
class ForbiddenZone:
    """Forbidden zone represented by polygon vertices in XY plane."""

    vertices: tuple[Point2D, ...]

    def __post_init__(self) -> None:
        vertices = tuple(self.vertices)
        if len(vertices) < 3:
            raise ValueError("ForbiddenZone requires at least 3 vertices")
        unique_vertices = {(vertex.x, vertex.y) for vertex in vertices}
        if len(unique_vertices) < 3:
            raise ValueError("ForbiddenZone requires at least 3 unique vertices")
        object.__setattr__(self, "vertices", vertices)
