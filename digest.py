#!/usr/bin/env python3
"""A plain-English "how's it going" summary of everything the bot has collected.

  python digest.py

Reads the committed data files (no API calls, no pulls) and prints: how much the bot
has watched, the best opportunities it has seen, the monthly lookup budget used, and
how each niche's scatter is holding up. Safe to run anytime.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def _load_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> int:
    obs = _load_jsonl(DATA / "observations.jsonl")
    ledger = _load_json(DATA / "cache" / "pull_ledger.json", {})
    history = _load_json(DATA / "scatter_history.json", [])
    outcomes = _load_json(DATA / "outcomes.json", [])

    print("=" * 60)
    print("valbot digest")
    print("=" * 60)

    # ---- deal flow ----
    runs = sorted({o["ts"] for o in obs})
    alerts = [o for o in obs if o.get("is_alert")]
    models_seen = defaultdict(int)
    for o in obs:
        models_seen[o["model"]] += 1
    print(f"\nDEAL FLOW ({len(obs)} auctions assessed across {len(runs)} logged runs)")
    if runs:
        print(f"  first: {runs[0][:16]}   latest: {runs[-1][:16]}")
    print(f"  alerts (passed every filter): {len(alerts)}")
    if models_seen:
        top = sorted(models_seen.items(), key=lambda kv: kv[1], reverse=True)[:6]
        print("  most-seen models: " + ", ".join(f"{m} ×{c}" for m, c in top))

    # ---- best opportunities seen ----
    scored = [o for o in obs if o.get("expected_profit") is not None]
    scored.sort(key=lambda o: o["expected_profit"], reverse=True)
    if scored:
        print("\nBEST OPPORTUNITIES SEEN (by expected profit)")
        for o in scored[:5]:
            bin_s = f" · BIN £{o['bin_price']:.0f}" if o.get("bin_price") else ""
            flag = "ALERT" if o.get("is_alert") else "seen"
            print(f"  [{flag}] {o['model']}: cur £{o['current_price']:.0f} -> "
                  f"max £{o['max_bid']:.0f}, profit £{o['expected_profit']:.0f}{bin_s}")

    # ---- budget ----
    print("\nSOLD-LOOKUP BUDGET")
    if ledger:
        for month, used in sorted(ledger.items()):
            print(f"  {month}: {used}/50 used ({50 - int(used)} left)")
    else:
        print("  no lookups recorded yet")

    # ---- scatter (latest + drift) ----
    if history:
        latest = history[-1]
        rows = sorted((r for r in latest["rows"] if r.get("n")),
                      key=lambda r: r.get("score", 0), reverse=True)
        print(f"\nNICHE SCATTER (latest scan {latest['scanned_at'][:16]}, "
              f"{len(history)} scans on record)")
        print(f"  {'niche':<22}{'n':>4}{'median':>9}{'low tail':>10}{'edge%':>7}")
        for r in rows:
            print(f"  {r['query'].replace(' body',''):<22}{r['n']:>4}"
                  f"{r['median']:>9.0f}{r['min']:>10.0f}{round(r['edge_pct']*100):>6}%")

    # ---- calibration readiness ----
    resolved = [r for r in outcomes if (r.get("result") or {}).get("resold_price") is not None]
    print(f"\nCALIBRATION\n  {len(outcomes)} alert(s) logged, {len(resolved)} resolved with a "
          "resale price. Fill in data/outcomes.json results, then run: python calibrate.py")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
