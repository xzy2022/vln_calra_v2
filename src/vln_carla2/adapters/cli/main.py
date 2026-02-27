"""Legacy CLI entrypoint kept only for migration guidance."""

from __future__ import annotations

import sys
from typing import Sequence

MIGRATION_MESSAGE = (
    "[ERROR] This entrypoint was moved. "
    "Use: python -m vln_carla2.app.cli_main <resource> <action> [options]"
)


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    print(MIGRATION_MESSAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
