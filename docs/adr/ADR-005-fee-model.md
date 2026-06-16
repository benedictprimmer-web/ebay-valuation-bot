# ADR-005 — Fee model for v1

**Status:** Accepted
**Date:** 2026-06-16

## Context
Every cost between the winning bid and the final profit must be in the buy-threshold math, or "profit" is fiction. Relevant 2026 UK facts:
- Business sellers pay ~12.8% final value fee + a fixed ~£0.40 per order (>£10).
- Private sellers pay £0 final value fees (since Oct 2024) — but resale volume risks reclassification as a business.
- Buyers pay a UK buyer-protection fee on many categories, including collectibles.
- Postage is paid both inbound (acquiring) and outbound (reselling).

## Decision
Bake in the **conservative all-in** model, itemised:

```
max bid = valuation − target margin
          − sell-side fee (~12.8% + ~£0.40)
          − buyer-protection fee (purchase)
          − postage(inbound)
          − postage(outbound)
```

Private-seller £0 sell fees are treated as upside, never assumed. Components stay itemised (not a single blended %) so it's visible which cost eats margin and the model survives eBay rate changes.

## Consequences
- Occasionally misses a thin deal, but every fired alert is genuinely profitable after all costs.
- Slightly more to maintain than a flat haircut, but transparent and rate-change resilient.
- Exact rates must be confirmed against eBay's live fee calculator before launch (placeholders until then).
