import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from valbot.config import apply_sector, load_config  # noqa: E402


def test_base_config_is_neutral_default():
    # base stays as-is so the pipeline/targets test fixtures are unaffected
    cfg = load_config()
    assert cfg["fees"]["seller_type"] == "private"
    assert cfg["valuation"]["sold_to_asking_ratio"] == 0.85


def test_apply_default_sector_fixes_assumptions():
    cfg = apply_sector(load_config(), None)  # falls back to active_sector
    assert cfg["active_sector"] == "graded-cards"
    # the two corrected assumptions
    assert cfg["fees"]["seller_type"] == "business"
    assert cfg["valuation"]["sold_to_asking_ratio"] == 1.0
    assert cfg["fees"]["sell_fvf_pct"] == 0.109


def test_cameras_sector_overrides():
    cfg = apply_sector(load_config(), "cameras-lenses")
    assert cfg["active_sector"] == "cameras-lenses"
    assert cfg["fees"]["sell_fvf_pct"] == 0.069
    assert cfg["fx"]["usd_to_gbp"] == 1.0  # UK GBP only
    assert cfg["thresholds"]["price_cap"] == 250.0  # learning mode; raise once niches confirmed
    # untouched base keys survive the merge
    assert cfg["gate"]["min_comps"] == 8
    assert "Sony A6000 body" in cfg["search"]["queries"]  # tier-down niches replacing blue-chips


def test_unknown_sector_raises():
    try:
        apply_sector(load_config(), "does-not-exist")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "unknown sector" in str(e)


def test_apply_sector_does_not_mutate_base():
    base = load_config()
    apply_sector(base, "cameras-lenses")
    assert base["fees"]["seller_type"] == "private"  # base untouched
