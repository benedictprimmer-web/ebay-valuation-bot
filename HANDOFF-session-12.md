# HANDOFF — eBay Valuation Bot, after session 12 (orchestrator)

Date: 2026-07-05. Read this first, then CLAUDE.md, then the two docs called out below.
Written to be handed to a capable model to drive the next phase.

## One line

The cameras lane is live and screened, but **half the niches were returning no sold comps
because transient empty feed responses got cached for 30 days** — now fixed and self-healing.
The next phase is: get real sold data via eBay Marketplace Insights (removes the flaky 50/month
third-party feed), grow niches once that cap is gone, and start turning human labels into tuning.
Main is at `881b187`, 108 tests pass.

## State of the system

- **Live lane:** `live-cameras.yml`, hourly, hybrid mode (free eBay Browse auctions valued
  against cached sold comps). Green. ~4 real alerts on a good day; 11 alerts logged so far.
- **40 niches** (30 bodies + 10 lenses), all resolving to an exact identity.
- **Screening on every target:** exact-model match, body-only (no kits/bundles), condition
  (drop for-parts/faulty), seller feedback ≥98%, shutter count (when stated), real postage.
- **Valuation:** conservative value from the sold-price distribution, confidence gate on
  comp count + dispersion, itemised fee model, max-bid solver. Read-only — never bids.
- **Feedback loop (built, barely used):** each alert has a ref code; `verdict.py` records
  good/bad (+ fair £); `calibrate.py` turns verdicts into per-niche over/under-valuation
  signals. **Only 1 human verdict recorded so far** — collection hasn't really started.
- **Summaries:** daily 7pm (lists alerts with codes as a labelling worksheet), weekly Sunday.

## The data problem this session uncovered (important)

From `observations.jsonl`: 462 of 995 assessments were "no comps". Cause: **20 of 40 niches
had an empty sold-feed result cached for the full 30 days.** The metered RapidAPI feed
(`ebay-average-selling-price`) rate-limited during warm-up and returned nothing, and we
cached that as if it were real. Proof: "Sony A7 2" cached 0 comps while "Sony A7 II" cached
60 (same camera); same-day queries split 60/0 with no pattern.

Fixed: empty results now expire after `empty_cache_days: 3` (not 30) and re-pull, bounded by
the budget caps. **But recovery is budget-gated:** the July ledger is at **43/50**, so only
~7 dead niches re-warm this month; the rest recover when the ledger resets **1 Aug**. This is
the strongest argument for Marketplace Insights below.

## Marketplace Insights — the intended fix for the data layer

The whole empty-comp mess comes from depending on a rate-limited third-party feed capped at
50 lookups/month. eBay's own **Marketplace Insights API** returns true UK sold prices (last
~90 days) with proper limits. It's the right long-term source.

**Ben must apply — it is not automatic with a dev account.** Marketplace Insights is a
restricted/limited-release Buy API. Steps (confirm current details at developer.ebay.com,
this may have shifted):
1. eBay developer account (Ben has one) with a **production keyset**.
2. Apply for access to the **Marketplace Insights API** (Buy APIs → request access / limited
   release application), describing the use case (personal resale valuation, read-only).
3. Accept the API licence / terms; eBay reviews and grants.
4. On grant you get the scope `https://api.ebay.com/oauth/api_scope/buy.marketplace.insights`
   and the endpoint `buy/marketplace_insights/v1_beta/item_sales/search`.

**Implementing it (a task for the next session, once granted) — NOT a pure config swap:**
- It uses OAuth client-credentials (same as our Browse source), not RapidAPI headers, so add
  an OAuth-authenticated sold source (reuse `BrowseAPISource._get_token`) or teach
  `ThirdPartySource` a `bearer` auth scheme. ~small.
- Confirm the field paths (item price, condition, sold date) against a real response and put
  them in the sector's `thirdparty.sold` block.
- Keep the cache + budget guards; MI's higher limits mean `monthly_pull_budget` can rise a
  lot, and the empty-cache problem largely disappears.
- Site/marketplace = EBAY_GB, GBP, so no FX.

## More niches — sequence AFTER Marketplace Insights

Ben wants more niches and more data — right call, but do it in order. Against today's 50/month
cap, 40 niches already strain the budget (that's partly what caused the empties). Adding more
now makes it worse. **Once MI removes the cap, expand freely.** Candidate next batch (all should
be verified with `parse_camera` first, and mostly one tier down / mid-liquidity):
- Bodies: Canon 1300D, 1200D, 2000D, 4000D, 80D, 90D; Nikon D3500, D5500, D7100, D7200, D750;
  Sony A6600, A6400; Fujifilm X-T2, X-T4, X-S10; Panasonic G9, GH5; Olympus E-M5 III.
- Lenses: Canon EF-S 18-55 STM, EF 75-300, EF 24-70 f4 L; Nikon 18-105 VR, 70-300;
  Sony FE 28-70, E 55-210; Fujifilm XF 18-55; Sigma 18-35 f1.8 (needs mount-aware identity).
- Two parser/identity jobs before some of these resolve cleanly: Canon 4-digit bodies
  (1200D/1300D) and mount-aware third-party lens keys (Sigma/Tamron span mounts under one key).

## Open threads / priorities (for the strong model)

1. **Marketplace Insights** (above) — the highest-leverage change; unblocks data + niches.
2. **Start labelling.** The loop exists but has 1 verdict. Get Ben rating the daily worksheet;
   at ~50 labels / ~5 per niche, run the Phase-2 analysis in `docs/plan-labelling-stage.md`.
3. **Watch which niches stay empty after re-warm.** If a query is *persistently* 0 (not
   transient), its search term needs work (add "EOS", a lens mount token, etc.).
4. **P2 quality:** fetch the listing description (Browse getItem) for shortlisted candidates
   to read shutter count / faults / accessories — title-only misses most. See
   `docs/analysis-quality-condition.md`.
5. **Near-close auction alerting:** a fresh £1 auction with 47h left can fire a speculative
   alert then get bid up. Only alert pure auctions near close, or tag them.
6. **DST:** the two digest crons are `0 18` (7pm BST) — flip to `0 19` when UK clocks go back.
7. **Hourly self-check-in automation** never armed (scheduler tool needed a one-time approval
   that failed). Re-offer.

## Merge / working policy

- Land changes via **local rebase + fast-forward to `main`**, never squash via the GitHub UI
  (that re-authors the commit and trips the stop-hook Unverified check). Committer stays
  `Claude <noreply@anthropic.com>`.
- Read-only forever. The bot never bids or spends.
- Data-collection phase: keep alerts LOOSE; tune only from labels, one lever at a time,
  Ben approves each change.

## How to run

```bash
python run.py --mode hybrid --sector cameras-lenses --dry-run     # live cameras, no WhatsApp
python run.py --sector cameras-lenses --daily-summary --dry-run   # the 7pm labelling worksheet
python verdict.py <ref> good|bad [reason] [--fair £]              # record a human verdict
python calibrate.py                                               # tuning report incl. verdicts
python scan.py --sector cameras-lenses --mode thirdparty         # niche scatter (cached)
python -m pytest -q                                              # 108 passing
```

Key files: `config.yaml` (all tunables), `src/valbot/ebay_client.py` (sources + gates),
`src/valbot/cache.py` (cache + budget), `src/valbot/valuation.py`, `src/valbot/camera.py`
(identity + shutter), `verdict.py` / `calibrate.py` (feedback loop).

## Opening message to paste next time (orchestrator)

Picking the eBay valuation bot back up. Read HANDOFF-session-12.md, then CLAUDE.md,
docs/analysis-quality-condition.md and docs/plan-labelling-stage.md. State: cameras lane is
live (hourly, ~4 alerts/day), 40 niches, screened for body-only / condition / seller / shutter
/ postage, feedback loop built (verdict.py → calibrate.py) but only 1 label so far. Main at
881b187, 108 tests pass. Half the niches recently had no comps (transient feed empties cached
30 days); fixed with a short empty-cache TTL, recovering as the budget allows (full recovery
early August). Merge policy: local rebase + fast-forward to main, never squash via UI.
Read-only always. Before acting, ask me: (1) did the Marketplace Insights application go
through — if so, wire it (OAuth sold source, confirm field paths) as the top priority; (2) how
many human labels have accumulated (python calibrate.py); (3) do you want to expand niches now
(only sensible once MI lifts the 50/month cap). Priorities in order: Marketplace Insights →
labelling analysis → niche expansion. Keep alerts loose; tune only from labels, one lever at a
time, my approval each change.
```
