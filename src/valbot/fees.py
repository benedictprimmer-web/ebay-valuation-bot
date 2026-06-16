"""All-in conservative fee model (ADR-005).

Itemised, not a flat haircut, so you can see which cost eats the margin and swap one
rate when eBay moves it. Two sides:
  - Sell side: Ben resells as a UK business seller -> FVF + fixed + regulatory + VAT.
  - Buy side: buyer-protection fee on the purchase, tiered. Assumed (conservative).
Postage both ways. Private-seller £0 sell fees are upside, never assumed.
"""

from __future__ import annotations


def sell_fees(sale_price: float, cfg: dict) -> dict[str, float]:
    """eBay costs Ben pays when he resells at `sale_price`.

    seller_type 'private' = £0 final value fees (UK, since Oct 2024). That's Ben's
    real account today, so it's the default. 'business' applies the full 12.8% + fixed
    + regulatory + VAT — switch to it if eBay/HMRC reclassify the account once resale
    volume looks like trading.
    """
    if cfg.get("seller_type", "private") == "private":
        return {
            "sell_fvf": 0.0,
            "sell_regulatory": 0.0,
            "sell_vat_on_fees": 0.0,
            "sell_total": 0.0,
        }
    fvf = sale_price * cfg["sell_fvf_pct"] + cfg["sell_fixed"]
    regulatory = sale_price * cfg["sell_regulatory_pct"]
    ebay_fees = fvf + regulatory
    vat = ebay_fees * cfg["vat_on_fees_pct"]
    total = ebay_fees + vat
    return {
        "sell_fvf": round(fvf, 2),
        "sell_regulatory": round(regulatory, 2),
        "sell_vat_on_fees": round(vat, 2),
        "sell_total": round(total, 2),
    }


def buyer_protection_fee(buy_price: float, cfg: dict) -> float:
    """Tiered UK buyer-protection fee on the purchase price."""
    if not cfg.get("apply_buyer_protection", True):
        return 0.0
    tiers = cfg["buyer_protection_tiers"]
    fee = cfg["buyer_protection_fixed"]
    lower = 0.0
    for upper, rate in tiers:
        if buy_price <= lower:
            break
        band = min(buy_price, upper) - lower
        fee += band * rate
        lower = upper
    if buy_price > lower:  # above the top tier bound, apply the last rate onward
        fee += (buy_price - lower) * tiers[-1][1]
    return fee


def profit(buy_price: float, sale_price: float, cfg: dict) -> float:
    """Net £ profit on a flip: resale minus the buy, all costs both sides."""
    sf = sell_fees(sale_price, cfg)["sell_total"]
    bpf = buyer_protection_fee(buy_price, cfg)
    return (
        sale_price
        - buy_price
        - sf
        - bpf
        - cfg["postage_in"]
        - cfg["postage_out"]
    )


def solve_max_bid(sale_price: float, required_profit: float, cfg: dict) -> float:
    """Highest buy price where profit still equals required_profit.

    profit() is monotonically decreasing in buy_price (buyer-protection adds to the
    buy), so bisect. Returns 0.0 if no buy price clears the required profit.
    """
    if profit(0.0, sale_price, cfg) < required_profit:
        return 0.0
    lo, hi = 0.0, sale_price
    for _ in range(60):  # ~1e-18 resolution, plenty
        mid = (lo + hi) / 2
        if profit(mid, sale_price, cfg) >= required_profit:
            lo = mid
        else:
            hi = mid
    return lo
