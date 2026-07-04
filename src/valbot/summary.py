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
from datetime import datetime, timedelta, timezone
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


# -- shared log readers (no network; read only what the hourly lane already writes) --

def _alerts_in(data_dir: Path, keep) -> list[dict]:
    """Alerts from outcomes.json whose London date passes keep(date), deduped by listing."""
    out: list[dict] = []
    path = Path(data_dir) / "outcomes.json"
    if not path.exists():
        return out
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return out
    seen: set = set()
    for r in rows:
        lid = r.get("listing_id")
        if lid not in seen and keep(_to_london_date(r.get("logged_at", ""))):
            seen.add(lid)
            out.append(r)
    return out


def _assessed_in(data_dir: Path, keep) -> set:
    """Distinct listing ids from observations.jsonl whose London date passes keep(date)."""
    out: set = set()
    path = Path(data_dir) / "observations.jsonl"
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if keep(_to_london_date(o.get("ts", ""))):
            out.add(o.get("listing_id"))
    return out


def _budget_line(cfg: dict, data_dir: Path, *, suffix: str = "") -> str:
    """The 'X/50 used this month' line from the pull ledger (read-only; no network)."""
    try:
        from .cache import SoldFeedCache

        budget = cfg.get("thirdparty", {}).get("sold", {}).get("monthly_pull_budget")
        if budget is not None:
            used = SoldFeedCache(Path(data_dir) / "cache").pulls_this_month()
            return f"\n🗓️ Sold-price lookups: {used}/{budget} used this month{suffix}."
    except Exception:
        pass
    return ""


def _fmt_alert(r: dict) -> str:
    pred = r.get("prediction", {}) or {}
    return (
        f"• {r.get('card', '?')} — £{r.get('current_price', '?')} "
        f"(max £{pred.get('max_bid', '?')}, ~£{pred.get('expected_profit', '?')} profit)"
    )


def build_daily_summary(cfg: dict, data_dir: str | Path, *, now: datetime | None = None) -> str:
    """Compose the daily WhatsApp summary text from the logs on disk."""
    now = now or _london_now()
    today = now.date()
    sector = cfg.get("active_sector", "cameras")

    alerts = _alerts_in(Path(data_dir), lambda d: d == today)
    assessed = _assessed_in(Path(data_dir), lambda d: d == today)
    budget_line = _budget_line(cfg, Path(data_dir))

    header = f"📷 valbot daily — {sector} — {today:%a %d %b %Y}"
    assessed_line = f"Assessed {len(assessed)} listing(s) across today's hourly runs."
    if alerts:
        body = "\n".join([f"🎯 {len(alerts)} bargain alert(s) today:"] + [_fmt_alert(r) for r in alerts[:5]])
    else:
        body = "✅ 0 bargains found today. All quiet — the bot is alive and watching."
    return f"{header}\n{assessed_line}\n{body}{budget_line}"


def build_weekly_digest(cfg: dict, data_dir: str | Path, *, now: datetime | None = None) -> str:
    """Compose the weekly WhatsApp digest — a rolling 7-day window ending today."""
    now = now or _london_now()
    end = now.date()
    start = end - timedelta(days=6)  # inclusive 7-day window
    keep = lambda d: d is not None and start <= d <= end  # noqa: E731
    sector = cfg.get("active_sector", "cameras")
    niches = len(cfg.get("search", {}).get("queries", []) or [])

    alerts = _alerts_in(Path(data_dir), keep)
    assessed = _assessed_in(Path(data_dir), keep)
    budget_line = _budget_line(cfg, Path(data_dir), suffix=f" · {niches} niches watched")

    header = f"📅 valbot weekly — {sector} — w/e {end:%a %d %b %Y}"
    assessed_line = f"This week ({start:%d %b}–{end:%d %b}): assessed {len(assessed)} listing(s)."
    if alerts:
        alerts.sort(
            key=lambda r: (r.get("prediction", {}) or {}).get("expected_profit") or 0.0,
            reverse=True,
        )
        models = {r.get("card") for r in alerts}
        head = f"🎯 {len(alerts)} bargain alert(s) across {len(models)} model(s). Top:"
        body = "\n".join([head] + [_fmt_alert(r) for r in alerts[:5]])
    else:
        body = "✅ 0 bargains this week. Quiet market — the bot is alive and watching."
    return f"{header}\n{assessed_line}\n{body}{budget_line}"
