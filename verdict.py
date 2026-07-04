#!/usr/bin/env python3
"""Record your at-a-glance judgement on an alert, then print the updated calibration.

  python verdict.py a1b2c3 good
  python verdict.py a1b2c3 bad "shutter too high, comps look boxed"
  python verdict.py a1b2c3 bad --fair 150 "overpriced, that copy is scuffed"

`token` is the alert's ref code (shown in the WhatsApp) or its listing id. This fills the
matching record's `human_verdict` in data/outcomes.json — the early, cheap training label
that calibrate.py folds into per-niche tuning. It suggests only; it never edits the model.

This is the channel-agnostic capture point: relaying a chat message, a Telegram button,
or a WhatsApp webhook would all call the same Store.record_verdict under the hood.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from valbot.calibrate import compute_calibration, format_calibration  # noqa: E402
from valbot.config import ROOT  # noqa: E402
from valbot.store import Store  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="record a human verdict on an alert")
    p.add_argument("token", help="alert ref code (from the WhatsApp) or listing id")
    p.add_argument("verdict", help="good | bad  (also y/n)")
    p.add_argument("reason", nargs="*", help="optional free-text reason")
    p.add_argument("--fair", type=float, default=None, help="your own £ fair value estimate")
    args = p.parse_args()

    store = Store(ROOT / "data")
    reason = " ".join(args.reason).strip() or None
    try:
        match = store.record_verdict(
            args.token, args.verdict, reason=reason, fair_value=args.fair
        )
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    if match is None:
        print(
            f"No alert found for {args.token!r}. Check the ref code / listing id.",
            file=sys.stderr,
        )
        return 1

    hv = match["human_verdict"]
    fair = f", your fair £{hv['fair_value']:.0f}" if hv.get("fair_value") else ""
    print(f"Recorded {hv['verdict']} on {match.get('card', match['listing_id'])}{fair}.")
    if reason:
        print(f"  reason: {reason}")
    print()
    records = json.loads((ROOT / "data" / "outcomes.json").read_text(encoding="utf-8"))
    print(format_calibration(compute_calibration(records)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
