# HANDOFF — eBay Valuation Bot, after session 5
Date: 2026-06-17. Read this first next time. Current state of truth.

## Where we are in one line
Option 3 is built and green — you can hand the bot a watch list of cards and it values
each against real Card API sold comps, returning max bid / margin / confidence / comp
count. The live auction feed is still the open problem (unchanged from session 4); no
research findings were pasted this session, so nothing new was wired.

## What changed this session
1. **Built targets mode (Option 3).** New CLI `targets.py` + module `src/valbot/targets.py`.
   You give it a watch list (CSV or JSON) of cards; it fetches Card API sold comps,
   values each, and prints a verdict per card. Reuses the existing valuation, gate, fee
   and threshold code unchanged — it only swaps the live poll for your list.
2. **Verdicts:** `BID` (under max bid, clears floors, with headroom), `SKIP` (over max
   bid / cap / floor), `LOW CONFIDENCE` (gate failed — thin or scattered comps),
   `NO DATA` (no comps), `MAX BID` (no price given — informational).
3. **Watch-list format:** `player, set_name, variant, grader, grade, current_price`.
   `variant` defaults to `base`; `current_price` optional. Column aliases accepted
   (`set`→`set_name`, `price`/`current`→`current_price`). Sample at
   `data/watchlist.example.csv`.
4. **Output:** clean console table + JSON to `data/targets_results.json` (gitignored) so
   it can feed calibration later.
5. **Tests:** added `tests/test_targets.py` (10 tests). Full suite green — **33 passed**.
6. **Docs:** README has a new "Targets mode" section + updated layout. This handoff added.
7. **No live wiring.** You didn't paste ChatGPT/Grok research findings, so there was no
   viable provider to wire. The `config.yaml` `live` block is untouched (still wrong for
   any real provider — see blocker 4).

## How to use it
```bash
# real comps (needs CARDAPI_KEY in env):
python targets.py --watchlist my_cards.csv
# test on the fixture, no keys:
python targets.py --watchlist data/watchlist.example.csv --mode mock
```
Targets mode needs **only** `CARDAPI_KEY`. No live/RapidAPI key required.

## Blockers / open issues (priority order)
1. **No live auction feed.** Still THE problem. uniquebyofficial rejected (session 4).
   Waiting on the two research prompts to surface a UK-auction provider with current bid
   + end time. Until then the *auto-poll* pipeline can't run; targets mode is the stopgap.
2. **Scheduled runs still go red.** The `valbot` workflow runs `thirdparty` every 20 min
   and fails with no live source. Disable the schedule (Actions → valbot → ··· → Disable
   workflow) — carried over from session 4, confirm it's done.
3. **Exposed RapidAPI key** — rotate it, update `EBAY_LIVE_API` secret (carried over).
4. **config.yaml `live` block wrong** for any real provider (still OpenWeb Ninja shape).
   Rewrite once research picks a provider (carried over).
5. **fx.usd_to_gbp = 0.79 placeholder.** Card API returns USD; US sold comps ≠ UK resale
   value. Watch this — targets mode inherits it. Calibrate against real UK outcomes.
6. **Stale duplicate folder.** `ebay-valuation-bot/` (nested), plus `ebay-valuation-bot.zip`,
   `ziIP2TLr`, `push-to-github.sh` are a stale zip snapshot from session 3. The nested copy
   does NOT have session-4/5 changes and breaks `pytest` collection (duplicate test module
   names). Safe to delete all four — the top-level folder is the only live copy. Run pytest
   with `--ignore=ebay-valuation-bot` until they're gone.

## Tasks for Ben
1. **Push session-5 changes via Claude Code** (Cowork GitHub connector is read-only).
   New/changed files listed below.
2. Run the two research prompts (`RESEARCH-chatgpt-api-sweep.md`, `RESEARCH-grok-social.md`)
   and paste findings next session so the live source can be wired.
3. Try targets mode on a few cards you're actually watching: build a CSV, run
   `python targets.py --watchlist your.csv`, sanity-check the max bids against your gut.
4. Delete the stale nested folder + zip/junk (blocker 6) when tidying.
5. Carried over: disable the workflow schedule; rotate the exposed key.

## Tasks for Claude (next session)
1. Wire the live source IF research returns a viable provider: rewrite `config.yaml` `live`
   block (host, query param, extra params, items_path, field paths incl. `ends_at`,
   currency), test the parser.
2. Calibration script once `outcomes.json` (or `targets_results.json` + real outcomes) has
   real results — fit the sold-to-asking ratio and tune the floors (carried over).
3. Tighten title matching if the first real week shows mismatches (carried over).
4. Consider logging targets-mode runs into a history file for calibration, not just
   overwriting `targets_results.json`.

## Decisions locked (build on these)
- Read-only only, no bidding (ADR-002).
- Sold comps = The Card API (works, tested).
- Targets mode (Option 3) is the working tool until a live feed exists.
- Live auction data is the project's hard problem — finding it is the main task.

## Files touched this session
- `targets.py` (new — CLI entry for targets mode)
- `src/valbot/targets.py` (new — watch-list load + per-card assessment)
- `src/valbot/formatting.py` (added `format_targets`, `target_to_dict`)
- `tests/test_targets.py` (new — 10 tests)
- `data/watchlist.example.csv` (new — sample watch list)
- `.gitignore` (ignore `data/targets_results.json`)
- `README.md` (Targets mode section + layout)
- `HANDOFF-session-5.md` (new)

## Opening message to paste next time
Picking the eBay valuation bot back up. Read OUTPUTS/eBay Valuation Bot/HANDOFF-session-5.md,
then CONTEXT.md and the ADRs — locked plan, build on it. Targets mode (Option 3) is built
and green; I've been using it on my watch list. The live auction feed is still the open
problem. Here's what the research turned up: [paste ChatGPT + Grok findings]. Wire the live
source if the research found one. Keep it read-only.
