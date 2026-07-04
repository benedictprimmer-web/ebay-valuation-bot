"""Daily summary message (WhatsApp) — a heartbeat plus the day's deal count.

Runs once a day (7pm UK). Reads only the logs the hourly lane already writes
(outcomes.json, observations.jsonl) plus the pull ledger — no network, no sold-feed
pulls. Reports how many listings were assessed today, how many bargain alerts fired,
and how much of the monthly sold-price budget is left.

Even a zero-deal day sends a message, so silence is a signal that something's wrong
(a dead-man's switch), which is exactly what "send 0 found if none found" asks for.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_LONDON = "Europe/London"


def _london_now() -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(_LONDON))
    except Exception:  # zoneinfo/tzdata unavailable -> UTC is close enough
        return datetime.now(timezone.utc)


def _to_london_date(iso_ts: str):
    """Local (London) calendar date of an ISO timestamp, or None if unparseable."""
    try:
        dt = datetime.fromisoformat(str(iso_ts).replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        from zoneinfo import ZoneInfo

        return dt.astimezone(ZoneInfo(_LONDON)).date()
    except Exception:
        return dt.astimezone(timezone.utc).date()


def build_daily_summary(cfg: dict, data_dir: str | Path, *, now: datetime | None = None) -> str:
    """Compose the daily WhatsApp summary text from the logs on disk."""
    data_dir = Path(data_dir)
    now = now or _london_now()
    today = now.date()
    sector = cfg.get("active_sector", "cameras")

    # Today's bargain alerts (outcomes.json). Dedupe by listing so a model that was
    # re-logged across runs counts once — alert dedupe means that's rare, but be safe.
    alerts: list[dict] = []
    outcomes = data_dir / "outcomes.json"
    if outcomes.exists():
        try:
            rows = json.loads(outcomes.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            rows = []
        seen: set = set()
        for r in rows:
            lid = r.get("listing_id")
            if lid not in seen and _to_london_date(r.get("logged_at", "")) == today:
                seen.add(lid)
                alerts.append(r)

    # Today's assessed listings (observations.jsonl) — distinct listing ids.
    assessed: set = set()
    obs = data_dir / "observations.jsonl"
    if obs.exists():
        for line in obs.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if _to_london_date(o.get("ts", "")) == today:
                assessed.add(o.get("listing_id"))

    # Monthly sold-feed budget (read-only ledger; no network).
    budget_line = ""
    try:
        from .cache import SoldFeedCache

        budget = cfg.get("thirdparty", {}).get("sold", {}).get("monthly_pull_budget")
        if budget is not None:
            used = SoldFeedCache(data_dir / "cache").pulls_this_month()
            budget_line = f"\n🗓️ Sold-price lookups: {used}/{budget} used this month."
    except Exception:
        pass

    header = f"📷 valbot daily — {sector} — {today:%a %d %b %Y}"
    assessed_line = f"Assessed {len(assessed)} listing(s) across today's hourly runs."
    if alerts:
        parts = [f"🎯 {len(alerts)} bargain alert(s) today:"]
        for r in alerts[:5]:
            pred = r.get("prediction", {}) or {}
            parts.append(
                f"• {r.get('card', '?')} — £{r.get('current_price', '?')} "
                f"(max £{pred.get('max_bid', '?')}, ~£{pred.get('expected_profit', '?')} profit)"
            )
        body = "\n".join(parts)
    else:
        body = "✅ 0 bargains found today. All quiet — the bot is alive and watching."

    return f"{header}\n{assessed_line}\n{body}{budget_line}"
