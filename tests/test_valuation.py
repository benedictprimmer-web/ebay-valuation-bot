import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from valbot.models import Card, Listing  # noqa: E402
from valbot.valuation import value_card, match_comps  # noqa: E402
from valbot.robust_stats import mad, iqr, percentile  # noqa: E402

VCFG = {
    "sold_to_asking_ratio": 0.85,
    "spread_method": "mad",
    "k": 1.0,
    "n_full_confidence": 15,
    "rel_dispersion_zero_conf": 0.50,
    "confidence_high": 0.66,
    "confidence_medium": 0.33,
}


def card(grade=10, grader="PSA"):
    return Card("Erling Haaland", "Topps Chrome", "base", grader, grade)


def comp(price, c=None):
    c = c or card()
    return Listing(f"id{price}", c, price, "http://x")


def test_robust_stats_basic():
    assert percentile([1, 2, 3, 4], 50) == 2.5
    assert mad([10, 10, 10]) == 0
    assert iqr([1, 2, 3, 4, 5, 6, 7, 8, 9]) == 4.0


def test_strict_match_excludes_other_grades():
    comps = [comp(90, card(10)), comp(50, card(9))]
    matched = match_comps(comps, card(10))
    assert len(matched) == 1
    assert matched[0].price == 90


def test_point_and_conservative_value():
    prices = [89, 92, 93, 94, 95, 95, 95, 96, 97, 98, 99]
    v = value_card(card(), [comp(p) for p in prices], VCFG)
    assert v is not None
    assert v.n == 11
    assert round(v.point_value, 2) == round(95 * 0.85, 2)
    # conservative is strictly below point value when there is any spread
    assert v.conservative_value < v.point_value


def test_uncertainty_pulls_conservative_down():
    tight = value_card(card(), [comp(p) for p in [94, 95, 95, 95, 96]], VCFG)
    wide = value_card(card(), [comp(p) for p in [40, 70, 95, 130, 160]], VCFG)
    # same median (95) but wider spread -> lower conservative value and lower confidence
    assert round(tight.point_value, 2) == round(wide.point_value, 2)
    assert wide.conservative_value < tight.conservative_value
    assert wide.confidence < tight.confidence


def test_more_comps_raises_confidence():
    few = value_card(card(), [comp(p) for p in [94, 95, 96]], VCFG)
    many = value_card(card(), [comp(95) for _ in range(15)] , VCFG)
    assert many.confidence > few.confidence


def test_no_comps_returns_none():
    assert value_card(card(), [], VCFG) is None
