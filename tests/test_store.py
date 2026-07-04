import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from valbot.models import ref_code  # noqa: E402
from valbot.store import Store  # noqa: E402


def test_ref_code_stable_and_short():
    assert ref_code("v1|307035031904|0") == ref_code("v1|307035031904|0")
    assert len(ref_code("anything")) == 6
    assert ref_code("A") != ref_code("B")


def _seed_outcome(tmp_path, listing_id="L1"):
    rec = {
        "listing_id": listing_id,
        "ref": ref_code(listing_id),
        "card": "Sony A6000",
        "prediction": {"point_value": 200.0},
        "human_verdict": {"verdict": None, "fair_value": None, "reason": None, "at": None},
        "result": {"resold_price": None},
    }
    (tmp_path / "outcomes.json").write_text(json.dumps([rec]))
    return rec


def test_record_verdict_by_ref_and_by_listing_id(tmp_path):
    rec = _seed_outcome(tmp_path)
    store = Store(tmp_path)

    # by ref code, with a fair value + reason
    m = store.record_verdict(rec["ref"], "bad", reason="scuffed", fair_value=150.0)
    assert m is not None
    saved = json.loads((tmp_path / "outcomes.json").read_text())[0]["human_verdict"]
    assert saved["verdict"] == "bad" and saved["fair_value"] == 150.0
    assert saved["reason"] == "scuffed" and saved["at"] is not None

    # by listing id, and thumbs normalisation (👍 -> good)
    assert store.record_verdict("L1", "👍") is not None
    assert json.loads((tmp_path / "outcomes.json").read_text())[0]["human_verdict"]["verdict"] == "good"


def test_record_verdict_unknown_token_returns_none(tmp_path):
    _seed_outcome(tmp_path)
    store = Store(tmp_path)
    assert store.record_verdict("nope99", "good") is None


def test_record_verdict_rejects_bad_verdict(tmp_path):
    _seed_outcome(tmp_path)
    store = Store(tmp_path)
    with pytest.raises(ValueError):
        store.record_verdict("L1", "maybe")
