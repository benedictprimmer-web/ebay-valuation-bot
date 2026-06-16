# ADR-008 — Confidence gate for v1

**Status:** Accepted
**Date:** 2026-06-16

## Context
Because v1 confirms every buy manually (ADR-002), the dominant risk is not runaway spend — it's a bad valuation making Ben overpay, plus alert spam from thin data eroding trust in the alerts. A valuation is only as good as the comps behind it, and the calibration is unproven at launch.

## Decision
Apply a **strict confidence gate**: only alert when there are ≥8 comparable active listings AND the price spread is under a set threshold. Skip thin or scattered data. Every alert still shows the underlying confidence signals (comp count, spread) alongside max bid and margin. Kill switch is simply disabling the scheduled workflow.

## Consequences
- Fewer but higher-quality alerts while calibration is unproven; cheap mistakes stay rare.
- Ben sees *why* the bot is confident and can overrule.
- The thresholds (≥8 comps, spread bound) are placeholders to tune from logged outcomes — loosen as accuracy proves out.
- No budget-cap automation needed in v1 since no money moves without a human; revisit if automation is added later.
