# Research results — Grok (fast version), pasted 17 June 2026

Source: Grok, run on the `RESEARCH-grok-social.md` prompt. Fast model, so treat as a
first pass to cross-check against the Claude-chat result.

## Headline findings
- **Official Browse/Buy API** is the "proper" route but approval is painful for solo
  builders — frequent rejections or long delays on production access. Sandbox is easy,
  production is gated. Framing it as a buyer/research tool (not automation/sniping) helps.
- **Apify eBay actors** come up repeatedly as the practical scraping route: structured
  output with current bids, end times, UK filtering; handles proxies/anti-bot internally.
- **RapidAPI eBay options** (OpenWeb Ninja Real-Time eBay Data, Bidvoy, others) are mixed —
  some give live bids, others lag or are BIN-focused. Cheap entry, variable quality.
- **DIY scraping** works but eBay aggressively detects bots: rate limits, IP bans, CAPTCHA,
  layout drift. Workarounds: residential proxies, polite cadence (minutes not seconds),
  headless stealth (Playwright/Puppeteer).

## Money-making angle
- Card flipping margins reported around 10–40%+ net after fees/shipping; graded flips or
  mispriced lots can hit 40–100%. Low-end common cards need high volume for real income.
- Monetisation beyond flipping: build/sell sniping or monitoring tools, Discord alert
  groups, newsletters, YouTube case studies; eBay Live / Whatnot for velocity; grading
  arbitrage; bulk lot break-up.
- Real talk: fees (~13%+) eat margins; success comes from sharp buying more than tech;
  volume + discipline beats one big score. Some sellers left eBay over fees.

## Grok's top approaches (consensus)
1. Apify (or similar managed scraper) + proxies — most practical for reliable current
   bid / end time on UK auctions without approval headaches. Cheapest reliable for indie.
2. eBay Browse API — if approved; best long-term/compliant.
3. Hybrid: RapidAPI wrapper for quick starts + custom monitoring; polite scraping backup.

Cheapest reliable per Grok: start with Apify actors or a solid RapidAPI option (~$10–50/mo).

## Caveats Grok flagged
- Opinions split on scraping vs API (scraping more accessible short-term).
- Flipping profitability is split (some crush it, others break even after time/fees).
- 2024–2026 data is fresher on tools than on deep profitability case studies.
