# ADR-004 — Alert ranking model for v1

**Status:** Accepted
**Date:** 2026-06-16

## Context
Margin % and absolute £ profit are different metrics that conflict (a 900% win can be £2; a 100% win can be £50). A single sort metric ignores one dimension. A weighted composite needs a weight guessed with no outcome data.

## Decision
Rank alerts by **expected £ profit per flip, gated by two floors**:
- Floor 1 (quality): margin ≥ ~25% — removes high-% but trivial-£ traps where fees/postage eat the win.
- Floor 2 (worth-the-effort): profit ≥ ~£15 — removes small-£ wins that cost the same manual effort as a big one.

The v1 price cap is a **separate** risk control, not a ranking input.

## Consequences
- Floors guarantee margin quality; the sort maximises money. Both dimensions respected without a tunable weight.
- Transparent — easy to explain why any alert ranked where it did.
- Assumes the binding constraint in v1 is time per flip (true while buys are manually confirmed). If capital becomes the constraint, a v2 toggle switches the sort to ROI (£ profit ÷ £ invested).
- Thresholds are placeholders to be calibrated from logged predicted-vs-actual outcomes.
