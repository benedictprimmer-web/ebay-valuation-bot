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
        choices=["mock", "thirdparty", "browse", "hybrid"],
        default="mock",
        help="mock=fixture; thirdparty=RapidAPI; browse=eBay API; "
             "hybrid=Browse auctions + cached sold comps",
    )
    p.add_argument("--dry-run", action="store_true", help="print alerts, don't send")
    p.add_argument("--config", default=None, help="path to config.yaml")
    p.add_argument("--mock-data", default=None, help="path to mock listings JSON")
    p.add_argument("--sector", default=None, help="sector profile (default: active_sector)")
    p.add_argument(
        "--heartbeat",
        action="store_true",
        help="if no opportunity alerts fire, send one confirmation message instead",
    )
    p.add_argument(
        "--log-all",
        action="store_true",
        help="append every assessment (not just alerts) to data/observations.jsonl",
    )
    p.add_argument(
        "--daily-summary",
        action="store_true",
        help="send ONE WhatsApp summary of today's deal flow (even if 0 found) and exit. "
             "Reads the logs only — no data source, no sold-feed pulls.",
    )
    p.add_argument(
        "--weekly-digest",
        action="store_true",
        help="send ONE WhatsApp digest of the last 7 days' deal flow and exit. "
             "Reads the logs only — no data source, no sold-feed pulls.",
    )
    args = p.parse_args()

    cfg = apply_sector(load_config(args.config), args.sector)
    print(f"Sector: {cfg.get('active_sector')}")

    # Digest modes: pure reporting off the on-disk logs. Short-circuit before any data
    # source, so they need no eBay/RapidAPI keys — only CallMeBot to send.
    if args.daily_summary or args.weekly_digest:
        from valbot.summary import build_daily_summary, build_weekly_digest

        alerter = get_alerter(dry_run=args.dry_run)
        builder = build_weekly_digest if args.weekly_digest else build_daily_summary
        msg = builder(cfg, ROOT / "data")
        alerter.send(msg)
        print(msg)
        return 0

    source = get_source(cfg, args.mode, mock_path=args.mock_data)
    # In mock mode default to dry-run alerts unless secrets are present.
    dry = args.dry_run or args.mode == "mock"
    alerter = get_alerter(dry_run=dry)
    store = Store(ROOT / "data")

    result = run_pipeline(cfg, source, alerter, store)
    print(format_summary(result.assessments, result.alerts))
    print(f"Sent {result.sent} alert(s)." + (" (dry-run)" if dry else ""))

    if args.log_all:
        n = store.log_observations(result.assessments)
        print(f"Logged {n} observation(s) to data/observations.jsonl.")

    # Heartbeat: real alerts already went out for any opportunity; if there were none,
    # send one confirmation so you know the run happened and CallMeBot is wired.
    if args.heartbeat and result.sent == 0:
        alerter.send(
            f"🤖 valbot test — {cfg.get('active_sector')}: assessed "
            f"{len(result.assessments)} auction(s), no opportunities right now. "
            "CallMeBot is working."
        )
        print("Sent heartbeat confirmation message.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
