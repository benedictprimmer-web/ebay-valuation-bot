"""Alert formatting. Ben sees how sure the bot is, not just a number."""

from __future__ import annotations

from .models import Assessment


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
