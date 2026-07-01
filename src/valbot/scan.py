"""Niche scatter scanner — find WHERE sold prices differ most.

The bot values one item at a time and (rightly) gates OUT scattered comps: you can't
confidently price a single card when sold prices are all over the place. But for
*prospecting* — deciding which niches are worth hunting in — scatter is the whole
point. A wide sold-price distribution means an inefficient market: bargains sit in
the low tail, below the price the item usually clears at.

For each query in the active sector this fetches sold comps (through the cache +
monthly budget, so a warm cache costs zero pulls), measures the distribution, and
ranks niches by an opportunity score = differentiation scaled by liquidity. Each
scan is appended to data/scatter_history.json so a trend builds over time.

Read-only. Places no bids, spends no pulls beyond the comps a valuation would anyway.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from .cache import BudgetExceeded
from .camera import parse_camera
from .ebay_client import parse_grade, query_tokens
from .models import Card
from .robust_stats import spread


def resolve_query(query: str, identity: str):
    """Turn a sector search query into the identity fetch_comps expects.

    camera -> exact body/lens via parse_camera (None if it doesn't resolve).
    card   -> Card from grader+grade plus player/set tokens (as the card lane builds it).
    """
    if identity == "camera":
        item = parse_camera(query)
        return item if item.resolved else None
    parsed = parse_grade(query)
    if not parsed:
        return None
    grader, grade = parsed
    tokens = query_tokens(query)
    return Card(
        player=tokens[0] if tokens else "unknown",
        set_name=" ".join(tokens[1:]) if len(tokens) > 1 else "unknown",
        variant="base",
        grader=grader,
        grade=grade,
    )


def scatter_stats(prices: list[float], method: str = "mad") -> dict:
    """Distribution shape for one niche. Empty dict if there's nothing to measure."""
    n = len(prices)
    if n == 0:
        return {}
    med = median(prices)
    lo, hi = min(prices), max(prices)
    disp = spread(prices, method) if n > 1 else 0.0
    rel_disp = (disp / med) if med > 0 else 0.0
    # Arbitrage edge: buy near the low tail, clear near the middle.
    edge_gbp = med - lo
    edge_pct = (edge_gbp / med) if med > 0 else 0.0
    # Differentiation (rel dispersion) rewarded by liquidity (more comps = more chances).
    score = rel_disp * (n ** 0.5)
    return {
        "n": n,
        "median": round(med, 2),
        "min": round(lo, 2),
        "max": round(hi, 2),
        "rel_dispersion": round(rel_disp, 3),
        "edge_gbp": round(edge_gbp, 2),
        "edge_pct": round(edge_pct, 3),
        "score": round(score, 3),
    }


def scan(cfg: dict, source) -> list[dict]:
    """One row per sector query, ranked by opportunity score (highest scatter first)."""
    identity = cfg.get("identity", "card")
    method = cfg["valuation"]["spread_method"]
    cache = getattr(source, "cache", None)
    rows: list[dict] = []
    for query in cfg["search"]["queries"]:
        ident = resolve_query(query, identity)
        if ident is None:
            rows.append({"query": query, "source": "unresolved", "stats": {}})
            continue
        before = cache.pulls_this_month() if cache else None
        try:
            comps = source.fetch_comps(ident)
        except BudgetExceeded:
            rows.append({"query": query, "source": "skipped (budget)", "stats": {}})
            continue
        if cache is None:
            src = "live"
        else:
            src = "fresh pull" if cache.pulls_this_month() > before else "cache"
        stats = scatter_stats([c.price for c in comps], method)
        rows.append({"query": query, "source": src, "stats": stats})
    rows.sort(key=lambda r: r["stats"].get("score", -1.0), reverse=True)
    return rows


def format_scan(rows: list[dict], cfg: dict) -> str:
    label = cfg.get("active_sector", "?")
    out = [
        f"Scatter scan — sector: {label}",
        "Ranked by opportunity (rel-dispersion × √n). Buy the low tail, clear near median.",
        "",
        f"  {'query':<24} {'n':>3} {'median':>8} {'min':>7} {'max':>7} "
        f"{'reldisp':>8} {'edge£':>7} {'edge%':>6}  source",
        f"  {'-'*24} {'-'*3} {'-'*8} {'-'*7} {'-'*7} {'-'*8} {'-'*7} {'-'*6}  {'-'*12}",
    ]
    for r in rows:
        s = r["stats"]
        if not s:
            out.append(f"  {r['query']:<24} {'—':>3} {'':>8} {'':>7} {'':>7} "
                       f"{'':>8} {'':>7} {'':>6}  {r['source']}")
            continue
        out.append(
            f"  {r['query']:<24} {s['n']:>3} {s['median']:>8.2f} {s['min']:>7.2f} "
            f"{s['max']:>7.2f} {s['rel_dispersion']:>8.3f} {s['edge_gbp']:>7.2f} "
            f"{s['edge_pct']*100:>5.1f}%  {r['source']}"
        )
    return "\n".join(out)


def append_history(rows: list[dict], cfg: dict, path: str | Path, *, now=None) -> None:
    """Append this scan to the history file so niche scatter can be tracked over time."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now(timezone.utc)).isoformat()
    record = {
        "scanned_at": stamp,
        "sector": cfg.get("active_sector"),
        "rows": [{"query": r["query"], "source": r["source"], **r["stats"]} for r in rows],
    }
    history = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    history.append(record)
    p.write_text(json.dumps(history, indent=2), encoding="utf-8")
