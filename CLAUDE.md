# valbot — working notes for Claude

## API budget (READ THIS BEFORE ANY LIVE RUN)
- **RapidAPI "eBay Average Selling Price" (sold feed) is capped at 50 pulls/month.** Be cautious.
- **1 pull = 1 `findCompletedItems` call = 1 model's sold comps.** The min/median/max/average
  stats come back in that SAME response — capturing them costs **zero** extra pulls.
- **pulls = (unique models valued) × (runs).** With 5 camera niches, one full run ≈ 5 pulls,
  so the 50/month budget = ~10 full runs per month, total.
- The `*/20 * * * *` cron in `.github/workflows/valbot.yml` (~2,160 runs/month) would blow the
  budget in under an hour. Do NOT let the sold feed run on that cron without caching + throttling.
- Prefer: cache sold comps (sold medians are stable day-to-day; reuse within ~7 days = 0 pulls),
  and run the sold feed manually / on-demand, not on the 20-min schedule.

## Implemented budget protection (src/valbot/cache.py)
- `SoldFeedCache` caches the sold feed for `cache_days` (30) and enforces
  `monthly_pull_budget` (50) via a monthly ledger. Both config'd on the cameras
  `thirdparty.sold` endpoint. Cache hit = 0 pulls; over budget = BudgetExceeded
  (callers degrade to "no fresh data", never crash/overspend).
- State lives in `data/cache/{sold_cache,pull_ledger}.json`, committed back by the
  workflow so it survives ephemeral Actions runs.
- Scatter scanner: `python scan.py --sector cameras-lenses --mode thirdparty` ranks
  niches by sold-price differentiation (rel-dispersion × √n). Warm cache = 0 pulls.
  Appends to `data/scatter_history.json`.

## Secrets
- The workflow reads env `RAPIDAPI_KEY` from `secrets.RAPIDAPI_KEY` (valbot.yml). One RapidAPI
  account key works across all subscribed APIs, so the live + sold feeds share it. The repo
  secret must be named `RAPIDAPI_KEY` (matches config `secret("RAPIDAPI_KEY")` and README).
</content>
</invoke>
