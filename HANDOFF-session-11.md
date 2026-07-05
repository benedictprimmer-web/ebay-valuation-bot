# HANDOFF — eBay Valuation Bot, after session 11 (orchestrator)

Date: 2026-07-05. Read this first next time. Then skim CLAUDE.md and the docs/ notes below.

## One line

The cameras lane is **live and working** — hourly runs now surface real deals (4 bargain
alerts today), screened for condition/seller/shutter/postage, and every alert can be
labelled good/bad to tune the model. 106 tests pass. Main is at `8bd4817`. The active work
now is **collecting human labels** (data-collection phase) before tuning.

## The arc of this session (what changed)

Started as a full audit; turned into getting the lane from "green but finding nothing" to
"live, screened, and self-improving." All merged to `main`.

1. **Fixed zero-deal-flow.** The hourly lane had assessed **0 auctions since launch**
   (`observations.jsonl` never created). Cause: filters far too tight (pure-auction-only ×
   require-Buy-It-Now × 24h × exact model). Loosened: auctions→48h AND Buy-It-Now/fixed-price
   are buyable **any time** (window only gates pure auctions); `require_buy_it_now: false`.
   Margins narrowed to profit_floor £12 / margin_floor 0.18. Result: lane went 0 → **4 real
   alerts today** (2× A6000 ~£104 profit, A7 II ~£74, D610 ~£87), 26/50 sold-pulls used.

2. **40 niches** (30 bodies + 10 first-party lenses). Parser gaps fixed (Canon M-series,
   2-digit Nikons like D90, Panasonic GX/GF/GM). Comp cleaning is now **kind-aware**:
   body-only excludes (zoom/kit/with-lens) don't gut lens comps.

3. **Budget hardened.** Added `max_pulls_per_run: 12` burst cap on top of the monthly
   ledger (50). Deleted the dead cards lane `valbot.yml` (was failing since 17 Jun, a `*/20`
   cron landmine). Live lane is `live-cameras.yml` (hourly hybrid).

4. **Quality / risk screening** (from Ben spotting a "parts not working" alert): capture
   `condition`, `conditionId`, seller feedback, and real per-listing postage from Browse.
   Drop broken/for-parts/faulty targets, spares-in-title, and sellers <98%. Shutter-count
   parsed from the title (unknown never penalises; skip auto-alert when a stated count is
   >70% of ~150k). Real postage feeds the profit/max-bid maths. Alert shows all of it.
   See `docs/analysis-quality-condition.md`.

5. **Human-in-the-loop feedback loop.** Every alert carries a quotable **ref code**;
   `verdict.py <ref> good|bad [reason] [--fair £]` records it; `calibrate.py` turns verdicts
   into per-niche "we're over/under-valuing" signals — an EARLY signal (no need to wait for a
   resale). The 7pm daily summary lists the day's alerts **with codes** so it doubles as a
   once-a-day batch-labelling worksheet.

6. **Summaries.** `daily-summary.yml` (18:00 UTC = 7pm BST) and `weekly-digest.yml`
   (Sun 18:00 UTC) — read logs only, 0 pulls, always send (dead-man's switch).

## Current state / decisions locked

- **Workflows on main:** `live-cameras` (hourly hybrid — the live lane), `daily-summary`
  (7pm), `weekly-digest` (Sun 7pm), `scan` (daily scatter). `valbot.yml` deleted.
- **Secrets all wired** (confirmed in run logs): EBAY_APP_ID/CERT, RAPIDAPI_KEY,
  CALLMEBOT_PHONE/APIKEY. WhatsApp alerts deliver.
- **Merge policy:** land via **local rebase + fast-forward to main** (committer stays
  `Claude <noreply@anthropic.com>` → no "Unverified" flag). Do NOT squash-merge via the
  GitHub UI (that re-authors the commit and trips the stop-hook). PR-create tooling was
  flaky this session; direct-to-main is the reliable path and Ben has authorised it.
- **Phase = data collection.** Keep alerts LOOSE on purpose (volume = signal). Do NOT
  tighten searches/floors yet; tune only after ~50 labels / ~5–10 per active niche.
- **Verdict channel:** a SEPARATE Claude session bootstrapped from
  `prompts/PROMPT-verdict-intake.md`. Simple good/bad labels for now. Telegram bot is the
  future upgrade (only worth it past ~15–20 alerts/day — not now).

## Open issues / priority

1. **Labels needed before any tuning.** `outcomes.json` has alerts but few/no
   `human_verdict`s yet. The whole next phase depends on Ben labelling ~2 weeks of alerts.
2. **DST caveat.** `daily-summary` and `weekly-digest` crons are `0 18` = 7pm BST now, but
   become 6pm GMT when clocks go back (~late Oct). Bump to `0 19` then. (live-cameras is
   hourly, unaffected.)
3. **Hourly self-check-in automation** never armed — the scheduler tool (create_trigger /
   send_later) needs a one-time approval that failed this session. Re-offer it.
4. **`outcomes.json.result` still empty** (won/final/resold). Realized-flip calibration
   waits on real purchases. Human verdicts are the interim signal.
5. **Backup sold feed (Marketplace Insights)** documented, not wired — Ben has an eBay dev
   account but Marketplace Insights is separately gated; apply so a fallback is ready.
6. **P2 (deeper quality):** fetch the item DESCRIPTION via Browse getItem for shortlisted
   candidates → parse shutter count / faults / accessories (title-only today misses most).
7. **Near-close auction alerting.** A fresh £1 auction with 47h left can fire a speculative
   alert then get bid up. Consider only alerting pure auctions near close, or tagging them.

## Tasks for Ben

1. **Start the verdict channel** — new Claude session on the repo, paste
   `prompts/PROMPT-verdict-intake.md`. Then label the day's alerts once a day (from the 7pm
   summary). Label ALL of them — the 👎s are the most informative.
2. Optionally apply for **eBay Marketplace Insights** (backup sold feed).
3. Decide if/when to add the **Telegram bot** (only if daily labelling gets tedious).

## Tasks for Claude (next session)

1. **When ~50 labels are in:** run the Phase-2 analysis (see `docs/plan-labelling-stage.md`)
   — per-niche 👎 rate + your-fair-vs-our-value + reason-coding — and propose ONE lever at a
   time (per-niche ratio, quality gates, or floors). calibrate.py suggests; Ben approves.
2. **Re-offer the hourly check-in automation** (needs Ben to approve the scheduler once).
3. **P2 description-fetch** for shutter/condition once label data shows quality is a frequent
   👎 reason.
4. **DST:** flip the two digest crons to `0 19` when the UK clocks go back.
5. Only tighten alerts when the data says so — not before.

## How to run (current)

```bash
python run.py --mode hybrid --sector cameras-lenses --dry-run        # live cameras, no WhatsApp
python run.py --sector cameras-lenses --daily-summary --dry-run      # the 7pm batch worksheet
python run.py --sector cameras-lenses --weekly-digest --dry-run      # Sunday digest
python verdict.py <ref> good|bad [reason] [--fair £]                 # record a human verdict
python calibrate.py                                                  # tuning report incl. human verdicts
python scan.py --sector cameras-lenses --mode thirdparty            # niche scatter (cached)
python -m pytest -q                                                  # 106 passing
```

## Opening message to paste next time (orchestrator)

Picking the eBay valuation bot back up. Read HANDOFF-session-11.md first, then skim
CLAUDE.md, docs/analysis-quality-condition.md and docs/plan-labelling-stage.md. State: the
cameras lane is LIVE (hourly, ~4 real alerts/day, 26/50 sold-pulls), 40 niches, screened for
condition/seller/shutter/postage, and every alert is labellable good/bad via verdict.py →
calibrate.py. Main is at 8bd4817, 106 tests pass. We are in the DATA-COLLECTION phase: keep
alerts loose, do NOT tune yet. Merge policy: local rebase + fast-forward to main, never
squash via the UI. Before doing anything, ask me: (1) how many human labels have accumulated
(python calibrate.py), and are we at ~50 / ~5+ per niche yet? (2) do I want the hourly
check-in automation armed, and should we bump the digest crons for DST? If we have enough
labels, run the Phase-2 analysis in docs/plan-labelling-stage.md and propose ONE tuning lever
for my approval. Otherwise keep collecting. No bids, ever — read-only.
```
