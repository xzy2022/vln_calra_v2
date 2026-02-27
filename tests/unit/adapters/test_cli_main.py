import sys

from vln_carla2.adapters.cli import main as legacy_cli_main


def test_legacy_cli_main_prints_migration_message_and_returns_error(
    capsys,
) -> None:
    exit_code = legacy_cli_main.main(["scene", "run"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "vln_carla2.app.cli_main" in captured.err


def test_legacy_cli_main_module_entrypoint_behaviour(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["python", "scene", "run"])
    exit_code = legacy_cli_main.main(sys.argv[1:])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "entrypoint was moved" in captured.err
