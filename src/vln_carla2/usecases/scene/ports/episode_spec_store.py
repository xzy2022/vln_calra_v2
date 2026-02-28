"""Port for saving episode specs."""

from typing import Protocol

from vln_carla2.domain.model.episode_spec import EpisodeSpec


class EpisodeSpecStorePort(Protocol):
    """Persistence port for episode-spec JSON."""

    def save(self, spec: EpisodeSpec, path: str | None) -> str:
        ...
