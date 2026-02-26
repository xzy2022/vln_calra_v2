from vln_carla2.app.settings import Settings


def test_settings_no_rendering_mode_maps_true() -> None:
    settings = Settings(no_rendering=True)

    assert settings.no_rendering_mode is True


def test_settings_no_rendering_mode_defaults_false() -> None:
    settings = Settings()

    assert settings.no_rendering_mode is False


def test_settings_offscreen_mode_maps_true() -> None:
    settings = Settings(offscreen=True)

    assert settings.offscreen_mode is True


def test_settings_offscreen_mode_defaults_false() -> None:
    settings = Settings()

    assert settings.offscreen_mode is False
