#!/usr/bin/env python3
"""Entry point. Read-only valuation + alert run.

  python run.py --mode mock --dry-run     # test the whole pipeline, no keys
  python run.py --mode live               # live data + real WhatsApp alerts

Mode 'live' needs EBAY_APP_ID, EBAY_CERT_ID, CALLMEBOT_PHONE, CALLMEBOT_APIKEY in env.
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

from valbot.alert import get_alerter  # noqa: E402
from valbot.config import ROOT, apply_sector, load_config  # noqa: E402
from valbot.ebay_client import get_source  # noqa: E402
from valbot.formatting import format_summary  # noqa: E402
from valbot.pipeline import run_pipeline  # noqa: E402
from valbot.store import Store  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="eBay valuation bot (read-only)")
    p.add_argument(
        "--mode",
        choices=["mock", "thirdparty", "browse"],
        default="mock",
        help="mock=fixture; thirdparty=RapidAPI (default live); browse=official eBay API",
    )
    p.add_argument("--dry-run", action="store_true", help="print alerts, don't send")
    p.add_argument("--config", default=None, help="path to config.yaml")
    p.add_argument("--mock-data", default=None, help="path to mock listings JSON")
    p.add_argument("--sector", default=None, help="sector profile (default: active_sector)")
    args = p.parse_args()

    cfg = apply_sector(load_config(args.config), args.sector)
    print(f"Sector: {cfg.get('active_sector')}")
    source = get_source(cfg, args.mode, mock_path=args.mock_data)
    # In mock mode default to dry-run alerts unless secrets are present.
    dry = args.dry_run or args.mode == "mock"
    alerter = get_alerter(dry_run=dry)
    store = Store(ROOT / "data")

    result = run_pipeline(cfg, source, alerter, store)
    print(format_summary(result.assessments, result.alerts))
    print(f"Sent {result.sent} alert(s)." + (" (dry-run)" if dry else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
