"""Planning map source outbound port."""

from __future__ import annotations

from typing import Protocol

from vln_carla2.domain.model.planning_map import PlanningMapSeed
from vln_carla2.domain.model.pose2d import Pose2D


class PlanningMapSourcePort(Protocol):
    """Provide snapshot data for planning map construction."""

    def snapshot(
        self,
        *,
        map_name: str,
        start: Pose2D,
        goal: Pose2D,
    ) -> PlanningMapSeed:
        ...

