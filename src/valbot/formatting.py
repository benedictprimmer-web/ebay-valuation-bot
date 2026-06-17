"""Alert formatting. Ben sees how sure the bot is, not just a number."""

from __future__ import annotations

from .models import Assessment
from .targets import TargetResult, verdict


def format_alert(a: Assessment) -> str:
    """One WhatsApp message per underpriced auction."""
    v = a.valuation
    assert v is not None and a.max_bid is not None
    lines = [
        "🏷️ Underpriced card",
        v.card.label(),
        "",
        f"Current bid: £{a.listing.price:.2f}",
        f"MAX BID:     £{a.max_bid:.2f}   (headroom £{a.headroom:.2f})",
        f"Exp. profit: £{a.expected_profit:.2f}  ·  margin {a.margin:.0%}",
        "",
        f"Point value:        £{v.point_value:.2f}",
        f"Conservative value: £{v.conservative_value:.2f}",
        f"Confidence: {v.confidence_label} ({v.confidence:.2f})  ·  "
        f"n={v.n}  ·  spread £{v.dispersion:.2f} ({v.rel_dispersion:.0%})",
        "",
        a.listing.url,
        "",
        "Read-only alert. You place the bid.",
    ]
    return "\n".join(lines)


def format_summary(assessments: list[Assessment], alerts: list[Assessment]) -> str:
    """Console summary for a run."""
    out = [
        f"Assessed {len(assessments)} auction(s); {len(alerts)} alert(s).",
    ]
    for a in alerts:
        v = a.valuation
        out.append(
            f"  ALERT  {v.card.label()}  cur £{a.listing.price:.2f} "
            f"-> max £{a.max_bid:.2f}  profit £{a.expected_profit:.2f} "
            f"({a.margin:.0%})  conf {v.confidence_label} n={v.n}"
        )
    skipped = [a for a in assessments if not a.is_alert]
    if skipped:
        out.append(f"  {len(skipped)} skipped:")
        for a in skipped[:20]:
            label = a.valuation.card.label() if a.valuation else a.listing.card.label()
            out.append(f"    - {label}: {'; '.join(a.reasons) or 'no reason'}")
    return "\n".join(out)


# --------------------------------------------------------------- targets mode


def target_to_dict(r: TargetResult) -> dict:
    """One watch-list result as a plain dict (for the JSON output / calibration)."""
    a = r.assessment
    v = a.valuation
    return {
        "card": r.target.label,
        "current_price": r.target.current_price,
        "verdict": verdict(r),
        "max_bid": a.max_bid,
        "headroom": a.headroom if r.has_price else None,
        "expected_profit": a.expected_profit if r.has_price else None,
        "margin": a.margin if r.has_price else None,
        "comp_count": v.n if v else 0,
        "confidence": v.confidence_label if v else None,
        "confidence_score": v.confidence if v else None,
        "point_value": round(v.point_value, 2) if v else None,
        "conservative_value": round(v.conservative_value, 2) if v else None,
        "passed_gate": a.passed_gate,
        "reasons": a.reasons,
    }


def format_targets(results: list[TargetResult]) -> str:
    """Console table for a targets run. One line per card, verdict first."""
    out = [f"Valued {len(results)} watched card(s) against sold comps.", ""]
    for r in results:
        a = r.assessment
        v = a.valuation
        out.append(verdict(r))
        out.append(f"   {r.target.label}")
        if v is not None:
            conf = f"{v.confidence_label} ({v.confidence:.2f})"
            out.append(
                f"   value £{v.point_value:.2f} (conservative £{v.conservative_value:.2f})"
                f"  ·  max bid £{a.max_bid:.2f}" if a.max_bid is not None
                else f"   value £{v.point_value:.2f} (conservative £{v.conservative_value:.2f})"
            )
            line = f"   confidence {conf}  ·  n={v.n} comps  ·  spread {v.rel_dispersion:.0%}"
            if r.has_price:
                line += (
                    f"\n   current £{r.target.current_price:.2f}"
                    f"  ·  exp. profit £{a.expected_profit:.2f}  ·  margin {a.margin:.0%}"
                )
            out.append(line)
        out.append("")
    return "\n".join(out).rstrip()
