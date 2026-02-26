from dataclasses import dataclass
from typing import Any

from vln_carla2.domain.model.scene_template import SceneObject, SceneObjectKind, ScenePose
from vln_carla2.infrastructure.carla.scene_object_spawner_adapter import (
    CarlaSceneObjectSpawnerAdapter,
)


@dataclass
class _Capture:
    kwargs: dict[str, Any] | None = None


def test_scene_object_spawner_adapter_maps_scene_object_to_spawn_call(monkeypatch) -> None:
    world = object()
    capture = _Capture()

    def fake_spawn_vehicle(**kwargs: Any) -> object:
        capture.kwargs = kwargs
        return object()

    monkeypatch.setattr(
        "vln_carla2.infrastructure.carla.scene_object_spawner_adapter.spawn_vehicle",
        fake_spawn_vehicle,
    )

    adapter = CarlaSceneObjectSpawnerAdapter(world)
    adapter.spawn(
        SceneObject(
            kind=SceneObjectKind.BARREL,
            blueprint_id="static.prop.barrel",
            role_name="barrel",
            pose=ScenePose(x=10.0, y=11.0, z=0.2, yaw=30.0),
        )
    )

    assert capture.kwargs == {
        "world": world,
        "blueprint_filter": "static.prop.barrel",
        "spawn_x": 10.0,
        "spawn_y": 11.0,
        "spawn_z": 0.2,
        "spawn_yaw": 30.0,
        "role_name": "barrel",
    }
