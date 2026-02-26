import pytest
from pathlib import Path

from vln_carla2.infrastructure.carla.server_launcher import (
    build_carla_server_command,
    is_loopback_host,
)


def test_build_carla_server_command_for_normal_mode() -> None:
    executable = Path(__file__)

    command = build_carla_server_command(
        executable_path=str(executable),
        rpc_port=2000,
    )

    assert command == [
        str(executable),
        "--carla-rpc-port=2000",
        "-nosound",
        "-quality-level=Epic",
    ]


def test_build_carla_server_command_for_offscreen_and_no_rendering() -> None:
    executable = Path(__file__)

    command = build_carla_server_command(
        executable_path=str(executable),
        rpc_port=2000,
        offscreen=True,
        no_rendering=True,
        no_sound=False,
        quality_level="low",
    )

    assert command[0] == str(executable)
    assert "--carla-rpc-port=2000" in command
    assert "-RenderOffScreen" in command
    assert "--no-rendering" in command
    assert "-quality-level=Low" in command
    assert "-nosound" not in command


def test_build_carla_server_command_rejects_invalid_quality() -> None:
    executable = Path(__file__)

    with pytest.raises(ValueError, match="quality_level must be one of"):
        build_carla_server_command(
            executable_path=str(executable),
            rpc_port=2000,
            quality_level="Medium",
        )


def test_is_loopback_host() -> None:
    assert is_loopback_host("127.0.0.1")
    assert is_loopback_host("localhost")
    assert is_loopback_host("::1")
    assert not is_loopback_host("192.168.1.12")
