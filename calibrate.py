#!/usr/bin/env python3
"""Read logged outcomes and report calibration numbers (read-only, suggests only).

  python calibrate.py                       # uses data/outcomes.json
  python calibrate.py --outcomes path.json

Fill in the `result` fields in data/outcomes.json as real flips resolve, then re-run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from valbot.calibrate import compute_calibration, format_calibration  # noqa: E402
from valbot.config import ROOT  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="valbot calibration (read-only)")
    p.add_argument("--outcomes", default=None, help="path to outcomes.json")
    args = p.parse_args()

    path = Path(args.outcomes) if args.outcomes else ROOT / "data" / "outcomes.json"
    records = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    print(format_calibration(compute_calibration(records)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
