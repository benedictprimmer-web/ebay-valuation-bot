# HANDOFF — eBay Valuation Bot, after build session 2

_Date: 2026-06-16. Read this first next time. It's the current state of truth._

## Where we are in one line

The bot is built and tested (21 passing tests). It runs read-only against built-in
mock data right now with no keys. To go live you pick a data provider, do two activation
steps, and paste in keys. No bidding anywhere in it, by design.

## What this is

A read-only bot that values graded football cards from comps, subtracts every cost, and
WhatsApps you when a live auction is underpriced. You place every bid yourself. The
locked plan is in CONTEXT.md and docs/adr/ (ADR-001 to ADR-009). Don't relitigate those
decisions, build on them.

## What's built and working

The whole pipeline runs end to end: poll auctions ending soon, pull comps for each card,
value it with uncertainty, gate on confidence, work out the max bid after fees, rank by
profit, send the alert, log the prediction.

- **Valuation engine** (`src/valbot/valuation.py`) — the core. Each card gets a range,
  not a number: point value, robust spread (MAD), comp count, a 0–1 confidence score,
  and a cautious value (`point_value − k×spread`) that every money decision uses. Thin
  or scattered comps shrink the bid or kill the alert on their own.
- **Fee model** (`src/valbot/fees.py`) — itemised, all-in. Defaults to your **private**
  account (£0 sell fees), with a business switch. Solves the max bid by working back from
  the floors.
- **Three data sources, one interface** (`src/valbot/ebay_client.py`) — `mock` (fixture,
  no keys), `thirdparty` (RapidAPI, the default live route, no eBay developer account),
  `browse` (official eBay API, free fallback). Swapping is a `--mode` flag.
- **Gate, ranking, alerts, logging** — confidence gate (≥8 comps, spread bound), rank by
  £ profit, WhatsApp via CallMeBot, state file to avoid repeat alerts, outcome log to
  calibrate later.
- **GitHub Actions cron** (`.github/workflows/valbot.yml`) — runs every 20 min, commits
  updated state back to the repo.
- **Visual** (`what-it-does.html`) — plain-English explainer with an interactive fee +
  bid example. Open it if you forget what any of this does.
- **21 tests** (`tests/`) — valuation, fees, full pipeline, third-party parsing.

## What changed this session (vs the first handoff)

1. **Fees fixed.** The first build modelled business-seller fees. You're private, so it
   now defaults to £0 sell fees. Haaland's max bid went £37.15 → £49.60 as a result.
   Business stays available behind `seller_type: business` for if you get reclassified.
2. **Data source switched to third-party as default.** The official Browse API needs the
   developer-account approval you hit. RapidAPI gives live search + real sold prices with
   no eBay account, so it's now the default. Official API kept as a free fallback.
   Recorded in ADR-009. Sold prices also remove the guessed asking-to-sold ratio, which
   was the weakest part of the valuation.
3. **Corrected two myths.** The developer account is unrelated to seller fees. And the
   Browse API uses an app token, not the per-user OAuth Gemini described.

## Open decisions / unknowns

- **Which RapidAPI provider.** Several do both live search and sold listings. Not yet
  chosen. Picking one is a [BEN] step (it needs a card on file). The code is provider-
  agnostic: host, two endpoint URLs, and four field paths live in `config.yaml`.
- **Placeholder thresholds.** 25% margin, £15 profit, £50 price cap, 0.85 ratio. These
  are starting guesses to calibrate from real logged outcomes, not settled numbers.
- **Title matching is approximate.** Grader and grade are parsed strictly; player/set
  come from the search query and must appear in the title. Fine for v1, worth watching
  in the first live week. First thing to tighten if alerts look mismatched.

## TASKS FOR YOU [BEN] — in order

1. **Push the repo.** You made it already. From the project folder:
   `git init && git add . && git commit -m "valbot v1" && git remote add origin <your-repo> && git push -u origin main`.
2. **Pick a RapidAPI eBay data API.** Sign up at rapidapi.com, search "eBay", subscribe
   to one that returns both live search and sold listings. Grab your key. Note the host
   and a sample response — I need the response shape to finish the mapping (see my tasks).
3. **CallMeBot activation.** From your phone, add +34 644 51 95 23, message it
   `I allow callmebot to send me messages`, save the API key it replies with.
4. **Add repo secrets** (Settings → Secrets and variables → Actions): `RAPIDAPI_KEY`,
   `CALLMEBOT_PHONE`, `CALLMEBOT_APIKEY`. (Add `EBAY_APP_ID` / `EBAY_CERT_ID` only if you
   ever use the official-API fallback.)
5. **Smoke test.** Actions → valbot → Run workflow → `mock`. Proves the workflow with no
   API spend. Then run `thirdparty` once your key's in.
6. **Run read-only for a week.** Alerts fire, you bid nothing. As auctions resolve, fill
   the `result` fields in `data/outcomes.json` (won/lost, final price, what it resold
   for). That's the calibration data.

## TASKS FOR ME [CLAUDE] — next session

1. **Confirm the field mapping** against your chosen provider's real sample response.
   Set `thirdparty.api_host`, the two endpoint URLs, and the four field paths in
   `config.yaml`. Test the parser against a saved copy of their JSON. This is the one
   bit that needs a real response to finish.
2. **Calibration script.** Once `outcomes.json` has real results, build a small tool that
   reads it, compares predicted cautious value vs actual sold, and suggests an updated
   sold-to-asking ratio and tighter floors. Currently the loop is manual.
3. **Tighten title matching** if the first live week shows mismatches — stricter
   player/set parsing, maybe a per-card allowlist.
4. **Confirm fee rates** against eBay's live calculator at go-live (rates were checked
   2026-06-16; private £0 sell fees, business 12.8% + £0.40 + 0.35% + VAT).
5. **Decide on bidding automation** — only after the read-only week proves the valuation
   tracks reality. Separate decision, own ToS weight (ADR-002). Not part of v1.

## Risks to keep in mind

- **Reclassification.** Regular buy-to-resell can get your private account flagged as a
  business by eBay/HMRC, which adds the business fees. If that happens, flip
  `seller_type` and the maths adjusts.
- **Provider dependency.** If the RapidAPI provider goes down or hikes prices, switch
  config or fall back to `--mode browse`. Cheap to reverse.
- **Calibration is unproven.** Until real outcomes are logged, treat alerts as a signal
  to check, not gospel. That's the whole point of the read-only week.

## Opening message to paste next time

> Picking the eBay valuation bot back up. Read OUTPUTS/eBay Valuation Bot/HANDOFF-session-2.md,
> then CONTEXT.md and the ADRs — that's the locked plan, build on it, don't relitigate.
> I've [pushed the repo / picked a RapidAPI provider — here's the host and a sample
> response / done CallMeBot / added secrets]. Finish the field mapping in config.yaml
> against the provider response, smoke-test it, and tell me the exact next step. Keep it
> read-only. No bidding.
