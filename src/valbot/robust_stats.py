"""Robust summary statistics. Pure Python, no numpy.

Robust (median/MAD/IQR) on purpose: one mad listing shouldn't blow up the spread.
See ADR-008 and the build handoff — uncertainty is priced into the bid, so the
spread measure must not be dragged by a single outlier the way std would be.
"""

from __future__ import annotations

from statistics import median


def percentile(values: list[float], pct: float) -> float:
    """Linear-interpolation percentile. `pct` in [0, 100]."""
    if not values:
        raise ValueError("percentile of empty sequence")
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    rank = (pct / 100) * (len(xs) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(xs) - 1)
    frac = rank - lo
    return xs[lo] + (xs[hi] - xs[lo]) * frac


def iqr(values: list[float]) -> float:
    """Interquartile range (Q3 - Q1)."""
    return percentile(values, 75) - percentile(values, 25)


def mad(values: list[float]) -> float:
    """Median absolute deviation from the median (raw, unscaled)."""
    if not values:
        raise ValueError("mad of empty sequence")
    med = median(values)
    return median([abs(x - med) for x in values])


def spread(values: list[float], method: str = "mad") -> float:
    """Robust dispersion. `method` is 'mad' or 'iqr'."""
    if method == "mad":
        return mad(values)
    if method == "iqr":
        return iqr(values)
    raise ValueError(f"unknown spread method: {method!r}")
