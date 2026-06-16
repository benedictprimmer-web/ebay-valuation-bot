# ADR-003 — Category scope for v1

**Status:** Accepted
**Date:** 2026-06-16

## Context
You can't value "everything." The valuation calibration (sold-vs-asking ratio) is category-specific, and v1's job is to prove the valuation engine works. The best v1 category has standardized identifiers, high liquidity, and low condition variance.

## Decision
v1 starts with **graded sports cards (PSA/BGS slabs)**. The data model treats _category_ as a parameter so a second category can be cloned later, but v1 runs a single calibration.

## Consequences
- Grading removes condition variance — the biggest source of valuation error — so the engine is tested on honest data.
- Comps line up cleanly (player + set + grade is near-fungible); high liquidity gives enough auctions to act on.
- Overlaps Ben's football knowledge.
- Multi-category support is deferred, not designed away: adding category #2 later is a config/clone job, not a rebuild. Building a multi-category framework now would be premature over-engineering.
