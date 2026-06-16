# ADR-001 — Valuation source for v1

**Status:** Accepted
**Date:** 2026-06-16

## Context
Every buy decision is `valuation − margin − fees`, so the valuation signal must be real. eBay's actual sold-price data (Marketplace Insights API) is the gold signal but is access-restricted and frequently denied to resellers. Scraping sold data is visible but breaks eBay's user agreement.

## Decision
v1 derives worth from **active listings (free Browse API) adjusted by a manually-calibrated sold-vs-asking ratio per category**, seeded with a small hand-recorded set of sold comps.

## Consequences
- Shippable now, fully within ToS.
- Lower precision than true sold comps; accuracy depends on the calibration ratio and improves as real sold outcomes are logged.
- Leaves a clean upgrade path: swap in Marketplace Insights later if approved, without changing the buy logic.
