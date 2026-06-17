# Deep research prompt — live eBay UK auction data (for ChatGPT)

Paste everything below into ChatGPT (use its deep research / web-browsing mode).

---

I'm building a read-only tool that watches **graded sports-card auctions on eBay UK** and flags ones that look underpriced versus recent sold prices. It alerts me; I bid by hand. No automated bidding.

For this to work I need a reliable, affordable way to pull **live auction listings** programmatically. Specifically, for each listing I need:

- **current bid price** (or current price), in **GBP** or convertible
- **auction end time** (or time remaining) — this is essential, the whole point is "ending soon"
- a stable **item ID** and the **listing URL**
- the listing **title**
- ideally a way to filter to **auctions only**, **eBay UK (ebay.co.uk)**, sorted by **ending soonest**, by **keyword**

I already have the *sold-price* side solved (a trading-card sold-comps API). I only need the **live auction** feed.

What I tried and why it failed: a RapidAPI provider called "Real-Time eBay API" (by uniquebyofficial). It returns ebay.com search results as Buy-It-Now price *ranges* in USD, with empty end-time fields and bid count always 0 — no real auction data. I need to avoid sinking time into similar scrapers that don't actually expose auction timers and bids.

## What I need you to research

1. **API providers that genuinely return live eBay auction data** (current bid + end time), beyond eBay's official API and beyond the dud above. Cover RapidAPI listings *and* standalone providers (e.g. Apify actors, ScraperAPI-style services, Zyte, Bright Data, Oxylabs, niche eBay data vendors). For each promising one, confirm from its docs whether it actually exposes: auction buying-format filter, current bid, end time/time-left, eBay UK marketplace, keyword search. Don't list providers you can't verify support auctions — that's the trap.

2. **eBay's official Browse API — the real access situation in 2026.** What's actually required to get production access for active/auction listing search? Is it genuinely a contract + approval, or do many devs get Browse access quickly? How long does approval take, and what gets applications rejected? Any recent (2025–2026) developer reports.

3. **How other people solve "live eBay auction data" in practice.** Search GitHub for open-source projects (eBay snipers, deal-finders, price trackers, card flippers) and read how they source live auction data — official API, scraping, third-party, RSS, anything. Note the repo, the method, and whether it still works. Also dev blogs / write-ups describing the approach and the pitfalls.

4. **Self-scraping reality.** If someone scrapes ebay.co.uk auction search directly: how hard is it, what breaks, what's the IP-ban / ToS risk, and what tooling (residential proxies, headless browsers) is realistically needed. Is there a lightweight legal route (e.g. eBay RSS feeds, affiliate feeds, sitemap)?

5. **Cost.** For every viable option, give the actual pricing tiers and whether a free/cheap tier covers ~a few hundred calls a day (one keyword sweep every 20 min).

## Output format

- A ranked shortlist of **2–4 options that actually work**, each with: name, method (official API / third-party / scrape), confirmed auction support (bid + end time + UK), auth model, pricing, and a link to docs or the repo.
- A clear **#1 recommendation** with the reasoning, and what the first integration step would be.
- A short "**avoid these**" list of providers that look right but don't expose auction data.
- Cite sources for each claim (links).

Be skeptical and concrete. I've already wasted a subscription on something that looked right and wasn't — I need verified auction support, not marketing copy.
