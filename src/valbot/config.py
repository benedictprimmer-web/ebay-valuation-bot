"""Config loading. YAML on disk, env vars for secrets only.

The base blocks (valuation, fees, fx, search...) are neutral defaults. Each real
category — cards, cameras, etc. — lives under `sectors` and overrides only the bits
that differ for it. `apply_sector` merges a sector's overrides over the base so the
bot can switch what it values without touching code. See config.yaml.
"""

from __future__ import annotations

import copy
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


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge `override` into `base` (override wins). Lists are replaced."""
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def apply_sector(cfg: dict, sector: str | None) -> dict:
    """Return a copy of cfg with one sector's overrides merged in.

    sector=None falls back to cfg['active_sector']. Raises if the named sector is
    unknown. The base cfg is never mutated; tests that call load_config() directly
    keep the neutral defaults.
    """
    name = sector or cfg.get("active_sector")
    sectors = cfg.get("sectors", {})
    if not name:
        return copy.deepcopy(cfg)
    if name not in sectors:
        raise ValueError(
            f"unknown sector: {name!r}. Available: {', '.join(sectors) or '(none)'}"
        )
    merged = copy.deepcopy(cfg)
    _deep_merge(merged, copy.deepcopy(sectors[name].get("overrides", {})))
    merged["active_sector"] = name
    return merged


def secret(name: str, required: bool = True) -> str | None:
    """Read a secret from the environment. Never hard-code keys."""
    val = os.environ.get(name)
    if required and not val:
        raise RuntimeError(
            f"Missing required secret: {name}. Set it as a repo secret / env var."
        )
    return val
