import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from valbot.calibrate import (  # noqa: E402
    compute_calibration,
    compute_human_feedback,
    format_calibration,
)


def rec(point_value, ratio_used, conservative_value, resold, won=True,
        expected_profit=None, realised_profit=None):
    return {
        "prediction": {
            "point_value": point_value,
            "ratio_used": ratio_used,
            "conservative_value": conservative_value,
            "expected_profit": expected_profit,
        },
        "result": {
            "won": won,
            "resold_price": resold,
            "realised_profit": realised_profit,
        },
    }


def test_empty_is_graceful():
    s = compute_calibration([])
    assert s["status"] == "no resolved outcomes yet"
    assert "fill" in format_calibration(s).lower()


def test_unresolved_records_dont_calibrate():
    # logged but no resold_price -> not usable yet
    r = rec(100, 0.85, 90, resold=None)
    s = compute_calibration([r])
    assert s["resolved_for_calibration"] == 0
    assert s.get("status") == "no resolved outcomes yet"


def test_suggested_ratio_from_realized():
    # point_value=85 at ratio 0.85 -> implied comp median 100. Resold 100 -> realized ratio 1.0
    recs = [
        rec(85, 0.85, 80, resold=100),
        rec(85, 0.85, 80, resold=95),  # realized 0.95
        rec(85, 0.85, 80, resold=100),  # realized 1.0
    ]
    s = compute_calibration(recs)
    assert s["resolved_for_calibration"] == 3
    assert s["suggested_sold_ratio"] == 1.0  # median of [1.0, 0.95, 1.0]
    assert s["conservative_coverage"] == 1.0  # all resold >= 80


def test_profit_bias_reported():
    recs = [rec(85, 1.0, 80, resold=100, expected_profit=20, realised_profit=25)]
    s = compute_calibration(recs)
    assert s["profit_bias"] == 5.0  # under-promised by £5
    assert "under-promised" in format_calibration(s)


def _verdict_rec(card, verdict, point_value=200.0, fair_value=None):
    return {
        "card": card,
        "prediction": {"point_value": point_value},
        "human_verdict": {"verdict": verdict, "fair_value": fair_value, "reason": None},
        "result": {"resold_price": None},
    }


def test_human_feedback_counts_and_worst_niches():
    recs = [
        _verdict_rec("Sony A6000", "bad"),
        _verdict_rec("Sony A6000", "bad"),
        _verdict_rec("Sony A6000", "good"),
        _verdict_rec("Nikon D610", "good"),
    ]
    h = compute_human_feedback(recs)
    assert h["labeled"] == 4 and h["good"] == 2 and h["bad"] == 2
    worst = h["worst_niches"][0]
    assert worst["model"] == "Sony A6000" and worst["bad"] == 2

    # human section renders even with no resolved flips
    out = format_calibration(compute_calibration(recs))
    assert "Human verdicts:" in out and "Sony A6000" in out


def test_human_fair_value_flags_overvaluation():
    # you think it's worth £150 vs our £200 point value -> ratio 0.75 -> we OVER-value
    recs = [_verdict_rec("Sony A6000", "bad", point_value=200.0, fair_value=150.0)]
    h = compute_human_feedback(recs)
    n = h["value_nudges"][0]
    assert n["model"] == "Sony A6000" and n["your_fair_vs_our_value"] == 0.75
    assert "OVER-valuing" in format_calibration(compute_calibration(recs))


def test_no_verdicts_is_graceful():
    h = compute_human_feedback([{"card": "x", "result": {"resold_price": None}}])
    assert h == {"labeled": 0, "good": 0, "bad": 0}
    assert "none yet" in format_calibration(compute_calibration([]))
