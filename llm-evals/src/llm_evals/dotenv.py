"""Load API keys from a local .env file.

The file is optional and never committed (see .gitignore). Lines look like
KEY=value. Blank lines and lines that start with # are skipped. A value may be
wrapped in single or double quotes. Variables that are already set in the
environment win, so a key exported in the shell or set as a CI secret is never
overwritten by the file.

This is a small loader on purpose. It keeps the package free of an extra
dependency for one feature.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_FILE_NAME = ".env"


def find_env_file(start: Path | None = None) -> Path | None:
    """Return the nearest .env file, looking from the start folder upwards."""
    folder = (start or Path.cwd()).resolve()
    for candidate in [folder, *folder.parents]:
        path = candidate / ENV_FILE_NAME
        if path.is_file():
            return path
    return None


def parse_env_lines(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def load_env_file(path: Path | None = None) -> list[str]:
    """Load a .env file into os.environ. Returns the names that were set.

    Existing environment variables are kept. Nothing is logged, so key values
    never appear in output.
    """
    env_path = path or find_env_file()
    if env_path is None or not env_path.is_file():
        return []
    values = parse_env_lines(env_path.read_text(encoding="utf-8").splitlines())
    loaded: list[str] = []
    for key, value in values.items():
        if key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded
