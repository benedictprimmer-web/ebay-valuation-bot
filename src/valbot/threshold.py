"""Gate -> fees -> floors -> the max bid. Builds an Assessment per target auction.

Money decisions use conservative_value, never point_value. The max bid is the most
Ben should pay; the alert fires only if the current price sits at or under it AND the
confidence gate passes.
"""

from __future__ import annotations

from .fees import sell_fees, buyer_protection_fee, profit, solve_max_bid
from .models import Assessment, Listing, Valuation


def passes_gate(v: Valuation, cfg: dict) -> tuple[bool, list[str]]:
    """Confidence gate (ADR-008): enough comps AND tight enough spread."""
    reasons: list[str] = []
    ok = True
    if v.n < cfg["gate"]["min_comps"]:
        ok = False
        reasons.append(f"thin comps (n={v.n} < {cfg['gate']['min_comps']})")
    if v.rel_dispersion > cfg["gate"]["max_rel_dispersion"]:
        ok = False
        reasons.append(
            f"scattered comps (rel spread {v.rel_dispersion:.2f} "
            f"> {cfg['gate']['max_rel_dispersion']})"
        )
    return ok, reasons


def assess(listing: Listing, valuation: Valuation | None, cfg: dict) -> Assessment:
    fee_cfg = cfg["fees"]
    th = cfg["thresholds"]

    if valuation is None:
        return Assessment(
            listing=listing,
            valuation=None,
            max_bid=None,
            expected_profit=None,
            margin=None,
            headroom=None,
            passed_gate=False,
            passed_floors=False,
            reasons=["no comps"],
        )

    gate_ok, gate_reasons = passes_gate(valuation, cfg)

    sale_price = valuation.conservative_value
    required_profit = max(th["margin_floor"] * sale_price, th["profit_floor"])
    # Use the listing's real inbound postage when known (Browse), else the flat estimate.
    postage_in = listing.postage_in if listing.postage_in is not None else fee_cfg["postage_in"]
    max_bid_raw = solve_max_bid(sale_price, required_profit, fee_cfg, postage_in=postage_in)
    # Price cap is a separate risk control (ADR-004) — clamps the bid, not the ranking.
    max_bid = min(max_bid_raw, th["price_cap"]) if max_bid_raw > 0 else None

    current = listing.price
    expected_profit = profit(current, sale_price, fee_cfg, postage_in=postage_in)
    margin = expected_profit / sale_price if sale_price > 0 else 0.0
    headroom = (max_bid - current) if max_bid is not None else None

    reasons = list(gate_reasons)
    floors_ok = True
    if max_bid is None:
        floors_ok = False
        reasons.append("no profitable bid after fees")
    else:
        if current > max_bid:
            floors_ok = False
            reasons.append(
                f"current £{current:.2f} above max bid £{max_bid:.2f}"
            )
        if current > th["price_cap"]:
            floors_ok = False
            reasons.append(f"over price cap (£{current:.2f} > £{th['price_cap']})")
        if expected_profit < th["profit_floor"]:
            floors_ok = False
            reasons.append(f"under profit floor (£{expected_profit:.2f})")
        if margin < th["margin_floor"]:
            floors_ok = False
            reasons.append(f"under margin floor ({margin:.0%})")

    # Quality floor: a STATED shutter count near end-of-life makes a body too worn to
    # auto-recommend (its comps are mixed-condition, so it isn't really a bargain). Only
    # fires when the count is known — unknown (the common case) never penalises.
    q = cfg.get("quality", {})
    sc = getattr(listing, "shutter_count", None)
    rating = q.get("shutter_rating_default")
    frac = q.get("shutter_max_fraction")
    if sc is not None and rating and frac and sc > float(frac) * float(rating):
        floors_ok = False
        reasons.append(
            f"high shutter count ({sc:,} > {int(float(frac) * 100)}% of ~{int(rating):,})"
        )

    sf = sell_fees(sale_price, fee_cfg)
    fee_breakdown = {
        **sf,
        "buyer_protection": round(buyer_protection_fee(current, fee_cfg), 2),
        "postage_in": round(postage_in, 2),
        "postage_out": fee_cfg["postage_out"],
        "required_profit": round(required_profit, 2),
    }

    return Assessment(
        listing=listing,
        valuation=valuation,
        max_bid=round(max_bid, 2) if max_bid is not None else None,
        expected_profit=round(expected_profit, 2),
        margin=round(margin, 4),
        headroom=round(headroom, 2) if headroom is not None else None,
        fee_breakdown=fee_breakdown,
        passed_gate=gate_ok,
        passed_floors=floors_ok,
        reasons=reasons,
    )
