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

## Secrets
- The workflow maps env `RAPIDAPI_KEY` from `secrets.EBAY_LIVE_API` (valbot.yml). One RapidAPI
  account key works across all subscribed APIs, so live + sold can share it — but the repo
  secret NAME the workflow reads is `EBAY_LIVE_API`, not `RAPIDAPI_KEY`. Keep these in sync.
</content>
</invoke>
