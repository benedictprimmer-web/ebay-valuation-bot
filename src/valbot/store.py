"""State + outcome log. Committed JSON for v1 (ADR-006); migrate to Turso only if needed.

Two files:
  state/alerted.json   — listing IDs already alerted on, so the bot doesn't repeat.
  outcomes.json        — every alert logged with its prediction. Fill in the real
                         result later (won/lost, final price, eventual resale) to
                         calibrate the sold-to-asking ratio and tune the floors.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Assessment


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.state_dir = self.data_dir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.alerted_path = self.state_dir / "alerted.json"
        self.outcomes_path = self.data_dir / "outcomes.json"
        self._alerted = self._load_alerted()

    def _load_alerted(self) -> set[str]:
        if self.alerted_path.exists():
            with open(self.alerted_path, "r", encoding="utf-8") as f:
                return set(json.load(f))
        return set()

    def already_alerted(self, listing_id: str) -> bool:
        return listing_id in self._alerted

    def mark_alerted(self, listing_id: str) -> None:
        self._alerted.add(listing_id)
        with open(self.alerted_path, "w", encoding="utf-8") as f:
            json.dump(sorted(self._alerted), f, indent=2)

    def log_observations(self, assessments: list[Assessment]) -> int:
        """Append EVERY assessment (alert or skip) to observations.jsonl — the full
        deal-flow record, one JSON object per line. This is the dataset that grows over
        time: what was on offer, what we valued it at, and whether/why it passed. Feeds
        later analysis and calibration. Append-only (JSONL) so it scales without rewrites.
        Returns how many rows were written."""
        if not assessments:
            return 0
        path = self.data_dir / "observations.jsonl"
        ts = _utcnow()
        with open(path, "a", encoding="utf-8") as f:
            for a in assessments:
                v = a.valuation
                f.write(json.dumps({
                    "ts": ts,
                    "listing_id": a.listing.listing_id,
                    "model": v.card.label() if v else a.listing.card.label(),
                    "current_price": a.listing.price,
                    "bin_price": a.listing.bin_price,
                    "condition": a.listing.condition,
                    "shutter_count": a.listing.shutter_count,
                    "seller_feedback_pct": a.listing.seller_feedback_pct,
                    "postage_in": a.listing.postage_in,
                    "ends_at": a.listing.ends_at,
                    "url": a.listing.url,
                    "point_value": round(v.point_value, 2) if v else None,
                    "conservative_value": round(v.conservative_value, 2) if v else None,
                    "n_comps": v.n if v else 0,
                    "confidence": v.confidence if v else None,
                    "rel_dispersion": round(v.rel_dispersion, 4) if v else None,
                    "max_bid": a.max_bid,
                    "expected_profit": a.expected_profit,
                    "margin": a.margin,
                    "is_alert": a.is_alert,
                    "passed_gate": a.passed_gate,
                    "passed_floors": a.passed_floors,
                    "reasons": a.reasons,
                }) + "\n")
        return len(assessments)

    def log_alert(self, a: Assessment) -> None:
        """Append the prediction. Result fields are null until Ben fills them in."""
        record = {
            "logged_at": _utcnow(),
            "listing_id": a.listing.listing_id,
            "url": a.listing.url,
            "card": a.valuation.card.label() if a.valuation else None,
            "current_price": a.listing.price,
            "ends_at": a.listing.ends_at,
            "prediction": {
                "max_bid": a.max_bid,
                "point_value": round(a.valuation.point_value, 2)
                if a.valuation
                else None,
                "conservative_value": round(a.valuation.conservative_value, 2)
                if a.valuation
                else None,
                "expected_profit": a.expected_profit,
                "margin": a.margin,
                "confidence": a.valuation.confidence if a.valuation else None,
                "n_comps": a.valuation.n if a.valuation else None,
                "rel_dispersion": round(a.valuation.rel_dispersion, 4)
                if a.valuation
                else None,
                "ratio_used": a.valuation.ratio if a.valuation else None,
            },
            "fees": a.fee_breakdown,
            "result": {  # fill in later for calibration
                "won": None,
                "final_price": None,
                "resold_price": None,
                "realised_profit": None,
                "notes": None,
            },
        }
        existing = []
        if self.outcomes_path.exists():
            with open(self.outcomes_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        existing.append(record)
        with open(self.outcomes_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
