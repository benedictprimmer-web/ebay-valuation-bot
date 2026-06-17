# HANDOFF — eBay Valuation Bot, after session 6
Date: 2026-06-17. Read this first next time.

## One line
Both deep-research efforts came back and converged: use eBay's official **Browse API**
for live data (we already built the client), **pivot toward cameras/lenses** as the
primary category with graded cards as the clean secondary, and **flip yourself** rather
than sell alerts. The model's wrong assumptions are fixed and the bot now switches between
sectors. Waiting on Ben's eBay developer approval to wire live data.

## What changed this session
1. **Research done + compiled.** Grok + two Claude-chat reports saved in `research/`.
   Two-page decision report at `reports/eBay-Bot-Decision-Report.pdf` (the main read).
   Earlier one-pagers (pricing model, synthesis) also in `reports/`.
2. **Sector profiles added.** `config.yaml` now has a `sectors` block; `--sector` switches
   between `graded-cards` (default) and `cameras-lenses`. `apply_sector()` in
   `src/valbot/config.py` deep-merges a sector's overrides over the neutral base. Wired into
   `run.py` and `targets.py`. The base config stays neutral so existing test fixtures hold.
3. **Two wrong assumptions fixed (in the sector profiles):**
   - `seller_type` private → **business**. Buying to resell with a third-party tool is
     business activity, and eBay only lets business sellers use such tools.
   - `sold_to_asking_ratio` 0.85 → **1.0**. Our comps are real sold prices, not asking.
   - FVF made category-specific: cards ~10.9%, cameras ~6.9% (CONFIRM on eBay's calculator).
   - Cameras sector is **GBP-only** (fx 1.0, no US sourcing), price_cap £600, profit_floor £40.
4. **Tests:** added `tests/test_sectors.py`. Full suite **38 passing**.
5. **Folder tidied:** research markdowns in `research/`, PDFs+HTML in `reports/`. Code,
   config, handoffs, README, CONTEXT, docs/ at root.

## The decision (build on this)
- Live data = **Browse API** (`--mode browse`, already coded). Finding API is dead (Feb 2025).
  RapidAPI scrapers unverifiable for UK auctions — stay closed.
- Sell **cameras/lenses first**, **graded cards second**. Value on clean identity, not category.
  Avoid watches, sneakers, fashion, Lego, books for an automated buyer.
- **Flip yourself.** Alert-SaaS market is crowded and moat-less. Maybe a paid tier much later.
- **Bad-listing arbitrage is real but narrow:** the edge is a seller hiding the identity
  signal (model suffix, cert, mount), not "bad photo = free money". Enforce
  high-confidence-or-no-bid (the existing gate already does this).

## Open issues / priority
1. **eBay keyset + compliance.** Ben applied. Once approved: complete the account-deletion
   notification step (can opt out — read-only tool stores no user data), create production
   keyset (App ID + Cert ID), add as repo secrets, run `--mode browse`. This is the live-data
   unblock. NB: the deletion-notification endpoint is the one real hoop.
2. **Self-test the Browse auction fields.** No public raw JSON proves a live ebay.co.uk
   auction returns `currentBidPrice`/`bidCount`/`itemEndDate`. Pull one real GB auction and
   check before trusting it. Docs + eBay staff say it works; verify anyway.
3. **No UK sold-comp source for cameras.** Card API is US/cards-only; eBay sold data is gated.
   This is THE open gap for the cameras lane. A short targeted search may be worth it; otherwise
   resolve during build (options: Browse active-listing comps as a proxy, or a sold-data provider).
4. **Cameras need exact-model title matching.** Current matcher is slab-oriented (grade regex +
   tokens). Build model-number extraction before running the cameras sector live.
5. Carried: rotate the exposed RapidAPI key; the workflow schedule should stay disabled until
   Browse is wired (it still runs `thirdparty`).
6. FVF + ratio are starting points — confirm FVF on eBay's calculator, calibrate ratio from
   real outcomes.

## Tasks for Ben
1. Finish eBay developer approval. Tell Claude when the keyset's ready.
2. Push session-6 changes via Claude Code (Cowork GitHub connector is read-only). Changed:
   `config.yaml`, `src/valbot/config.py`, `run.py`, `targets.py`, `tests/test_sectors.py`,
   plus new `research/` and `reports/` folders. (Decide if research/reports go in the repo or
   stay local — they're docs, not code.)
3. Run the `research/RESEARCH-what-to-sell.md` prompt was already run; results are saved. No
   new research needed right now.

## Tasks for Claude (next session)
1. When the keyset lands: set up the account-deletion notification endpoint, wire
   EBAY_APP_ID/EBAY_CERT_ID, switch live source to Browse, self-test a GB auction.
2. Build the cameras lane: exact-model matching + a UK sold-comp source (resolve gap #3).
3. Calibration script once real outcomes exist.
4. Tighten title matching once the first real week shows mismatches.

## How to run (current)
```bash
python targets.py --watchlist data/watchlist.example.csv --mode mock                 # cards (default)
python targets.py --watchlist my_cams.csv --sector cameras-lenses --mode mock        # cameras
python run.py --mode browse --sector graded-cards                                    # live (needs eBay keys)
```

## Opening message to paste next time
Picking the eBay valuation bot back up. Read OUTPUTS/eBay Valuation Bot/HANDOFF-session-6.md,
then CONTEXT.md and the ADRs. Research is done: Browse API for data, pivot to cameras/lenses
(cards secondary), flip myself. Sector switching + the fee/ratio fixes are built, 38 tests green.
My eBay developer status: [approved? keyset ready?]. If yes, wire Browse + self-test a GB auction.
Then build the cameras lane (exact-model matching + a UK sold-comp source). Keep it read-only.
