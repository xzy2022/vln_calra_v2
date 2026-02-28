"""Environment helpers for CLI adapter startup."""

from __future__ import annotations

import os


def load_env_from_dotenv(path: str = ".env") -> None:
    """Best-effort dotenv loader for CLI startup."""
    if not os.path.exists(path):
        return

    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                if not key or key in os.environ:
                    continue

                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]
                os.environ[key] = value
    except OSError:
        return


def get_default_carla_exe() -> str | None:
    """Return default Carla executable path from env."""
    return os.getenv("CARLA_UE4_EXE")

