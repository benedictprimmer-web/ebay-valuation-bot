import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from valbot.cache import BudgetExceeded, SoldFeedCache  # noqa: E402
from valbot.config import apply_sector, load_config  # noqa: E402
from valbot.ebay_client import ThirdPartySource  # noqa: E402


class _Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


T0 = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def _sold_response():
    return {"products": [
        {"title": "Sony A6000 body", "sale_price": 150.0, "item_id": "p1", "link": "u1"},
        {"title": "Sony A6000 body only", "sale_price": 95.0, "item_id": "p2", "link": "u2"},
    ]}


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_cache_hit_within_ttl_and_miss_when_stale(tmp_path):
    clock = _Clock(T0)
    cache = SoldFeedCache(tmp_path, now=clock)
    cache.put("url", "Sony A6000", [{"sale_price": 150.0}])
    # 29 days later -> still fresh
    clock.t = T0 + timedelta(days=29)
    assert cache.get("url", "Sony A6000", 30) is not None
    # 31 days later -> stale, treated as a miss
    clock.t = T0 + timedelta(days=31)
    assert cache.get("url", "Sony A6000", 30) is None


def test_monthly_ledger_counts_and_rolls_over(tmp_path):
    clock = _Clock(T0)
    cache = SoldFeedCache(tmp_path, now=clock)
    cache.record_pull()
    cache.record_pull()
    assert cache.pulls_this_month() == 2
    assert cache.remaining(50) == 48
    # next month starts fresh
    clock.t = datetime(2026, 8, 1, tzinfo=timezone.utc)
    assert cache.pulls_this_month() == 0
    assert cache.remaining(50) == 50


def test_check_budget_raises_at_cap(tmp_path):
    cache = SoldFeedCache(tmp_path, now=_Clock(T0))
    for _ in range(3):
        cache.record_pull()
    cache.check_budget(5)  # under cap -> fine
    cache.record_pull()
    cache.record_pull()  # now 5
    with pytest.raises(BudgetExceeded):
        cache.check_budget(5)


def _cameras_src(tmp_path, clock):
    cfg = apply_sector(load_config(), "cameras-lenses")
    cache = SoldFeedCache(tmp_path, now=clock)
    return ThirdPartySource(api_key="x", cfg=cfg, cache=cache), cfg, cache


def test_get_pulls_once_then_serves_from_cache(tmp_path, monkeypatch):
    src, cfg, cache = _cameras_src(tmp_path, _Clock(T0))
    calls = {"n": 0}

    def fake_post(url, headers=None, json=None, timeout=None):
        calls["n"] += 1
        return _FakeResp(_sold_response())

    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    endpoint = cfg["thirdparty"]["sold"]
    first = src._get(endpoint, "Sony A6000")
    assert len(first) == 2 and calls["n"] == 1
    assert cache.pulls_this_month() == 1
    # identical query -> served from cache, no second HTTP call, no extra pull
    second = src._get(endpoint, "Sony A6000")
    assert second == first and calls["n"] == 1
    assert cache.pulls_this_month() == 1


def test_get_refuses_pull_when_budget_spent(tmp_path, monkeypatch):
    src, cfg, cache = _cameras_src(tmp_path, _Clock(T0))
    for _ in range(50):  # exhaust the monthly budget
        cache.record_pull()

    def boom(*a, **k):
        raise AssertionError("must not hit the network when budget is spent")

    import requests
    monkeypatch.setattr(requests, "post", boom)

    with pytest.raises(BudgetExceeded):
        src._get(cfg["thirdparty"]["sold"], "Nikon D610")  # uncached -> would pull


def test_per_run_pull_cap_bounds_one_run(tmp_path, monkeypatch):
    """The per-run cap stops a single cold-cache run from draining the monthly budget:
    it pulls up to the cap, then refuses further live pulls (caller degrades to no comps)."""
    src, cfg, cache = _cameras_src(tmp_path, _Clock(T0))
    endpoint = dict(cfg["thirdparty"]["sold"])
    endpoint["max_pulls_per_run"] = 2  # tighten for the test

    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResp(_sold_response())

    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    src._get(endpoint, "Nikon D610")     # miss -> pull 1
    src._get(endpoint, "Nikon D7000")    # miss -> pull 2
    assert cache.pulls_this_month() == 2
    with pytest.raises(BudgetExceeded):
        src._get(endpoint, "Canon 600D")  # 3rd distinct miss -> over per-run cap
    # a query already cached this run still serves for free, cap notwithstanding
    assert src._get(endpoint, "Nikon D610") is not None
    assert cache.pulls_this_month() == 2  # monthly ledger untouched by the refusal
