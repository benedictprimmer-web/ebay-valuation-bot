#!/usr/bin/env python3
"""Option 3 — semi-manual targets mode (read-only).

Hand it a watch list of cards; it values each against real Card API sold comps and
prints the max bid, margin, confidence and comp count. No live auction feed needed.

  python targets.py --watchlist data/watchlist.example.csv --mode mock   # no keys
  python targets.py --watchlist my_cards.csv                             # real comps

Real comps (--mode thirdparty, the default) need CARDAPI_KEY in the environment.
Results are also written to JSON (--out) so they can feed calibration later.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from valbot.config import ROOT, apply_sector, load_config  # noqa: E402
from valbot.ebay_client import get_source  # noqa: E402
from valbot.formatting import format_targets, target_to_dict  # noqa: E402
from valbot.targets import load_watchlist, run_targets  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="eBay valuation bot — targets mode (read-only)")
    p.add_argument("--watchlist", required=True, help="path to watch list (.csv/.tsv/.json)")
    p.add_argument(
        "--mode",
        choices=["mock", "thirdparty", "browse"],
        default="thirdparty",
        help="thirdparty=Card API sold comps (default, needs CARDAPI_KEY); mock=fixture",
    )
    p.add_argument("--config", default=None, help="path to config.yaml")
    p.add_argument("--mock-data", default=None, help="path to mock listings JSON")
    p.add_argument("--out", default=None, help="where to write JSON results")
    p.add_argument("--sector", default=None, help="sector profile (default: active_sector)")
    args = p.parse_args()

    cfg = apply_sector(load_config(args.config), args.sector)
    print(f"Sector: {cfg.get('active_sector')}")
    source = get_source(cfg, args.mode, mock_path=args.mock_data)
    watchlist = load_watchlist(args.watchlist, identity=cfg.get("identity", "card"))

    results = run_targets(cfg, source, watchlist)
    print(format_targets(results))

    out_path = Path(args.out) if args.out else ROOT / "data" / "targets_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([target_to_dict(r) for r in results], indent=2), encoding="utf-8"
    )
    print(f"\nWrote {len(results)} result(s) to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
