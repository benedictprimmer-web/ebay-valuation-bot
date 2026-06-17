# HANDOFF — eBay Valuation Bot, after session 4
Date: 2026-06-17. Read this first next time. Current state of truth.

## Where we are in one line
The code is on GitHub and the mock run is green, but the live auction feed is still unsolved — the RapidAPI provider Ben bought turned out to be a Buy-It-Now scraper with no auction data, so we're pausing the live hunt, going big on the sold side, and building a semi-manual valuation loop that works this week.

## What changed this session

1. **The repo is finally on GitHub** — `benedictprimmer-web/ebay-valuation-bot`. It was empty (session-2's "pushed" never landed). The Cowork GitHub connector is **read-only** (every write returns 403), so Claude couldn't push or open a PR. Ben pushed it from Claude Code instead, which uses his own write credentials.
2. **Mock workflow run #2 = green.** Wiring proven end to end on GitHub's runner, no keys needed. The pipeline runs.
3. **Secrets fixed.** On GitHub: `CARDAPI_KEY` (correct) and `EBAY_LIVE_API` (holds the RapidAPI key — Ben named it differently). Rather than rename, the workflow now maps `RAPIDAPI_KEY: ${{ secrets.EBAY_LIVE_API }}` (valbot.yml line 36, pushed and confirmed on main).
4. **The live provider is a dead end.** Ben subscribed to "Real-Time eBay API" by *uniquebyofficial* on RapidAPI. Full response inspected: it's an ebay**.com** search-results scraper. Every `time.timeLeft` / `time.timeEnd` / `endDate` is empty, `bidsCount` is always 0, and prices are USD *ranges* (`from`/`to`). It gives no auction end time, no current bid, no GBP. It cannot drive an auction-sniping bot. No config mapping fixes missing data.
5. **eBay's own Browse API has the right data but is gated.** Per eBay's docs, production Buy API access needs approval and a signed contract — the exact gatekeeper the project went third-party to avoid (ADR-009 / D1). Not a quick win.
6. **OpenWeb Ninja** (the provider the config's `live` block was originally written for) lists eBay "Listings & Auctions" as **coming soon** — unconfirmed it returns auction data, so not worth subscribing to on spec.

## Decision taken this session
Stop forcing a cheap live source. Instead:
- **Go big on the sold side** (Card API works, tested) and **build Option 3** — a semi-manual valuation loop: Ben hands the bot a short list of cards he's watching, it values each against real Card API sold comps and returns max bid / margin / confidence. Ships a working tool this week, proves the valuation on real data, generates calibration numbers.
- **Run two deep-research efforts** to find a viable live auction-data source (prompts written this session: `RESEARCH-chatgpt-api-sweep.md`, `RESEARCH-grok-social.md`).
- **Apply for eBay Browse access in the background** — lower priority. Ben would rather not depend on eBay if another source exists.

## Blockers / open issues (priority order)
1. **No live auction feed.** This is THE problem. uniquebyofficial rejected. Waiting on research to surface a provider that returns UK auctions with current bid + end time, affordably. Until then the bot can't auto-poll auctions.
2. **Scheduled runs will go red.** The workflow runs `thirdparty` every 20 min and will fail until a live source is wired. Recommend disabling the schedule (Actions → valbot → ··· → Disable workflow) until then.
3. **Exposed key.** The RapidAPI key was shown in a screenshot during setup. Rotate it on RapidAPI and update the `EBAY_LIVE_API` secret. Low stakes, do it when tidying.
4. **config.yaml `live` block is wrong for any real provider.** It still targets OpenWeb Ninja's shape (host `real-time-ebay-data1.p.rapidapi.com`, `buying_format: auction`, `time_left`). Rewrite once research picks a provider.
5. fx.usd_to_gbp = 0.79 placeholder; US comps ≠ UK resale value (carried over).

## TASKS FOR BEN
1. Run the two research prompts — `RESEARCH-chatgpt-api-sweep.md` in ChatGPT, `RESEARCH-grok-social.md` in Grok. Paste findings back next session.
2. Disable the valbot workflow schedule to stop the red 20-min runs.
3. (Tidy) Rotate the exposed RapidAPI key; update `EBAY_LIVE_API`.
4. (Background) Decide whether to apply for eBay Browse access. Steps: register free at developer.ebay.com → create a keyset (gives App ID + Cert ID) → apply for Buy API → Browse production access via their form → agree to the API license. Form + wait, not hard.

## TASKS FOR CLAUDE (next session)
1. **Build Option 3** — semi-manual targets mode. A small input list of cards (JSON or CSV) → fetch Card API sold comps → output max bid, margin, confidence, comp count. Reuse the existing valuation/threshold/fees code. Then Ben pushes via Claude Code.
2. **Wire the live source** once research returns a viable provider: rewrite the `live` block (host, query param, extra params, items_path, field paths incl. ends_at, currency), test the parser.
3. Calibration script once outcomes.json has real results (carried over).
4. Tighten title matching if the first real week shows mismatches (carried over).

## Decisions locked (build on these)
- Read-only only, no bidding (ADR-002).
- Sold comps = The Card API (works).
- Two-source split (ADR-010) holds in principle, but the LIVE provider is unresolved. uniquebyofficial is rejected.
- Live auction data is the project's hard problem — treat finding it as the main task, not a detail.

## Files touched this session
- `.github/workflows/valbot.yml` (line 36: RAPIDAPI_KEY ← EBAY_LIVE_API)
- `HANDOFF-session-4.md` (new)
- `RESEARCH-chatgpt-api-sweep.md` (new — deep research prompt)
- `RESEARCH-grok-social.md` (new — deep research prompt)

## Opening message to paste next time
Picking the eBay valuation bot back up. Read OUTPUTS/eBay Valuation Bot/HANDOFF-session-4.md, then CONTEXT.md and the ADRs — locked plan, build on it. The code's on GitHub and the mock run is green. The live auction feed is the open problem; the RapidAPI provider I bought was a dud (no auction data). Here's what the research turned up: [paste ChatGPT + Grok findings]. Build Option 3 (the semi-manual valuation loop) so I have a working tool, and wire the live source if the research found one. Keep it read-only.
