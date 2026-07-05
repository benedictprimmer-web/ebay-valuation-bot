# valbot

valbot watches eBay UK for used cameras selling below what they're worth and sends a WhatsApp when it finds one. It never bids and never spends money. It tells you the most it would pay and why; you decide.

It began as a valuation engine for graded sports cards and now runs on cameras and lenses.

## What it does

The same camera model sells for very different prices on eBay, depending on how the listing is written, when it ends, and whether the seller knows what they have. A Nikon D610 that usually goes for about £256 has sold for as little as £103. That spread is the opportunity: buy near the bottom of the range and the camera is still worth the middle.

![How scattered each niche's sold prices are](docs/figure-range.svg)

Each bar is one model, drawn from the cheapest it sold for to the dearest. The gap between the cheap sales and the typical sale is the room to make money. valbot watches the niches where that gap is biggest and most consistent. Right now that's 30 camera bodies and 10 lenses.

## How it works

Once an hour, for each model it watches, valbot:

1. Pulls what's buyable now: auctions ending within 48 hours, plus Buy-It-Now listings you can grab at any time. Both come from eBay's free Browse API.
2. Values each one against what that exact model actually sold for recently. These are real completed sales, not asking prices.
3. Works out the most it would pay, after eBay fees and postage both ways, using the low end of the price range rather than the average.
4. Sends a WhatsApp if the current price is below that number.

It skips listings it shouldn't recommend: broken or "for parts" bodies, sellers below 98% positive feedback, and bodies whose listing states a high shutter count. When a listing gives its real postage cost, that figure goes into the maths instead of an estimate.

### How it decides what a camera is worth

valbot never trusts a single price. For each model it builds the full spread of recent sales and bids against the safe, low end of it. Two things set its confidence: how many past sales it found, and how tightly they agree. A model with lots of consistent sales gets close to a full bid. A thin or scattered one gets a low bid, or no alert at all. Uncertainty lowers the price rather than appearing as a separate warning.

Sold data from eBay is messy, so it's cleaned first. New and boxed items, multi-item bundles, and parts/repair units are dropped, and only exact-model matches are kept. For a lens niche the cleaning is looser, because a zoom is still a lens and a "kit lens" is the item itself, so real comps aren't thrown away.

### What an alert looks like

```
🏷️ Underpriced listing
Sony A6000

Current bid: £139.95
MAX BID:     £191.07   (headroom £51.12)
Exp. profit: £103.98  ·  margin 37%
Condition:   Used  ·  seller 99% (2130)

Conservative value: £300.00
Confidence: high (0.80)  ·  n=14 sold comps

https://www.ebay.co.uk/itm/...
Read-only alert. You place the bid.
Rate it → reply "24fa4f good" or "24fa4f bad – why".
```

You get the most you should pay, the expected profit after fees, the bot's confidence, the item link, and a short code for rating it. You place every bid yourself.

## Teaching it

Every alert carries a short code. Record your verdict and it tunes the model:

```bash
python verdict.py 24fa4f bad --fair 240 "scuffed, comps look boxed"
```

`calibrate.py` folds those verdicts in and reports where your judgement disagrees with the bot, for example "on the A6000 your fair price is 0.78× ours, so we're overvaluing it." That signal arrives without waiting for a resale to complete. A summary at 7pm lists the day's alerts with their codes so you can rate them in one batch, and a digest lands on Sunday.

The reply path is still manual. CallMeBot only sends messages, so for now verdicts are relayed through a second chat session (`prompts/PROMPT-verdict-intake.md`). A Telegram bot would close the loop automatically; see `docs/plan-labelling-stage.md`.

## Running it

```bash
pip install -r requirements.txt

python run.py --mode mock                                 # sample data, prints, no keys
python run.py --mode hybrid --sector cameras-lenses       # live: free auctions + cached sold prices
python scan.py --sector cameras-lenses --mode thirdparty  # rank niches by bargain-room
python -m pytest -q                                       # 106 tests
```

Modes: `mock` (built-in fixture), `thirdparty` (RapidAPI), `browse` (eBay Browse), `hybrid` (Browse auctions valued against cached sold comps, which is the live route).

### Keys

The bot runs on GitHub Actions, so keys live as repository secrets (Settings → Secrets and variables → Actions), never in the code.

| Secret | For | Where to get it |
|---|---|---|
| `RAPIDAPI_KEY` | Sold prices | Subscribe to "eBay Average Selling Price" on rapidapi.com |
| `EBAY_APP_ID` / `EBAY_CERT_ID` | Live auctions | Free developer account at developer.ebay.com |
| `CALLMEBOT_PHONE` / `CALLMEBOT_APIKEY` | WhatsApp alerts | WhatsApp `+34 644 51 95 23` with the text "I allow callmebot to send me messages" |

Until CallMeBot is set up, alerts print to the run log, so nothing breaks if you add the keys later. Kill switch: disable the workflow in the Actions tab and nothing runs.

Scheduled workflows:

| Workflow | Schedule | Job |
|---|---|---|
| `live-cameras.yml` | hourly | the live watcher |
| `daily-summary.yml` | 7pm UK | the day's alerts as a rating worksheet |
| `weekly-digest.yml` | Sunday evening | weekly summary |
| `scan.yml` | daily | niche scatter scan |

GitHub cron runs on UTC and does not follow British Summer Time, so the two evening jobs shift by an hour when the clocks change.

## Cost

Two feeds. Live auctions from eBay Browse are free with no meaningful limit. Sold prices come from a metered RapidAPI feed capped at 50 lookups a month. Sold prices barely move week to week, so each model's result is cached for 30 days, which works out to roughly one lookup per model per month and keeps 40 niches under the cap.

Two guards make an overspend impossible: a monthly ledger (a hard 50) and a per-run cap (`max_pulls_per_run`, 12) so one cold-cache run can't drain the month. If the feed is unavailable, a run skips that model rather than failing. The provider is set in `config.yaml`, so a backup can be swapped in without touching code; the options are listed in `docs/analysis-quality-condition.md` and the ADRs, with eBay Marketplace Insights as the intended long-term source.

## Layout

```
config.yaml            every tunable: niches, fees, thresholds, budget, gates
run.py                 hourly live run, daily summary, weekly digest
scan.py                niche scatter scanner
verdict.py             record a human good/bad verdict on an alert
calibrate.py           check predictions against verdicts and real outcomes
src/valbot/
  valuation.py         price distribution and conservative value
  fees.py              eBay fee model and max-bid solver
  camera.py            messy listing title to exact model, plus shutter count
  ebay_client.py       data sources and the quality / seller / condition gates
  cache.py             30-day sold cache and monthly budget guard
  summary.py           daily and weekly WhatsApp summaries
  store.py             alert log, human verdicts, observations
  alert.py             CallMeBot WhatsApp
data/
  cache/               cached sold prices and the monthly ledger
  outcomes.json        logged alerts, human verdicts, real results
  observations.jsonl   every assessment, for later analysis
.github/workflows/     live-cameras, daily-summary, weekly-digest, scan
```

## Notes

Read-only by design: valbot finds and explains, you decide and buy. The reasoning behind each design decision is recorded in [CONTEXT.md](CONTEXT.md) and [docs/adr/](docs/adr). Notes for picking the project back up are in the `HANDOFF-*.md` files.
