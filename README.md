# valbot — eBay valuation bot (read-only)

Values graded sports cards from active eBay listings and WhatsApps you when one's
underpriced after every fee. It never bids. You confirm and place every buy yourself.

The decisions behind it are locked in [CONTEXT.md](CONTEXT.md) and [docs/adr/](docs/adr).
This README is how you run it and what you need to plug in.

## What it does, in one pass

Poll auctions ending soon, gather comps for each card, value it, gate on confidence,
work out the most you should pay, rank survivors by expected profit, send a WhatsApp.
Then log the prediction so you can check it against reality later.

```
poll → match comps → value (with uncertainty) → gate → max bid → rank → alert → log
```

## The valuation, and why it's a distribution not a number

A point estimate hides how sure the bot is. So each card gets a spread, not a single
figure:

- `point_value` = median comp asking price × the sold-to-asking ratio.
- `dispersion` = a robust spread (MAD by default, IQR optional) so one mad listing
  can't blow up the number the way standard deviation would.
- `n` = how many comps backed it.
- `confidence` = a 0–1 score from `n` and the relative spread. Lots of tight comps
  scores high. Few scattered ones scores low.
- `conservative_value` = `point_value − k × dispersion`. This is the number every
  money decision uses. Never the middle.

The buy threshold runs off the conservative end:

```
max bid = conservative_value − target profit − sell fees − buyer protection − postage in − postage out
```

A confident card with tight comps gets a near-full bid. A thin or scattered one gets a
much lower bid, or no alert at all. Uncertainty isn't a label on the side. It's priced
straight into what you'd pay.

An alert fires only when the current price sits at or under the max bid, the margin
clears ~25%, the profit clears ~£15, and the confidence gate passes (≥8 comps, spread
under threshold). Every alert shows max bid, point value, conservative value,
confidence, comp count and spread, so you can see why it's confident and overrule it.

## Run it locally

```bash
pip install -r requirements.txt

# Test the whole thing on mock data, no keys, prints alerts instead of sending:
python run.py --mode mock

# Live data + real WhatsApp (needs the secrets below in your environment):
python run.py --mode thirdparty   # default route, RapidAPI
python run.py --mode browse       # fallback, official eBay API
```

Tests:

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

Mock mode runs the full pipeline against `data/mock_listings.json`. It's built to
exercise both paths: two cards alert, four get skipped (thin comps, scattered comps,
over the price cap, no comps). Use it to sanity-check any change to the logic before
going live.

## Config

Everything tunable lives in [config.yaml](config.yaml): the calibration ratio, the
confidence gate, every fee rate itemised, the floors, the price cap, the search
queries. The placeholder thresholds (25% margin, £15 profit, £50 cap, 0.85 ratio) are
starting points to calibrate from logged outcomes, not settled numbers.

## Fee model

Itemised and conservative, confirmed against eBay UK's live rates on 2026-06-16. The
`seller_type` setting drives the sell side:

- Private seller (the default, your account today): £0 final value fees since Oct 2024.
  Watch for reclassification — eBay and HMRC flag accounts that buy-to-resell regularly
  and push them onto a business account. If that happens, set `seller_type: business`.
- Business seller: 12.8% final value fee + £0.40 fixed (orders over £10) + 0.35%
  regulatory operating fee, with 20% VAT on those fees. VAT-registered? Set
  `vat_on_fees_pct: 0` since you reclaim it.
- Buy side: the UK buyer-protection fee, tiered (7% to £20, 4% to £300, 2% above) plus
  £0.10. Assumed by default to stay conservative. Toggle with `apply_buyer_protection`.
- Postage both ways, flat per slab.

Private-seller £0 sell fees are treated as upside, never assumed. The trading-card 50%
FVF discount only kicks in at $1,000+, so it doesn't touch anything under the £50 cap.

## What you need to plug in — do these in order

Steps marked **[BEN]** only you can do. The code's built; these connect it.

**1. [BEN] Create the GitHub repo.** Make a private repo, push this whole folder into
it (CONTEXT.md, docs/adr/, src/, the workflow, all of it).

```bash
cd "OUTPUTS/eBay Valuation Bot"
git init && git add . && git commit -m "valbot v1"
git remote add origin git@github.com:YOURNAME/valbot.git
git push -u origin main
```

**2. [BEN] Get a RapidAPI key for an eBay data API.** This is the default route, and it
skips the eBay developer account entirely. Sign up at rapidapi.com, subscribe to an eBay
data API that gives live search and sold listings (search "eBay" on RapidAPI — several
do both), and copy your key. Then open `config.yaml` and set `thirdparty.api_host`, the
two endpoint `url`s, and the four field paths to match your provider's sample response.
That mapping is the only provider-specific bit; the rest is done.

Fallback if you'd rather use eBay's official API: skip RapidAPI, get a developer account
at developer.ebay.com with production App ID + Cert ID, and run `--mode browse`. The
Browse API needs no user token, just those two keys. Approval can be slow or refused,
which is why it's the fallback, not the default.

**3. [BEN] CallMeBot activation.** One-time, from your own phone. Add CallMeBot's number
(+34 644 51 95 23) to your contacts, send it `I allow callmebot to send me messages`,
and it replies with your personal API key. Full steps: callmebot.com/whatsapp.php.

**4. [BEN] Add the repo secrets.** In the repo: Settings → Secrets and variables →
Actions → New repository secret. Add four:

| Secret | Value |
|---|---|
| `RAPIDAPI_KEY` | your RapidAPI key (step 2) |
| `CALLMEBOT_PHONE` | your WhatsApp number, e.g. `+447…` |
| `CALLMEBOT_APIKEY` | the key CallMeBot sent you (step 3) |
| `EBAY_APP_ID` | only if using the official-API fallback |
| `EBAY_CERT_ID` | only if using the official-API fallback |

**5. Check it.** In the repo, Actions → valbot → Run workflow → pick `mock`. That proves
the workflow, the install and the run without spending an API call. Then run it once
with `thirdparty` once your RapidAPI key is in. The cron then takes over every 20 minutes.

## Going live, carefully

Run it read-only for a week. Alerts fire, you place no bids. As real auctions resolve,
fill in the `result` fields in `data/outcomes.json` (won/lost, final price, what it
later resold for). That's the data that calibrates the sold-to-asking ratio and tunes
the floors. Once the predicted values track reality, the thresholds can loosen.

Kill switch: disable the workflow in the Actions tab. Nothing runs, no money ever moves
without you.

## Layout

```
config.yaml              all tunables
run.py                   entry point
src/valbot/
  valuation.py           the distribution + conservative value
  fees.py                itemised all-in fee model + max-bid solver
  threshold.py           gate, floors, builds each assessment
  ebay_client.py         mock + thirdparty (RapidAPI) + official Browse, one interface
  alert.py               CallMeBot WhatsApp
  store.py               alert dedupe state + outcome log
  pipeline.py            the one pass
data/
  mock_listings.json     fixture for testing without keys
  sold_seed.json         hand-recorded solds seeding the ratio
  outcomes.json          logged predictions, fill in real results to calibrate
tests/                   valuation, fees, full pipeline
.github/workflows/valbot.yml   the cron
```
