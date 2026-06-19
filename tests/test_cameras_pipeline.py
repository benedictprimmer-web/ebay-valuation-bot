"""Cameras lane, end to end. Proves exact-model identity drives the same pipeline the
cards lane uses: source -> match comps by model -> value -> gate -> threshold -> alert.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from valbot.camera import parse_camera  # noqa: E402
from valbot.config import ROOT, apply_sector, load_config  # noqa: E402
from valbot.ebay_client import MockSource, get_source  # noqa: E402
from valbot.pipeline import run_pipeline  # noqa: E402
from valbot.store import Store  # noqa: E402
from valbot.targets import load_watchlist, run_targets  # noqa: E402

FIXTURE = ROOT / "data" / "mock_cameras.json"


def cam_cfg():
    return apply_sector(load_config(), "cameras-lenses")


class _NullAlerter:
    def __init__(self):
        self.sent = []

    def send(self, msg):
        self.sent.append(msg)


class _NullStore:
    def already_alerted(self, _):
        return False

    def log_alert(self, _):
        pass

    def mark_alerted(self, _):
        pass


def test_sector_switches_identity_to_camera():
    assert cam_cfg().get("identity") == "camera"


def test_source_drops_unresolved_targets():
    """The junk-lot target can't resolve to a model -> never reaches valuation."""
    src = MockSource(FIXTURE)
    titles = {t.card.label() for t in src.fetch_targets()}
    assert not any("job lot" in t.lower() for t in titles)
    # 5 fixture targets, 1 is junk -> 4 resolved
    assert len(src.fetch_targets()) == 4


def test_comps_match_by_exact_model():
    src = MockSource(FIXTURE)
    a7 = parse_camera("Sony A7 III body")
    comps = src.fetch_comps(a7)
    assert len(comps) == 10  # all 10 A7 III spellings cluster
    # a different model must not leak in
    assert all(c.card.key() == a7.key() for c in comps)
    r6 = parse_camera("Canon EOS R6 body")
    assert src.fetch_comps(r6) and all(
        c.card.key() == r6.key() for c in src.fetch_comps(r6)
    )
    # R6 and R6 Mark II are different identities
    assert parse_camera("Canon EOS R6").key() != parse_camera("Canon EOS R6 Mark II").key()


def test_pipeline_alerts_underpriced_skips_thin_and_scattered():
    cfg = cam_cfg()
    src = get_source(cfg, "mock", mock_path=FIXTURE)
    result = run_pipeline(cfg, src, _NullAlerter(), _NullStore())

    alerted = {a.listing.listing_id for a in result.alerts}
    # CAM-A7 (£360) exceeds price_cap=250 → correctly blocked in learning mode
    assert "CAM-A7" not in alerted
    assert "CAM-RF50" in alerted    # value ~£150, current £70 — under cap, strong spread

    by_id = {a.listing.listing_id: a for a in result.assessments}
    # thin comps (4 < 8) -> gate fails, no alert
    assert not by_id["CAM-R6"].passed_gate
    assert "CAM-R6" not in alerted
    # XT4 sits at fair value -> passes the gate but no profitable bid after fees
    assert by_id["CAM-XT4"].passed_gate
    assert "CAM-XT4" not in alerted
    # the junk-lot target never made it to assessment at all
    assert "CAM-JUNK" not in by_id


def test_camera_watchlist_loads_and_resolves(tmp_path):
    wl = tmp_path / "cams.csv"
    wl.write_text("title,current_price\nSony A7 III body,450\nCanon RF 50mm f1.8 STM,\n")
    items = load_watchlist(wl, identity="camera")
    assert items[0].card.key() == parse_camera("Sony A7 III").key()
    assert items[0].current_price == 450.0
    assert items[1].current_price is None


def test_camera_watchlist_rejects_ambiguous_title(tmp_path):
    wl = tmp_path / "bad.csv"
    wl.write_text("title\njob lot of cameras untested\n")
    with pytest.raises(ValueError):
        load_watchlist(wl, identity="camera")


def test_targets_mode_values_camera_against_comps():
    cfg = cam_cfg()
    src = get_source(cfg, "mock", mock_path=FIXTURE)
    a7 = parse_camera("Sony A7 III body")
    from valbot.targets import TargetInput

    results = run_targets(cfg, src, [TargetInput(card=a7, current_price=450.0, label=a7.label())])
    a = results[0].assessment
    assert a.passed_gate and a.valuation.n == 10
    assert a.max_bid is not None
