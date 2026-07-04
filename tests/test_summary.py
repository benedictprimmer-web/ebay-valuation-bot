import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from valbot.summary import build_daily_summary  # noqa: E402

CFG = {
    "active_sector": "cameras-lenses",
    "thirdparty": {"sold": {"monthly_pull_budget": 50}},
}


def _now():
    # 19:00 on 4 Jul 2026, London. Use UTC tz here; the function derives the local day.
    return datetime(2026, 7, 4, 18, 0, tzinfo=timezone.utc)


def _seed(data_dir: Path, *, with_alert: bool):
    (data_dir / "cache").mkdir(parents=True, exist_ok=True)
    (data_dir / "cache" / "pull_ledger.json").write_text(json.dumps({"2026-07": 14}))
    outcomes = []
    if with_alert:
        outcomes.append({
            "logged_at": "2026-07-04T15:00:00+00:00",  # today
            "listing_id": "T1", "card": "Sony A6000",
            "current_price": 120.0,
            "prediction": {"max_bid": 160.0, "expected_profit": 35.0},
        })
    outcomes.append({  # an old alert that must NOT be counted today
        "logged_at": "2026-06-01T15:00:00+00:00",
        "listing_id": "OLD", "card": "Nikon D610", "current_price": 100.0,
        "prediction": {"max_bid": 150.0, "expected_profit": 30.0},
    })
    (data_dir / "outcomes.json").write_text(json.dumps(outcomes))
    # observations: two distinct today, one old
    lines = [
        {"ts": "2026-07-04T09:00:00+00:00", "listing_id": "T1"},
        {"ts": "2026-07-04T10:00:00+00:00", "listing_id": "T2"},
        {"ts": "2026-07-04T09:00:00+00:00", "listing_id": "T1"},  # dup same listing
        {"ts": "2026-06-30T09:00:00+00:00", "listing_id": "OLDOBS"},
    ]
    with open(data_dir / "observations.jsonl", "w") as f:
        for o in lines:
            f.write(json.dumps(o) + "\n")


def test_summary_reports_todays_alerts_and_budget(tmp_path):
    _seed(tmp_path, with_alert=True)
    msg = build_daily_summary(CFG, tmp_path, now=_now())
    assert "1 bargain alert(s) today" in msg
    assert "Sony A6000" in msg
    assert "Assessed 2 listing(s)" in msg      # T1, T2 distinct; old obs excluded
    assert "14/50 used this month" in msg
    assert "OLD" not in msg and "Nikon D610" not in msg  # yesterday's alert excluded


def test_summary_zero_found_still_sends_all_quiet(tmp_path):
    _seed(tmp_path, with_alert=False)
    msg = build_daily_summary(CFG, tmp_path, now=_now())
    assert "0 bargains found today" in msg
    assert "alive and watching" in msg
    assert "Assessed 2 listing(s)" in msg


def test_summary_handles_missing_files(tmp_path):
    # No logs at all yet -> still produces a valid zero message, no crash.
    msg = build_daily_summary(CFG, tmp_path, now=_now())
    assert "0 bargains found today" in msg
    assert "Assessed 0 listing(s)" in msg
