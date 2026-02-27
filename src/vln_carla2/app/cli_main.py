"""Thin CLI entrypoint that delegates to CLI adapter and app composition root."""

from __future__ import annotations

import sys
from typing import Sequence

from vln_carla2.adapters.cli.main import run_cli
from vln_carla2.app.bootstrap import build_cli_application


def main(argv: Sequence[str] | None = None) -> int:
    app = build_cli_application()
    return int(run_cli(argv, app))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

