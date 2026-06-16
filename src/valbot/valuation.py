"""Valuation with uncertainty priced in.

The whole point of this session: don't output a single number. Output a distribution
and bid against its conservative end. Wider spread or fewer comps pulls the
conservative value down on its own — uncertainty isn't a warning label bolted on the
side, it's in the number the money decision uses.

Per card:
  point_value        = median(comp asking) * sold_to_asking_ratio
  dispersion         = robust spread (MAD or IQR) of asking, * ratio (value scale)
  n                  = comp count
  rel_dispersion     = dispersion / point_value
  confidence         = f(n, rel_dispersion) in [0, 1]
  conservative_value = point_value - k * dispersion   (k ~ 1)

Every downstream money decision uses conservative_value, never point_value.
"""

from __future__ import annotations

from statistics import median

from .models import Card, Listing, Valuation
from .robust_stats import spread


def match_comps(comps: list[Listing], card: Card) -> list[Listing]:
    """Strict match on player + set + variant + grader + grade."""
    return [c for c in comps if c.matches(card)]


def _confidence(n: int, rel_dispersion: float, cfg: dict) -> tuple[float, str]:
    """High n and tight spread -> high confidence. Both pull it down independently."""
    n_full = cfg["n_full_confidence"]
    rel_zero = cfg["rel_dispersion_zero_conf"]

    n_factor = min(1.0, n / n_full) if n_full > 0 else 1.0
    disp_factor = max(0.0, 1.0 - (rel_dispersion / rel_zero)) if rel_zero > 0 else 1.0
    score = round(n_factor * disp_factor, 3)

    if score >= cfg["confidence_high"]:
        label = "high"
    elif score >= cfg["confidence_medium"]:
        label = "medium"
    else:
        label = "low"
    return score, label


def value_card(card: Card, comps: list[Listing], cfg: dict) -> Valuation | None:
    """Compute the valuation distribution for one card. None if no comps."""
    matched = match_comps(comps, card)
    if not matched:
        return None

    askings = [c.price for c in matched]
    ratio = cfg["sold_to_asking_ratio"]

    asking_median = median(askings)
    asking_spread = spread(askings, cfg["spread_method"])

    point_value = asking_median * ratio
    dispersion = asking_spread * ratio  # keep spread on the value scale
    rel_dispersion = dispersion / point_value if point_value > 0 else float("inf")

    conservative_value = point_value - cfg["k"] * dispersion
    conservative_value = max(0.0, conservative_value)

    confidence, label = _confidence(len(matched), rel_dispersion, cfg)

    return Valuation(
        card=card,
        n=len(matched),
        point_value=point_value,
        dispersion=dispersion,
        rel_dispersion=rel_dispersion,
        conservative_value=conservative_value,
        confidence=confidence,
        confidence_label=label,
        ratio=ratio,
    )
