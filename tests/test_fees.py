import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from valbot.fees import (  # noqa: E402
    sell_fees,
    buyer_protection_fee,
    profit,
    solve_max_bid,
)

FCFG = {
    "seller_type": "business",
    "sell_fvf_pct": 0.128,
    "sell_fixed": 0.40,
    "sell_regulatory_pct": 0.0035,
    "vat_on_fees_pct": 0.20,
    "apply_buyer_protection": True,
    "buyer_protection_tiers": [[20, 0.07], [300, 0.04], [4000, 0.02]],
    "buyer_protection_fixed": 0.10,
    "postage_in": 3.50,
    "postage_out": 3.50,
}


def test_sell_fees_itemised():
    f = sell_fees(100.0, FCFG)
    assert round(f["sell_fvf"], 2) == round(100 * 0.128 + 0.40, 2)
    assert round(f["sell_regulatory"], 2) == 0.35
    # VAT applies on top of fvf + regulatory
    assert round(f["sell_vat_on_fees"], 2) == round((f["sell_fvf"] + 0.35) * 0.20, 2)


def test_private_seller_has_zero_sell_fees():
    cfg = {**FCFG, "seller_type": "private"}
    f = sell_fees(100.0, cfg)
    assert f["sell_total"] == 0.0
    # private seller can bid more than a business seller for the same card
    assert solve_max_bid(100.0, 25.0, cfg) > solve_max_bid(100.0, 25.0, FCFG)


def test_buyer_protection_tiers():
    # £10 fully in first tier: 0.10 + 0.07*10 = 0.80
    assert round(buyer_protection_fee(10, FCFG), 2) == 0.80
    # £50: 0.10 + 0.07*20 + 0.04*30 = 0.10 + 1.40 + 1.20 = 2.70
    assert round(buyer_protection_fee(50, FCFG), 2) == 2.70


def test_buyer_protection_can_be_disabled():
    cfg = {**FCFG, "apply_buyer_protection": False}
    assert buyer_protection_fee(50, cfg) == 0.0


def test_profit_monotonic_decreasing():
    assert profit(10, 100, FCFG) > profit(40, 100, FCFG)


def test_solve_max_bid_hits_required_profit():
    sale = 100.0
    required = 25.0
    mb = solve_max_bid(sale, required, FCFG)
    # at the solved bid, realised profit should equal the requirement
    assert abs(profit(mb, sale, FCFG) - required) < 0.05
    # bidding £1 more should drop profit below the requirement
    assert profit(mb + 1, sale, FCFG) < required


def test_solve_returns_zero_when_impossible():
    # tiny sale price can't clear a £15 profit after fees + postage
    assert solve_max_bid(15.0, 15.0, FCFG) == 0.0


def test_postage_in_override_beats_flat_estimate():
    # A listing with pricey real postage nets less profit and a lower max bid than the
    # flat £3.50 estimate; free postage (0.0) does better.
    base = profit(40, 100, FCFG)                       # flat 3.50
    dear = profit(40, 100, FCFG, postage_in=9.99)      # real, expensive
    free = profit(40, 100, FCFG, postage_in=0.0)       # free postage
    assert dear < base < free
    assert round(base - dear, 2) == round(9.99 - 3.50, 2)
    # the max bid tracks the same way
    assert solve_max_bid(100, 25, FCFG, postage_in=9.99) < solve_max_bid(100, 25, FCFG)
