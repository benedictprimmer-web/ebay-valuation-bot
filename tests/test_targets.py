import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from valbot.config import ROOT, load_config  # noqa: E402
from valbot.ebay_client import MockSource  # noqa: E402
from valbot.formatting import format_targets, target_to_dict  # noqa: E402
from valbot.targets import (  # noqa: E402
    TargetInput,
    load_watchlist,
    run_targets,
    verdict,
)
from valbot.models import Card  # noqa: E402


def build_source():
    return MockSource(ROOT / "data" / "mock_listings.json")


def write_csv(rows: str) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
    f.write(rows)
    f.close()
    return f.name


def test_load_watchlist_csv_aliases_and_defaults():
    path = write_csv(
        "player,set,grader,grade,price\n"
        "Erling Haaland,Topps Chrome,psa,10,22\n"
    )
    wl = load_watchlist(path)
    assert len(wl) == 1
    t = wl[0]
    assert t.card.grader == "PSA"  # upper-cased
    assert t.card.variant == "base"  # defaulted
    assert t.card.set_name == "Topps Chrome"  # "set" alias mapped
    assert t.current_price == 22.0  # "price" alias mapped


def test_load_watchlist_blank_price_is_none():
    path = write_csv(
        "player,set_name,variant,grader,grade,current_price\n"
        "Erling Haaland,Topps Chrome,base,PSA,10,\n"
    )
    wl = load_watchlist(path)
    assert wl[0].current_price is None


def test_load_watchlist_missing_required_field_raises():
    path = write_csv("player,set_name,grade\nFoo,Bar,10\n")  # no grader
    try:
        load_watchlist(path)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "grader" in str(e)


def test_load_watchlist_json():
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(
        {"cards": [{"player": "Jude Bellingham", "set_name": "Prizm",
                    "grader": "PSA", "grade": 9, "current_price": 18}]},
        f,
    )
    f.close()
    wl = load_watchlist(f.name)
    assert wl[0].card.player == "Jude Bellingham"
    assert wl[0].current_price == 18.0


def card(player, set_name, variant, grader, grade):
    return Card(player=player, set_name=set_name, variant=variant, grader=grader, grade=grade)


def test_bid_verdict_when_under_max_bid():
    cfg = load_config()
    t = TargetInput(card("Erling Haaland", "Topps Chrome", "base", "PSA", 10), 22.0,
                    "Erling Haaland — Topps Chrome base PSA 10")
    [r] = run_targets(cfg, build_source(), [t])
    assert r.assessment.valuation is not None
    assert r.assessment.passed_gate
    assert r.assessment.max_bid is not None
    assert r.assessment.max_bid >= 22.0
    assert verdict(r).startswith("BID")


def test_no_price_reports_max_bid_only():
    cfg = load_config()
    t = TargetInput(card("Erling Haaland", "Topps Chrome", "base", "PSA", 10), None,
                    "Erling Haaland — Topps Chrome base PSA 10")
    [r] = run_targets(cfg, build_source(), [t])
    assert not r.has_price
    assert verdict(r).startswith("MAX BID")
    d = target_to_dict(r)
    # price-dependent fields suppressed when no current price
    assert d["margin"] is None
    assert d["headroom"] is None
    assert d["max_bid"] is not None
    assert d["comp_count"] >= 8


def test_thin_comps_low_confidence():
    cfg = load_config()
    # Vinicius Select BGS 9.5 has too few comps in the fixture (B = thin).
    t = TargetInput(card("Vinicius Junior", "Select", "base", "BGS", 9.5), 20.0, "Vini")
    [r] = run_targets(cfg, build_source(), [t])
    assert not r.assessment.passed_gate
    assert "LOW CONFIDENCE" in verdict(r)


def test_no_comps_is_no_data():
    cfg = load_config()
    t = TargetInput(card("Jamal Musiala", "Optic", "base", "SGC", 10), 25.0, "Musiala")
    [r] = run_targets(cfg, build_source(), [t])
    assert r.assessment.valuation is None
    assert verdict(r).startswith("NO DATA")


def test_over_price_cap_skips():
    cfg = load_config()
    # Phil Foden Prizm silver PSA 10 at £60 is over the £50 cap (D).
    t = TargetInput(card("Phil Foden", "Prizm", "silver", "PSA", 10), 60.0, "Foden")
    [r] = run_targets(cfg, build_source(), [t])
    assert r.has_price
    assert not r.assessment.passed_floors
    assert verdict(r).startswith("SKIP")


def test_format_targets_runs():
    cfg = load_config()
    wl = load_watchlist(ROOT / "data" / "watchlist.example.csv")
    results = run_targets(cfg, build_source(), wl)
    text = format_targets(results)
    assert "watched card" in text
    assert "BID" in text
