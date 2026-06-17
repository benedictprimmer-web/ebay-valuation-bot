# ADR-011 — Cameras lane: exact-model identity + the sold-comp source

**Status:** Accepted
**Date:** 2026-06-17

## Context
ADR-003 scoped v1 to graded cards because grading kills condition variance and makes
comps line up. Sessions 5–6 decided to add cameras/lenses as the primary category
(HANDOFF-session-6). Two things blocked it:

1. **Identity.** Cards match on grader + grade parsed from the title. Cameras don't have
   that — two listings are the same comp only if they're the same body or lens, and eBay
   titles are messy ("mark iii" vs "mk 3" vs "iii", missing suffixes, brand typos,
   α symbols). `src/valbot/camera.py` could parse a title into an exact model, but nothing
   used it — it was an orphan module.
2. **Sold comps.** The cards lane gets real sold prices from The Card API (ADR-010), which
   is cards-only and USD. No equivalent was wired for UK cameras, and eBay's own sold data
   (Marketplace Insights) stays partner-gated — confirmed still refused to resellers, June 2026.

## Decision

### A. Identity is a per-sector switch, not a rebuild
Added `identity: card | camera` to config. The neutral default is `card`; the
cameras-lenses sector overrides to `camera`. The switch routes title→identity at the
source boundary only:

- `camera` resolves a title to a `CameraItem` (brand + exact model) via `parse_camera`.
  A title that doesn't pin down a specific model returns None and is **dropped before
  valuation** — resolve-or-skip, the cameras equivalent of the cards confidence gate. The
  bot never bids on a guess.
- `CameraItem` exposes the same `key()` / `label()` / `matches()` that `Card` does, so the
  entire downstream — value → gate → fees → threshold → rank → alert — runs **unchanged**.
  No pipeline code is category-aware.

Wired through every source (mock, third-party, Browse) and the watchlist/targets loader.
A camera watchlist row is just a `title`; an ambiguous title is rejected at load so a
hand-curated list fails loud instead of valuing the wrong thing.

### B. Sold-comp source: start free + official, upgrade to real sold data
No clean, official UK sold-price feed exists. Every real sold source is a third-party
eBay scraper (same ToS grey-zone already accepted in ADR-009/010 for cards). The choice
is staged rather than single:

- **Now (default): Browse active-listing proxy.** Use the official, free, ToS-clean
  Browse API (`--mode browse`) to pull active listings for the exact model, take the median
  asking price, and apply a calibrated sold-to-asking ratio (~0.85 for used UK gear, the
  cards lane's original method). Costs nothing, signs up for nothing, and ships the moment
  the eBay keyset lands — the same unblock the rest of the bot waits on.
- **Upgrade: Apify eBay sold-listings actor.** Real ebay.co.uk GBP sold prices with
  condition/date filters, ~$4/1,000 results on Apify's free-tier base. The only researched
  option where GBP + sold-only + concrete price were all verifiable. Swap it in once the
  lane has flagged real auctions and the precision is worth paying for. Drops into the
  existing `thirdparty.sold` config block (ratio → 1.0 once comps are true sold prices).
- **Rejected: RapidAPI `ecommet` completed-items.** Architecturally the cleanest drop-in
  (returns a median directly, GB site confirmed), but its pricing tier could not be
  verified and it's an opaque single-provider dependency. Re-open if the Apify route
  disappoints.

The deciding criterion: get the lane live for £0 first; pay for accuracy only once it earns.

## Consequences
- Cameras run end-to-end today on `--mode mock` (fixture: `data/mock_cameras.json`); the
  live feed is one config edit + the keyset away. Cards lane untouched — 38 → 58 tests, all green.
- Identity quality is now the lane's main risk, not category. `parse_camera` covers the
  common Sony/Canon/Nikon/Fuji/Panasonic/Olympus model patterns; rare or oddly-written
  models fall to manual review rather than mis-valuing. Tighten patterns as real titles show gaps.
- The Browse proxy's ~0.85 ratio is a placeholder — calibrate from real sold outcomes, same
  as the cards ratio. Set it back to 1.0 when the Apify sold feed is wired.
- Two scraper caveats carried from ADR-009/010: third-party sources are ToS grey, and any
  US-sourced sold price ≠ UK resale value (cameras sector stays GBP-only, fx 1.0).
