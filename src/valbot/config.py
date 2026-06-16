"""Config loading. YAML on disk, env vars for secrets only."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT / "config.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def secret(name: str, required: bool = True) -> str | None:
    """Read a secret from the environment. Never hard-code keys."""
    val = os.environ.get(name)
    if required and not val:
        raise RuntimeError(
            f"Missing required secret: {name}. Set it as a repo secret / env var."
        )
    return val
