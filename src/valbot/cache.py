"""Disk-backed cache + monthly pull budget for the metered sold-price feed.

The RapidAPI sold feed is capped (see CLAUDE.md: 50 pulls/month). Sold-price
distributions are near-stationary week to week, so we cache each query's response
for `cache_days` (~a month): a re-run of the same model then costs ZERO pulls, and
the whole "1 pull per item per month = 50 items" budget model falls out for free.

A hard monthly ledger backstops the cache. On a cache MISS — the only thing that
triggers a live pull — the budget is checked first; once the month's allowance is
spent, the pull is refused (BudgetExceeded) rather than silently overrunning the
quota. Callers degrade that to "no fresh data" so a run never crashes on it.

Both files live under data/cache/ and are committed back by the workflow, so the
cache and ledger survive across the ephemeral GitHub Actions runs.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


class BudgetExceeded(RuntimeError):
    """Raised when a live pull would exceed the monthly sold-feed budget."""


class FeedUnavailable(RuntimeError):
    """Raised when the sold feed can't be reached (HTTP 429/5xx, timeout, network).

    Callers degrade to 'no fresh comps' and skip, exactly as for BudgetExceeded — a
    feed hiccup must never crash a read-only run."""


class SoldFeedCache:
    """Response cache + monthly pull ledger for a metered HTTP feed.

    `now` is injectable so tests can age entries or roll the month without sleeping.
    """

    def __init__(self, cache_dir: str | Path, *, now=None):
        self.dir = Path(cache_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.dir / "sold_cache.json"
        self.ledger_path = self.dir / "pull_ledger.json"
        self._now = now or _utcnow

    # -- json helpers --------------------------------------------------------
    @staticmethod
    def _load(path: Path) -> dict:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    @staticmethod
    def _save(path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def key(url: str, query: str) -> str:
        return hashlib.sha1(f"{url}::{query}".encode("utf-8")).hexdigest()[:16]

    # -- response cache ------------------------------------------------------
    def get(
        self,
        url: str,
        query: str,
        cache_days: float,
        empty_cache_days: float | None = None,
    ) -> list[dict] | None:
        """Fresh cached items for (url, query), or None if absent/stale.

        An EMPTY cached result (0 comps) is usually a transient upstream hiccup —
        the metered feed rate-limiting and returning nothing — not a real "no sales".
        Caching that for the full `cache_days` locks a live niche out for a month. So an
        empty entry expires after the much shorter `empty_cache_days` and is re-pulled.
        """
        entry = self._load(self.cache_path).get(self.key(url, query))
        if not entry:
            return None
        fetched = datetime.fromisoformat(entry["fetched_at"])
        age_days = (self._now() - fetched).total_seconds() / 86400.0
        ttl = float(cache_days)
        if not entry.get("items") and empty_cache_days is not None:
            ttl = float(empty_cache_days)
        if age_days > ttl:
            return None
        return entry["items"]

    def put(self, url: str, query: str, items: list[dict]) -> None:
        cache = self._load(self.cache_path)
        cache[self.key(url, query)] = {
            "fetched_at": self._now().isoformat(),
            "query": query,
            "items": items,
        }
        self._save(self.cache_path, cache)

    # -- monthly pull ledger -------------------------------------------------
    def pulls_this_month(self) -> int:
        return int(self._load(self.ledger_path).get(_month_key(self._now()), 0))

    def remaining(self, budget: int | None) -> int | None:
        """Pulls left this month, or None when no budget is configured."""
        if budget is None:
            return None
        return max(0, int(budget) - self.pulls_this_month())

    def check_budget(self, budget: int | None) -> None:
        """Raise BudgetExceeded if a live pull now would breach the monthly budget."""
        if budget is None:
            return
        used = self.pulls_this_month()
        if used >= int(budget):
            raise BudgetExceeded(
                f"monthly sold-feed budget reached: {used}/{budget} pulls used this "
                f"month. Skipping live pull (cached data still served)."
            )

    def record_pull(self) -> None:
        ledger = self._load(self.ledger_path)
        mk = _month_key(self._now())
        ledger[mk] = int(ledger.get(mk, 0)) + 1
        self._save(self.ledger_path, ledger)
