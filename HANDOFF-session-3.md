HANDOFF — eBay Valuation Bot, after build session 3
Date: 2026-06-16. Read this first next time. Current state of truth.

# Where we are in one line
Comps side is done and wired to The Card API (real sold prices, tested). The live-auction
side is the one thing left to connect, and the chosen provider is "saying invalid" — that's
the first thing to fix. Mock pipeline green, 23 tests passing. Still read-only, no bidding.

# What changed this session (vs HANDOFF-session-2)

1. Picked the comps provider: The Card API (thecardapi.com). Trading-card native — parses
   player/set/grade, returns true sold prices including accepted Best Offer. Better than any
   generic eBay sold scraper, and it reduces the title-matching risk from session 2. Free tier:
   5,000 sales/day, 7-day lookback. Used direct (not via RapidAPI): cleaner, own key header.

2. Confirmed the feed has to be TWO sources, not one. Live listings and sold prices are
   separate products everywhere. So: sold/comps = The Card API; live/targets = a RapidAPI
   eBay source. This is the right architecture, not a compromise. Logged as ADR-010.

3. Wired The Card API into the bot and tested it:
   - config.yaml `thirdparty.sold` now points at The Card API with field mapping confirmed
     against their published response schema (id, title, price, listing_url under `data`).
   - Per-endpoint auth added: each endpoint carries its own `auth` block, so the sold source
     uses `x-market-api-key` (CARDAPI_KEY) while the live source uses RapidAPI headers
     (RAPIDAPI_KEY). Neither needs the other's key to run.
   - USD->GBP conversion added. The Card API returns USD; bot reasons in GBP. New `fx.usd_to_gbp`
     in config (placeholder 0.79). Conversion happens at ingestion in ThirdPartySource._parse.
   - Tests went 21 -> 23: comps parse/filter test rewritten to The Card API's real shape;
     two new tests prove each source picks the right key.
   - GitHub workflow now passes CARDAPI_KEY through to the run step.

4. Corrected the CallMeBot number. Session-2 handoff said +34 644 51 95 23; CallMeBot's live
   site now lists +34 623 78 64 49. Use the number currently on callmebot.com.

# What Ben did this session
- Pushed the repo (session 2 task 1). Done.
- Got a The Card API key and added it to GitHub secrets as CARDAPI_KEY. Done.
- Subscribed to a live eBay API on RapidAPI ("Real-Time eBay API" by Best APIs) — but it's
  "saying invalid". Unresolved. See blockers.
- CallMeBot: in progress (was told to send the exact phrase "I allow callmebot to send me
  messages" — confirm the API key actually came back).

# Blockers / open issues (in priority order)

1. Live source not connected. Ben subscribed to "Real-Time eBay API" (by Best APIs) on
   RapidAPI but the key/sub is "saying invalid". Could be: subscription still provisioning,
   wrong key copied, or testing against the wrong host. NEXT SESSION: get this working, then
   grab ONE sample response from its RapidAPI Results tab so the field mapping can be wired.
   Note: that provider's latency is ~28s (slow but fine for a 20-min cron). The config `live`
   block is currently a placeholder pointing at OpenWeb Ninja's shape — it WILL need rewriting
   to match whatever provider Ben actually keeps.

2. thirdparty can't run end-to-end yet. Needs: live source wired + RAPIDAPI_KEY added to GitHub
   secrets. Until then, only `mock` runs. (Claude's sandbox has no internet and can't trigger
   GitHub Actions, so the real thirdparty test must run on GitHub via the workflow's Run button.)

3. fx.usd_to_gbp = 0.79 is a placeholder. Bigger caveat: US sold comps are NOT the same as UK
   resale value. Watch this in the read-only week before trusting the converted figure.

4. The Card API free tier = 7-day lookback. Thin/obscure cards may not reach the 8-comp gate
   in 7 days (bot just won't alert — safe, but misses some). Starter ($19/mo, 30-day) fixes it
   if 7 days proves too short. Don't pay until the test week shows it's needed.

5. Key hygiene: the CARDAPI_KEY was pasted into chat during setup. Low stakes (free card-price
   key) but regenerate it on thecardapi.com if being tidy.

# TASKS FOR YOU [BEN] — in order
1. Fix the live eBay API subscription. On RapidAPI, confirm the subscription is active (not
   pending), copy the key from the API's "Header Parameters" / your Apps > Security page, and
   do one test search in its playground. If it works, copy the response from the Results tab and
   paste it to Claude. If still invalid, try a different eBay live provider — there are ~15.
2. Add RAPIDAPI_KEY to GitHub secrets (Settings > Secrets and variables > Actions). Same place
   you put CARDAPI_KEY.
3. Finish CallMeBot if not done: send the exact phrase from your phone, save the API key it
   replies with, add CALLMEBOT_PHONE and CALLMEBOT_APIKEY to GitHub secrets.
4. Smoke test on GitHub: Actions > valbot > Run workflow > mock (proves wiring, no spend). Then
   run thirdparty once the live source is wired.
5. Run read-only for a week. Bid nothing. Fill `result` fields in data/outcomes.json as auctions
   resolve. That's the calibration data.

# TASKS FOR CLAUDE — next session
1. Wire the live source against Ben's chosen provider's real sample response: set config `live`
   host, url, query param, extra params, items_path, and the field paths (title/price/id/url/
   ends_at). Confirm prices are GBP (query ebay.co.uk) or add conversion if not. Test the parser.
2. Sanity-check the end-to-end thirdparty path once both keys exist (Ben runs it on GitHub;
   read the result together).
3. Calibration script — once outcomes.json has real results: compare predicted cautious value
   vs actual sold, suggest a real fx rate and tighter floors. (Carried over from session 2.)
4. Tighten title matching if the first live week shows mismatches. (Carried over.)
5. Confirm fee rates against eBay's live calculator at go-live. (Carried over; private £0 sell
   fees still assumed.)

# Decisions locked (don't relitigate — build on them)
- CONTEXT.md + ADR-001..ADR-010. ADR-009 = third-party default. ADR-010 = the two-source split.
- Read-only only. No bidding in v1 (ADR-002).
- Comps = The Card API. Live = a RapidAPI eBay source (provider TBD until the "invalid" is fixed).

# Files touched this session
- config.yaml (thirdparty rewrite: per-endpoint auth + currency; new fx block)
- src/valbot/ebay_client.py (_headers_for, _auth_for, _key_for, _fx_factor; per-endpoint auth + USD->GBP)
- tests/test_thirdparty.py (real Card API schema + 2 auth tests; 21 -> 23)
- .env.example (added CARDAPI_KEY)
- .github/workflows/valbot.yml (passes CARDAPI_KEY)
- docs/adr/ADR-010-split-data-sources.md (new)

# Opening message to paste next time
Picking the eBay valuation bot back up. Read OUTPUTS/eBay Valuation Bot/HANDOFF-session-3.md,
then CONTEXT.md and the ADRs — locked plan, build on it, don't relitigate. The comps side (The
Card API) is wired and tested. The live eBay source on RapidAPI was "saying invalid" — I've
[fixed it / picked a different provider]; here's the host and a sample response from its Results
tab. Wire the live field mapping in config.yaml, test the parser, and tell me the exact next
step. Keep it read-only. No bidding.
