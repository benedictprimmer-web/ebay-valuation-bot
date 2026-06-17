# Deep research prompt — what actually works, from people who've done it (for Grok)

Paste everything below into Grok (lean on its X/Twitter access + web).

---

I'm building a read-only tool that watches **graded sports-card auctions on eBay UK** and flags underpriced ones. I bid by hand — no auto-bidding. My blocker is getting **live auction data** programmatically: I need each listing's **current bid**, **auction end time**, item ID, URL, and title, filtered to **eBay UK auctions**, affordably.

I don't want polished vendor marketing. I want **first-hand, recent (2024–2026) experience** from people who've actually tried to pull eBay auction data — what worked, what got them blocked, what they'd do differently.

## Dig into these sources

- **X/Twitter**: developers, resellers, card flippers, and scraping/indie-hacker accounts talking about eBay APIs, eBay scraping, sniping tools, reselling automation, and data providers. Surface specific tools and specific complaints.
- **Reddit**: r/flipping, r/sportscard, r/sportscards, r/webscraping, r/eBaySellers, r/learnprogramming, r/datasets, and any eBay-developer threads. Find posts where people describe how they got (or failed to get) live eBay auction data.
- Hacker News and dev forums where relevant.

## Questions to answer

1. What do people **actually use** to get live eBay (especially UK) auction data — official Browse API, specific RapidAPI providers (name them), Apify/other scrapers, or DIY scraping? Which ones do people say genuinely return **current bid + end time** (not just Buy-It-Now prices)?
2. What's the **real story on eBay's official API approval** in 2025–2026 — do people get Browse/Buy access easily, or get stuck/rejected? Any tips that worked?
3. What **breaks or gets you banned** when scraping eBay directly — rate limits, IP bans, layout changes — and how do people get around it (proxies, cadence, headless browsers)?
4. Any **specific providers or repos people recommend or warn against by name**, with the reason.
5. Any clever **non-obvious routes** (RSS feeds, affiliate/partner feeds, third-party deal-alert services with APIs, existing sniping services that expose data).

## Output format

- Grouped themes (e.g. "official API experience", "third-party providers people rate", "scraping gotchas", "things to avoid").
- **Named** tools/providers/repos with a one-line verdict and a link or source for each.
- A short list of the **2–3 approaches that come up most as actually working**, and any consensus on the cheapest reliable one.
- Flag where opinion is split or where info looks out of date.

Prioritise recent, specific, first-hand posts over generic listicles.
