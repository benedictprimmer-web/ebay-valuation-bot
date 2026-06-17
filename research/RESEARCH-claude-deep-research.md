# Deep research prompt — for Claude (chat, deep research / extended mode)

Paste everything below the line into Claude. It's a deeper version of the Grok prompt:
same core blocker, but it pushes harder on first-hand evidence, the money-making
angle, and which product category is actually worth my effort. Run it after the Grok
one so they cross-check each other.

---

**Role and goal.** You're my research partner. I want recent (2024–2026), first-hand,
specific evidence from people who've actually done this — not generic listicles or API
marketing. Where the evidence is thin or split, say so plainly rather than papering over it.

**What I'm building.** A read-only tool that watches graded sports-card auctions on
**eBay UK** and flags underpriced ones. I bid by hand — no auto-bidding, no ToS breach.
The valuation side already works: I pull real sold prices, take a conservative figure,
subtract all fees, and get a max bid. It's live as a manual "watch list" tool today.

**My hard blocker.** Reliable, affordable, programmatic **live auction data** for eBay
UK: current bid, auction end time, item ID, URL, and title, filtered to UK auctions
(not Buy-It-Now). The RapidAPI provider I bought turned out to be a Buy-It-Now scraper
with no auction fields, so that route is dead. I need to know what actually works.

**My constraints and preferences — weight your answer to these.**
- UK marketplace specifically. US-only data is much less useful to me.
- Read-only and within eBay's terms. I won't auto-bid or do anything ban-worthy.
- Small budget. Roughly £0–50/month to start. Flag the genuinely cheap reliable option.
- I prefer **high margin per flip, low volume**. Effort-per-flip matters more to me than
  total throughput. I'd rather make £40 on one clean flip than chase 20 small ones.
- I'm an indie solo builder, comfortable with code, not a registered business yet.

## Part A — the live data problem (go deeper than surface API talk)

1. **What people actually use for live eBay UK auction data.** Name specific providers,
   actors, repos and APIs. For each, state plainly: does it return current bid AND end
   time for *auctions* (not just BIN), does it cover ebay.co.uk, what does it cost, and
   how reliable is it in practice. I want a comparison I can act on, e.g. a table of
   provider × current-bid × end-time × UK × price × reliability × source link.
2. **The official eBay API in 2025–2026, told straight.** What's the real approval rate
   for Browse / Buy production access for a solo dev with a read-only buyer tool? What
   framing or steps got people approved? What gets people rejected? How long did it take?
   Is the auction data in Browse actually complete (live current bid, end time) or partial?
3. **Scraping reality.** For people who scraped eBay UK auctions: what got them blocked
   (rate limits, IP bans, CAPTCHA, layout changes), and what specifically worked around it
   (proxy type, polling cadence, headless stealth). Equally important: the **legal / ToS /
   account-risk** picture for a read-only buyer scraping at low volume. Is the risk real
   for someone bidding manually, or mostly a seller-side concern?
4. **Non-obvious routes.** RSS, affiliate/partner feeds, the eBay Partner Network, deal-
   alert services with APIs, sniping services that expose data, browser-extension
   approaches. Anything that returns live auction state without heavy scraping.

## Part B — making money (this is half the point, treat it seriously)

5. **First-hand money stories, 2024–2026.** Find people who actually made money in this
   space and say exactly how. Split it into: (a) flipping itself — real margins after fees
   and shipping, what categories and tactics, how much time per week; (b) building and
   selling tools, alert feeds, or Discord/newsletter communities around auction data —
   what they charged, how many subscribers, what retention looked like; (c) anything else
   (live selling, lot break-up, grading arbitrage). Prioritise concrete numbers over vibes.
6. **Flipper vs tool-builder.** What does the evidence say about which actually pays for a
   solo person — using the tool to flip, or selling the tool/alerts to other flippers?
   Where's the moat in each? What kills each model?

## Part C — is sports cards even the right category for me?

7. **High-margin, low-volume category scan.** Given my preference for effort-per-flip over
   volume, compare graded sports cards against other arbitrage-on-eBay-UK categories:
   electronics (phones, GPUs, audio), watches, sneakers, vintage tech, designer goods,
   anything else that comes up. For each, assess: typical margin per flip, how much
   condition variance hurts automated valuation, and whether item **identity is clean
   enough to value programmatically** (e.g. exact model numbers, sealed/new, graded slabs,
   stated refurb grades — versus messy used goods where condition is everything).
8. **The verdict I want from this part:** which one or two categories give the best mix of
   margin per flip, clean identity for valuation, and low volume needed — and why. Be
   willing to tell me sports cards is or isn't the best fit.

## Sources to actually dig
- **Reddit:** r/flipping, r/sportscards, r/sportscard, r/webscraping, r/eBaySellers,
  r/ebay, r/learnprogramming, r/datasets, r/Flipping, and eBay-developer threads. Look for
  posts where people describe succeeding or failing, with specifics.
- **X / Twitter:** resellers, card flippers, scraping and indie-hacker accounts on eBay
  APIs, scraping, sniping, reselling automation, and data providers.
- **Hacker News, GitHub, dev forums, indie-hacker communities** (Indie Hackers, etc.).
- **Provider docs** for any tool you name, to confirm what fields it really returns.

## Output format
- Group by theme: live-data options (with the comparison table), official-API reality,
  scraping + legal picture, money-making evidence, category verdict.
- Name every tool, provider, repo, person or post, each with a one-line verdict and a link.
- End with: the 2–3 approaches that come up most as actually working for live UK auction
  data, the cheapest reliable one, and your honest call on the best category for my
  high-margin / low-volume preference.
- Flag clearly wherever evidence is thin, outdated, or split.

Prioritise recent, specific, first-hand posts and case studies over general advice.
