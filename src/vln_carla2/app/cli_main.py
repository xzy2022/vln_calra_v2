"""Thin CLI entrypoint that delegates to CLI adapter and app composition root."""

from __future__ import annotations

import sys
from typing import Sequence

from vln_carla2.adapters.cli.env import get_default_carla_exe, load_env_from_dotenv
from vln_carla2.adapters.cli.main import CliDispatchConfig, run_cli
from vln_carla2.app.bootstrap import build_cli_application


def build_cli_dispatch_config() -> CliDispatchConfig:
    """Load entrypoint env and build CLI parser defaults."""
    load_env_from_dotenv()
    return CliDispatchConfig(default_carla_exe=get_default_carla_exe())


def main(argv: Sequence[str] | None = None) -> int:
    app = build_cli_application()
    config = build_cli_dispatch_config()
    return int(run_cli(argv, app, config=config))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
