#!/usr/bin/env python3
"""Scatter scanner — rank the active sector's niches by sold-price differentiation.

Finds WHERE prices are scattered (inefficient markets = bargains in the low tail),
not just what one item is worth. Reads sold comps through the cache + monthly pull
budget, so a warm cache costs zero pulls.

  python scan.py --sector cameras-lenses --mode thirdparty   # real sold comps (cached)
  python scan.py --sector cameras-lenses --mode mock          # no keys, fixture data
  python scan.py --no-history                                 # don't append to history

Each scan is appended to data/scatter_history.json (unless --no-history) so niche
scatter can be tracked over time. Read-only; never bids.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

try:
    from dotenv import load_dotenv  # noqa: E402
    load_dotenv()
except ImportError:
    pass

from valbot.config import ROOT, apply_sector, load_config  # noqa: E402
from valbot.ebay_client import get_source  # noqa: E402
from valbot.scan import append_history, format_scan, scan  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="valbot scatter scanner (read-only)")
    p.add_argument("--sector", default=None, help="sector profile (default: active_sector)")
    p.add_argument("--mode", choices=["mock", "thirdparty", "browse"], default="thirdparty")
    p.add_argument("--config", default=None, help="path to config.yaml")
    p.add_argument("--mock-data", default=None, help="path to mock listings JSON")
    p.add_argument("--no-history", action="store_true", help="don't append to scatter_history.json")
    args = p.parse_args()

    cfg = apply_sector(load_config(args.config), args.sector)
    source = get_source(cfg, args.mode, mock_path=args.mock_data)

    print(f"Sector: {cfg.get('active_sector')}  (mode: {args.mode})")
    rows = scan(cfg, source)
    print(format_scan(rows, cfg))

    cache = getattr(source, "cache", None)
    if cache is not None:
        budget = cfg["thirdparty"]["sold"].get("monthly_pull_budget")
        remaining = cache.remaining(budget)
        used = cache.pulls_this_month()
        if remaining is not None:
            print(f"\nPulls this month: {used}/{budget}  ({remaining} left).")

    if not args.no_history:
        append_history(rows, cfg, ROOT / "data" / "scatter_history.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
