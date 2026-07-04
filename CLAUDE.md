# valbot — working notes for Claude

## API budget (READ THIS BEFORE ANY LIVE RUN)
- **RapidAPI "eBay Average Selling Price" (sold feed) is capped at 50 pulls/month.** Be cautious.
- **1 pull = 1 `findCompletedItems` call = 1 model's sold comps.** The min/median/max/average
  stats come back in that SAME response — capturing them costs **zero** extra pulls.
- **pulls = (unique models valued, uncached) × (cache-miss events).** 20 camera niches, each
  cached 30 days ⇒ ~20 pulls/month (≤1 per model), well under 50.
- Two hard guards on the metered feed (config'd on the cameras `thirdparty.sold` block):
  `monthly_pull_budget: 50` (ledger ceiling) AND `max_pulls_per_run: 12` (burst cap so one
  cold-cache run can't drain the month). Over either → BudgetExceeded → caller degrades to
  "no fresh comps" and skips; never crashes, never overspends.
- HISTORICAL: the old `*/20` cron in `valbot.yml` was the budget landmine — it has been
  DELETED (2026-07). It was the abandoned cards lane (The Card API + a different RapidAPI
  product; it never touched the 50-cap camera feed) and had been failing since 17 Jun. The
  live lane is `live-cameras.yml` (hourly, `--mode hybrid`): free Browse auctions valued
  against cache-served sold comps ⇒ ~0 pulls/run once warm.

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

## Data capture (for calibration + keeping this running)
- `data/observations.jsonl` — append-only, EVERY assessment from every hourly live run
  (alerts AND skips): model, price, BIN, valuation, decision + reasons. `run.py --log-all`
  writes it; live-cameras.yml commits it back. The growing deal-flow dataset.
- `data/scatter_history.json` — one row per scan. scan.yml now runs DAILY (cron 06:30) so
  niche scatter builds a time series (cache-served, ~0 pulls after warmup).
- `data/outcomes.json` — alerts with predictions; fill `result` when a flip resolves →
  `calibrate.py` tunes the ratio/floors from reality.

## Two feeds — only ONE is metered
- SOLD comps (ebay-average-selling-price, 50/month) = valuation. Cached 30 days, so
  ~1 pull/model/month. The 20 camera niches = ~20 pulls/month.
- LIVE current auctions = a SEPARATE feed with its own quota. `--mode hybrid` gets these
  FREE from eBay Browse (EBAY_APP_ID/EBAY_CERT_ID) and values them against the cached sold
  comps. Running live hourly is ~free on the 50 budget: comps are cache hits.
- Camera targets now include BOTH pure auctions (ending within `ending_within_hours`, 48h)
  AND Buy-It-Now / fixed-price listings (snap-buyable any time, so the window doesn't gate
  them). `require_buy_it_now: false`. See `_fetch_camera_targets`.
- Modes: mock | thirdparty (RapidAPI live+sold) | browse (eBay live+active proxy) |
  hybrid (Browse auctions + cached sold comps — the cameras live route).
- Workflows: live-cameras.yml (hourly hybrid — the live lane), scan.yml (daily scatter
  scan). valbot.yml (old cards cron) was DELETED 2026-07.

## Secrets
- The workflow reads env `RAPIDAPI_KEY` from `secrets.RAPIDAPI_KEY` (live-cameras.yml). One RapidAPI
  account key works across all subscribed APIs, so the live + sold feeds share it. The repo
  secret must be named `RAPIDAPI_KEY` (matches config `secret("RAPIDAPI_KEY")` and README).
</content>
</invoke>
