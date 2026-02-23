import pytest


@pytest.mark.integration
def test_control_loop_smoke() -> None:
    carla = pytest.importorskip("carla")

    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(2.0)
    try:
        client.get_world()
    except Exception as exc:
        pytest.skip(f"CARLA server unavailable on 127.0.0.1:2000: {exc}")

    from vln_carla2.app.bootstrap import run
    from vln_carla2.app.settings import Settings

    result = run(Settings(steps=60, target_speed_mps=5.0))

    assert result.executed_steps == 60
    assert result.last_speed_mps > 0.1
    assert result.avg_speed_mps > 0.1
