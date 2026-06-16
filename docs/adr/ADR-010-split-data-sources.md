# ADR-010 — Split the feed: The Card API for comps, RapidAPI for live auctions

**Status:** Accepted (refines ADR-009; ADR-009's "third-party default" still stands)
**Date:** 2026-06-16

## Context
ADR-009 assumed one third-party provider would serve both halves of the feed: live
auctions ending soon (targets) and real sold prices (comps). Provider research showed
that assumption was wrong — the two are almost always separate products:

- **Live/active listings** with `time_left`, `bid_count`, `buying_format` come from
  general eBay-scraper APIs (e.g. OpenWeb Ninja "Real-Time eBay Data").
- **Sold prices** come from dedicated sold-comp APIs. For graded cards specifically,
  **The Card API** (thecardapi.com) is trading-card native: it parses player / set /
  grade and returns true sold prices including accepted Best Offer amounts — a better
  comp source than any generic eBay sold scraper, and it directly reduces the
  title-matching risk that ADR-009 flagged.

The Card API is not on RapidAPI for our purposes; its direct REST API
(`/api/v1/market/sales`, `x-market-api-key` header) is cleaner and well documented.
Its prices are USD; the bot reasons in GBP.

## Decision
Use **two sources, split by job**, both behind the existing `thirdparty` config:

- `sold` → The Card API, direct REST, its own key (`CARDAPI_KEY`). Prices USD.
- `live` → an eBay-scraper API on RapidAPI (`RAPIDAPI_KEY`). Prices GBP (query ebay.co.uk).

`config.yaml` now allows **per-endpoint auth** (`auth.scheme: rapidapi | header`) and a
per-endpoint `currency`. A global `fx.usd_to_gbp` converts USD comps to GBP at ingestion.

## Consequences
- Comps quality goes up: card-native parsing + true Best-Offer prices.
- Two keys instead of one; each endpoint resolves only the key it needs, so the comps
  side can run without a RapidAPI key and vice versa.
- New currency assumption. `fx.usd_to_gbp` is a placeholder (0.79) to calibrate. Bigger
  caveat: **US sold comps are not the same as UK resale value** — watch this in the
  read-only week before trusting the converted figure.
- Free-tier lookback on The Card API is 7 days; thin cards may not clear the 8-comp gate.
  Starter ($19/mo, 30-day lookback) is the fix if 7 days proves too short.
- Official eBay Browse API (`--mode browse`) remains the keyless fallback, unchanged.
