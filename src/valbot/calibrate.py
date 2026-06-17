"""Turn logged outcomes into calibration numbers.

The model ships with placeholders: a sold ratio, the floors, the fees. The honest way
to set them is from reality. Every alert is logged to data/outcomes.json with its
prediction; once you fill in what actually happened (won?, final price, what it resold
for), this reads those back and tells you whether the model was right and what to nudge.

Nothing here is trusted blind — it reports what the data says and suggests, it doesn't
auto-edit the config. With no resolved outcomes yet, it explains what to fill in.
"""

from __future__ import annotations

from statistics import median


def _resolved(records: list[dict]) -> list[dict]:
    """Records where you've filled in a real resale price — enough to calibrate value."""
    out = []
    for r in records:
        res = r.get("result") or {}
        if res.get("resold_price") is not None:
            out.append(r)
    return out


def compute_calibration(records: list[dict]) -> dict:
    logged = len(records)
    resolved = _resolved(records)
    won = [r for r in records if (r.get("result") or {}).get("won") is True]

    summary: dict = {
        "logged": logged,
        "won": len(won),
        "resolved_for_calibration": len(resolved),
    }
    if not resolved:
        summary["status"] = "no resolved outcomes yet"
        return summary

    realized_ratios: list[float] = []
    conservative_safe = 0
    profit_errors: list[float] = []
    for r in resolved:
        pred = r.get("prediction") or {}
        res = r.get("result") or {}
        resold = float(res["resold_price"])
        pv = pred.get("point_value")
        ratio_used = pred.get("ratio_used")
        if pv and ratio_used:
            implied_comp_median = pv / ratio_used
            if implied_comp_median > 0:
                realized_ratios.append(resold / implied_comp_median)
        cv = pred.get("conservative_value")
        if cv is not None and resold >= cv:
            conservative_safe += 1
        rp = res.get("realised_profit")
        ep = pred.get("expected_profit")
        if rp is not None and ep is not None:
            profit_errors.append(float(rp) - float(ep))

    if realized_ratios:
        summary["suggested_sold_ratio"] = round(median(realized_ratios), 3)
        summary["ratio_samples"] = len(realized_ratios)
    summary["conservative_coverage"] = round(conservative_safe / len(resolved), 3)
    if profit_errors:
        summary["profit_bias"] = round(median(profit_errors), 2)  # +ve = we under-promised
    summary["status"] = "calibrated"
    return summary


def format_calibration(s: dict) -> str:
    lines = [
        "Calibration",
        f"  logged alerts:        {s['logged']}",
        f"  marked won:           {s['won']}",
        f"  resolved (resold):    {s['resolved_for_calibration']}",
    ]
    if s.get("status") != "calibrated":
        lines += [
            "",
            "  No resolved outcomes yet. To calibrate, open data/outcomes.json and fill",
            "  each record's `result`: won (true/false), final_price, resold_price,",
            "  realised_profit. Re-run this once a few real flips have resolved.",
        ]
        return "\n".join(lines)
    if "suggested_sold_ratio" in s:
        lines.append(
            f"  suggested sold ratio: {s['suggested_sold_ratio']} "
            f"(from {s['ratio_samples']} resolved; current config may differ)"
        )
    lines.append(
        f"  conservative coverage: {s['conservative_coverage']:.0%} "
        "(share where resale >= our conservative value; want this high)"
    )
    if "profit_bias" in s:
        sign = "under-promised" if s["profit_bias"] >= 0 else "OVER-promised"
        lines.append(f"  profit bias:          £{s['profit_bias']:+.2f} ({sign})")
    return "\n".join(lines)
