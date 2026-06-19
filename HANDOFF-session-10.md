# HANDOFF — eBay Valuation Bot, after session 10

Date: 2026-06-19. Read this first next time.

## One line

The cameras lane is **read-only-ready**. Comps are clean (eBay category filter + price-floor backstop, session 9), the `ending_within_hours` window is now enforced in Browse mode (session 10), and 69 tests pass. The read-only week can start. The cards lane still needs a free `CARDAPI_KEY` before it has live comps.

## What changed this session (10)

1. **`ending_within_hours` is now enforced in Browse mode.** It was a dead config key — Browse returns results sorted by `endingSoonest` with no time cutoff, so auctions days away were surfacing as alerts (the £5.21 and £10.71 "deals" were a week out with one early bid). Added a module-level `ends_within()` helper (parses any ISO8601 form — `Z`, `+00:00`, or naive; boundary-inclusive; safe on None/bad input) and a one-line guard in `BrowseAPISource.fetch_targets` that drops anything outside the window. Cameras set to **24h** (room to bid by hand); base stays **6h** for the cards lane. Live result: **7 → 2 auctions assessed**, the week-out noise gone, the 2 remaining ending today and correctly priced. **69 tests passing.**

2. **Niche research saved + test watchlists created.** `research/niche-shortlist-cards-cameras.md` holds a deep-research shortlist (3–5 card niches, 3–5 camera niches) scored against seven target criteria. `data/watchlist.test-cameras.csv` and `data/watchlist.test-cards.csv` hold the test targets. **Honest read: the shortlist is blue-chips** — maximally liquid, but priced too efficiently to flip (see strategic note).

3. **`.env` clarified.** `python-dotenv` loading was wired in session 8 (`run.py`/`targets.py`, graceful try/except, gitignored). The real keys live in the repo's `.env`, where the live self-test passed. The `.env` in the Cowork working copy is a commented scaffold only — ignore it.

## Decisions locked

- **Comp quality (the session-9 fix): filter at the source by eBay category leaf, not title heuristics.** `category_ids` = `{body: "31388", lens: "3323"}` (31388 Digital Cameras, 3323 Camera Lenses leaf — NOT the 78997 Lenses & Filters parent, which contains hoods/filters). Browse takes one category per request, so it's a per-kind dict resolved from `card.kind` at query time. Plus a price-floor backstop (`comp_min_price: {body: 80, lens: 25}`) for anything that slips through. Chosen over the three title-heuristic options (blocklist / "for"-preposition / price floor) because it's structural and low-maintenance. **Candidate for ADR-012.** Commit `a4f56d6`.
- **Window: enforce `ending_within_hours` post-fetch in Browse** (`fetch_targets`). 24h cameras, 6h base.
- **Cameras valuation ratio 0.85** — Browse active-listing proxy (ADR-011). Reverts to 1.0 when the Apify sold feed is wired.
- **Read-only week runs both** the live poll (`run.py`) and the watchlist (`targets.py`).

## Strategic note (read this before picking targets)

**Blue-chip gear is priced too efficiently for this bot to flip.** Live numbers prove it: the A7 III conservative value is £639, so after the 25% margin the max bid is ~£401, but real A7 III auctions close at £680–900. Even with the price cap removed, the bot would never bid high enough to win one. The same pattern hits every most-watched item — tight live pricing means no bargains. **The bot's edge is one tier down:** less-watched gear and cards where live/auction prices are scattered enough that underpriced ones actually appear. Don't chase the obvious blue-chips; that's criterion 4 (loose live prices) and the shortlist scores weakest there.

## Open issues / priority

1. **`CARDAPI_KEY` still placeholder (Ben).** Cards lane has no live comps until it's set. Sign up at thecardapi.com (key starts `tca_`), add to `.env`. Mock-only until then.
2. **CallMeBot not set up (Ben).** `CALLMEBOT_PHONE` + `CALLMEBOT_APIKEY` placeholder; one-time WhatsApp activation (see README). Dry-run is mandatory until then.
3. **GitHub Actions schedule still disabled.** Enable only after CallMeBot is wired and a few clean read-only days have passed. The window blocker (was #1 last session) is now cleared.
4. **Fees are placeholders** — cards FVF ~10.9%, cameras ~6.9%, fixed £0.40, regulatory 0.35%. Not blocking read-only (no bids), but confirm against eBay UK's business-seller calculator before the first real bid.
5. **RF 50mm vintage-glass leak (minor).** The category filter removed accessories; what remains is real vintage/third-party 50mm glass (Pentacon, Canon M39) that parses as "Canon RF 50mm." Spread is only 14%, so the gate still holds. Fix later with model-suffix matching ("RF STM").
6. **A7 III price cap (£600) — leave it.** It skips real auctions, but per the strategic note the margin math already rules out the A7 III regardless. Not worth raising. Revisit per-model only if a cheaper, scattered niche needs a different cap.
7. **No outcomes logged yet.** All thresholds (ratio 0.85, FVF 6.9%, margin 25%, profit £40) are informed placeholders. The read-only week starts now that comps are clean and the window is enforced.

## Tasks for Ben

1. Get `CARDAPI_KEY` from thecardapi.com and add it to `.env` (unlocks the cards lane).
2. Activate CallMeBot and add the two keys to `.env` when you want real WhatsApp alerts.
3. Run the cameras lane read-only daily for ~a week (`python run.py --mode browse --sector cameras-lenses --dry-run`) and note what it flags.
4. Decide the real niches — and weight toward one tier down from the blue-chip shortlist, where bargains actually appear.

## Tasks for Claude (next session)

1. **Build the read-only-week outcome logging** — capture predicted vs actual (won/lost, final price, eventual resale) to `data/outcomes.json`, then wire the `calibrate.py` loop to set the sold ratio and floors from real data.
2. **Wire `CARDAPI_KEY`** into the cards lane once Ben has it; run the Card API check (verify endpoint, field paths, keyword matching, real comps come back).
3. **Write ADR-012** documenting the comp-quality fix (category filter + price floor) and the window enforcement.
4. **RF 50mm suffix matching** if the vintage-glass leak widens; revisit `price_cap` per-model only if a niche needs it.
5. **Enable GitHub Actions** once CallMeBot is wired and a few read-only days look clean.

## How to run (current)

```bash
python run.py --mode browse --sector cameras-lenses --dry-run                 # live cameras, no WhatsApp
python targets.py --watchlist data/watchlist.test-cameras.csv --sector cameras-lenses --mode browse
python run.py --mode browse --dry-run                                         # live cards (0 comps until CARDAPI_KEY)
python run.py --mode mock --dry-run                                           # cards, fixture only
python -m pytest -q                                                           # 69 passing
```

## Opening message to paste next time

Picking the eBay valuation bot back up. Read OUTPUTS/eBay Valuation Bot/HANDOFF-session-10.md, then skim CONTEXT.md and the ADRs. State: cameras lane is read-only-ready — comps are clean (category filter 31388/3323 + price-floor backstop), the `ending_within_hours` window is enforced (24h cameras), and 69 tests pass. Cards lane still needs a free `CARDAPI_KEY` before it has live comps; CallMeBot isn't wired so it's dry-run only; Actions stays disabled. Before doing anything, ask me: (1) did I get the `CARDAPI_KEY` into `.env`, and do you want to wire + check the cards lane? (2) have I run any read-only cameras days, and do we have outcomes to log? Then the priority is building the read-only-week outcome logging (predicted vs actual → `data/outcomes.json`) and the calibrate.py loop. Keep it read-only — no bids, no live WhatsApp until I say. Heads-up on targeting: the blue-chip shortlist is priced too efficiently to flip; aim one tier down.
