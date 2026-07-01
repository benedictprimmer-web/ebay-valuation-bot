import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from valbot.config import load_config, ROOT  # noqa: E402
from valbot.ebay_client import MockSource  # noqa: E402
from valbot.pipeline import run_pipeline  # noqa: E402
from valbot.store import Store  # noqa: E402


class CapturingAlerter:
    def __init__(self):
        self.messages = []

    def send(self, text):
        self.messages.append(text)
        return True


def build():
    cfg = load_config()
    source = MockSource(ROOT / "data" / "mock_listings.json")
    alerter = CapturingAlerter()
    tmp = tempfile.mkdtemp()
    store = Store(tmp)
    return cfg, source, alerter, store


def test_pipeline_fires_expected_alerts():
    cfg, source, alerter, store = build()
    result = run_pipeline(cfg, source, alerter, store)
    alert_ids = {a.listing.listing_id for a in result.alerts}
    # A and F alert; B (thin), C (scattered), D (over cap/floor), E (no comps) skip.
    assert alert_ids == {"A1", "F1"}
    assert result.sent == 2


def test_alerts_ranked_by_expected_profit():
    cfg, source, alerter, store = build()
    result = run_pipeline(cfg, source, alerter, store)
    profits = [a.expected_profit for a in result.alerts]
    assert profits == sorted(profits, reverse=True)
    assert result.alerts[0].listing.listing_id == "A1"


def test_skips_have_reasons():
    cfg, source, alerter, store = build()
    result = run_pipeline(cfg, source, alerter, store)
    by_id = {a.listing.listing_id: a for a in result.assessments}
    assert "thin comps" in " ".join(by_id["B1"].reasons)
    assert "scattered" in " ".join(by_id["C1"].reasons)
    assert by_id["E1"].reasons == ["no comps"]
    assert not by_id["D1"].is_alert


def test_dedupe_prevents_repeat_alerts():
    cfg, source, alerter, store = build()
    run_pipeline(cfg, source, alerter, store)
    second = run_pipeline(cfg, source, alerter, store)
    assert second.sent == 0  # already alerted, deduped


def test_observations_log_captures_every_assessment():
    cfg, source, alerter, store = build()
    result = run_pipeline(cfg, source, alerter, store)
    n = store.log_observations(result.assessments)
    assert n == len(result.assessments) >= 6  # alerts AND skips, not just the 2 alerts
    import json

    path = store.data_dir / "observations.jsonl"
    lines = path.read_text().strip().splitlines()
    assert len(lines) == n
    rows = [json.loads(line) for line in lines]
    # both an alert and a skip are present, with their decision recorded
    assert any(r["is_alert"] for r in rows)
    assert any(not r["is_alert"] for r in rows)
    assert all("model" in r and "current_price" in r and "reasons" in r for r in rows)
    # appends, not overwrites
    store.log_observations(result.assessments)
    assert len(path.read_text().strip().splitlines()) == 2 * n


def test_outcome_log_written():
    cfg, source, alerter, store = build()
    run_pipeline(cfg, source, alerter, store)
    assert store.outcomes_path.exists()
    import json

    records = json.loads(store.outcomes_path.read_text())
    assert len(records) == 2
    assert records[0]["prediction"]["max_bid"] is not None
    assert records[0]["result"]["won"] is None
