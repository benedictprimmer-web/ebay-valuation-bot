"""The one pass: poll -> match comps -> value -> gate -> threshold -> rank -> alert -> log.

Read-only. Nothing here places a bid or moves money.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ebay_client import ListingSource
from .formatting import format_alert
from .models import Assessment
from .threshold import assess
from .valuation import value_card


@dataclass
class RunResult:
    assessments: list[Assessment]
    alerts: list[Assessment]
    sent: int


def run_pipeline(cfg: dict, source: ListingSource, alerter, store) -> RunResult:
    targets = source.fetch_targets()

    assessments: list[Assessment] = []
    for target in targets:
        comps = source.fetch_comps(target.card)
        valuation = value_card(target.card, comps, cfg["valuation"])
        assessments.append(assess(target, valuation, cfg))

    # Alerts only: passed gate AND floors. Rank by expected £ profit (ADR-004).
    alerts = [a for a in assessments if a.is_alert]
    alerts.sort(key=lambda a: a.expected_profit, reverse=True)

    sent = 0
    dedupe = cfg["alert"]["dedupe"]
    max_per_run = cfg["alert"]["max_per_run"]
    for a in alerts:
        if sent >= max_per_run:
            break
        if dedupe and store.already_alerted(a.listing.listing_id):
            continue
        alerter.send(format_alert(a))
        store.log_alert(a)
        store.mark_alerted(a.listing.listing_id)
        sent += 1

    return RunResult(assessments=assessments, alerts=alerts, sent=sent)
