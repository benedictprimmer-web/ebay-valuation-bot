"""Option 3 — semi-manual targets mode.

No live auction feed needed. You hand the bot a short watch list of cards (CSV or
JSON); it values each against real Card API sold comps and tells you the most you
should pay, the margin, the confidence, and how many comps backed the number.

Use it on an auction you're already watching: drop in the card plus the price it's
sitting at, and it says BID (with headroom) or SKIP (with why). Leave the price out
and it just hands back the max bid to compare by eye.

Same valuation, gate, fee and threshold code as the live pipeline — this only swaps
the input (your list) for the poll. Read-only. Nothing here places a bid.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from .ebay_client import ListingSource
from .models import Assessment, Card, Listing
from .threshold import assess
from .valuation import value_card

# accepted CSV / JSON aliases -> canonical field
_ALIASES = {
    "player": "player",
    "set": "set_name",
    "set_name": "set_name",
    "setname": "set_name",
    "variant": "variant",
    "parallel": "variant",
    "grader": "grader",
    "grade": "grade",
    "current_price": "current_price",
    "current": "current_price",
    "price": "current_price",
    "current_bid": "current_price",
}


@dataclass
class TargetInput:
    card: Card
    current_price: float | None  # the live auction price you're watching, if any
    label: str                   # how it read in the watch list (for reporting)


@dataclass
class TargetResult:
    target: TargetInput
    assessment: Assessment

    @property
    def has_price(self) -> bool:
        return self.target.current_price is not None


# --------------------------------------------------------------------- load


def _norm_row(raw: dict) -> dict:
    """Map a watch-list row's keys onto canonical field names."""
    out: dict = {}
    for k, v in raw.items():
        if k is None:
            continue
        key = _ALIASES.get(str(k).strip().lower())
        if key:
            out[key] = v
    return out


def _card_from_row(row: dict) -> tuple[Card, float | None, str]:
    player = str(row["player"]).strip()
    set_name = str(row.get("set_name", "")).strip()
    variant = str(row.get("variant") or "base").strip() or "base"
    grader = str(row["grader"]).strip().upper()
    grade = float(row["grade"])
    raw_price = row.get("current_price")
    price: float | None
    if raw_price is None or str(raw_price).strip() == "":
        price = None
    else:
        price = float(raw_price)
    card = Card(player=player, set_name=set_name, variant=variant, grader=grader, grade=grade)
    return card, price, card.label()


def load_watchlist(path: str | Path) -> list[TargetInput]:
    """Read a watch list from CSV or JSON. Fields: player, set_name, variant,
    grader, grade, current_price (optional). variant defaults to 'base'."""
    p = Path(path)
    rows: list[dict]
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        rows = data["cards"] if isinstance(data, dict) else data
    elif p.suffix.lower() in (".csv", ".tsv"):
        delim = "\t" if p.suffix.lower() == ".tsv" else ","
        with open(p, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f, delimiter=delim))
    else:
        raise ValueError(f"watch list must be .csv, .tsv or .json, got {p.suffix!r}")

    out: list[TargetInput] = []
    for i, raw in enumerate(rows, start=1):
        row = _norm_row(raw)
        missing = [f for f in ("player", "grader", "grade") if not str(row.get(f, "")).strip()]
        if missing:
            raise ValueError(f"watch-list row {i} missing required field(s): {', '.join(missing)}")
        card, price, label = _card_from_row(row)
        out.append(TargetInput(card=card, current_price=price, label=label))
    return out


# ---------------------------------------------------------------------- run


def assess_target(target: TargetInput, source: ListingSource, cfg: dict) -> TargetResult:
    """Value one watched card against sold comps and run it through the same
    gate/fee/threshold logic as the live pipeline."""
    comps = source.fetch_comps(target.card)
    valuation = value_card(target.card, comps, cfg["valuation"])
    # No live price -> price 0.0 so max_bid/confidence still compute; the verdict
    # and formatter ignore price-dependent fields when current_price is None.
    price = target.current_price if target.current_price is not None else 0.0
    listing = Listing(
        listing_id=target.card.key(),
        card=target.card,
        price=price,
        url="",
        is_auction=True,
    )
    assessment = assess(listing, valuation, cfg)
    return TargetResult(target=target, assessment=assessment)


def run_targets(cfg: dict, source: ListingSource, watchlist: list[TargetInput]) -> list[TargetResult]:
    return [assess_target(t, source, cfg) for t in watchlist]


# ------------------------------------------------------------------- verdict


def verdict(r: TargetResult) -> str:
    """Short call for one card. Drives both the console line and the JSON field."""
    a = r.assessment
    if a.valuation is None:
        return "NO DATA — no comps found"
    if not a.passed_gate:
        # only the gate reasons (comp count / spread), not the downstream floor noise
        gate_reasons = [r for r in a.reasons if "comps" in r]
        return "LOW CONFIDENCE — " + "; ".join(gate_reasons or a.reasons)
    if a.max_bid is None:
        return "NO BID — not profitable after fees"
    if not r.has_price:
        return f"MAX BID £{a.max_bid:.2f}"
    if a.passed_floors:
        return f"BID — up to £{a.max_bid:.2f} (headroom £{a.headroom:.2f})"
    return "SKIP — " + "; ".join(a.reasons)
