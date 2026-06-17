# Research results — Claude (chat), pasted 17 June 2026

Source: Claude chat, deeper run on the live-data question. More schema-level verification
than the Grok pass. Cross-checks and largely overrides Grok's "Apify first" call.

## Bottom line
The official **eBay Browse API is a viable live-auction source in 2026** for a read-only
use case. Its `item_summary/search` response can return `currentBidPrice`, `bidCount`,
`itemEndDate`, `itemId`, `legacyItemId`, `itemWebUrl`, and `title` for auctions. It
supports keyword search, auction filtering via `buyingOptions:{AUCTION}`,
`sort=endingSoonest`, and `X-EBAY-C-MARKETPLACE-ID: EBAY_GB` for eBay UK. Default Browse
limit is **5,000 calls/day** — plenty for a 20-minute sweep across several keywords.

No RapidAPI provider could be verified from docs as reliably returning live auction
bid + end-time for eBay UK. That's the exact failure mode to avoid (matches the
`uniquebyofficial` dud).

## Ranked shortlist
1. **eBay Browse API** — only option with first-party docs for the exact fields/filters
   needed. OAuth client-credentials (server-to-server, no bidder login). Effectively free
   under default limits. Caveat: `getItems` is limited-release, but `search`, `getItem`,
   `getItemByLegacyId` are open to all.
2. **Apify `data_ops_main/ebay-uk-scraper`** — cleanest UK-only scraper, documents keyword
   search, bid count, time remaining. Apify token; ~$2/1,000 starts; free $5 to test.
   Best non-official path for a UK "ending soon" watchlist.
3. **Apify `cloud9_ai/ebay-product-scraper`** — explicit docs: 8 markets incl. UK, bids,
   time left, auction filter, ending-soonest. From $1.50/1,000 results.
4. **Apify `harvestlab/ebay-product-scraper`** — richest schema (13 markets, bids, time
   left, item IDs) but the actor itself warns of HTTP 403 blocks from Apify-hosted
   requests as of June 2026. Backup only.

## The Browse API access reality (this matters for me — I just signed up)
- Developer-program membership is **free**; account approval ~**1 business day**.
- Before a production keyset works, you must complete the **account-deletion / closure
  notification compliance step**.
- After the keyset, you can use APIs immediately under default limits.
- Oct 2025 eBay support: most Browse methods are **not restricted**, open to all partners.
  The valid scope is the generic application scope (`buy.browse` is NOT a valid scope).
- The "contracts + approval" horror stories are mostly about (a) gated Buy/checkout flows
  and limited-release methods, and (b) the **Application Growth Check** needed only to go
  beyond default limits. For a few hundred calls/day, basic Browse access is usually not
  the hard part. Looking atypical (not a business) can slow developer-account approval.

## Number-one recommendation
Build against the **official Browse API first**. It gives the key fields directly: current
bid, bid count, end timestamp, stable IDs, listing URL, UK support, auction filter,
ending-soon sort. Less infra, less breakage, less proxy spend than scraping.

Integration steps: 1) create developer account + production keyset; 2) complete the
account-deletion compliance step; 3) get a client-credentials token (generic scope);
4) `GET /buy/browse/v1/item_summary/search` with `EBAY_GB`, `q=`, `filter=buyingOptions:{AUCTION}`,
`sort=endingSoonest`; 5) store `legacyItemId`, `itemId`, `itemWebUrl`, `title`,
`currentBidPrice`, `bidCount`, `itemEndDate`; 6) optionally enrich rows with `getItem`.
Backup if access snags: Apify `data_ops_main/ebay-uk-scraper` for a fast UK proof-of-concept.

## On RSS / watchcount-style routes
eBay search RSS refreshes only ~every 30 min and won't surface items ending within ~15 min,
so it's poor for "ending soon" logic. RSS-Bridge eBay had 403s in May 2026 and empty
results in Aug 2025. Not a foundation.

## Self-scraping reality
Possible but not lightweight at reliability. eBay `robots.txt` prohibits automated access
without permission; datacentre IPs get blocked; residential proxies + pacing needed.
Unblocking layers exist (ScraperAPI ~$49/mo for 100k credits; Bright Data ~$1.50/1,000
records) but they solve a problem Browse already solves more cleanly for these fields.
Also: search completeness is imperfect (listings can lag up to 24h in search), and HTML
selector drift needs maintenance.

## Avoid
- RapidAPI providers that don't explicitly document live auction fields (the dud pattern).
- RSS / RSS-bridge for ending-soon logic.
- Actors/wrappers that only advertise price/condition/shipping without naming bids + time-left.

## Maintained code references
- `hendt/ebay-api` (TypeScript, Browse support) — durable first-party wrapper.
- `austinpkugler/lego-price-tracker` (`ebaysdk`, notes the 5,000/day limit).
- `samjmck/ebay-monitor` (scrapes search; admits it's unmaintained).
- `IsmaelHG/eBayAutoSearch` (scrapes saved-search URLs; needs residential IP since 2023).

## Shortest version
Use Browse first; keep one UK-specific Apify actor as contingency; do not build on RSS or
poorly documented RapidAPI scrapers.
