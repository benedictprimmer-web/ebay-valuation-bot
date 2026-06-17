# Deep research prompt — what should I actually sell? (for Claude chat, deep research mode)

Paste everything below the line into Claude. This is the second research effort: the live
auction-data question is mostly answered (use eBay's Browse API), so this one is about
**which category and which angle** to point the bot at. Run it in deep-research / extended
mode.

---

**Role and goal.** You're my research partner. I want recent (2024–2026), first-hand,
specific evidence from people who've actually flipped on eBay UK — real numbers, real
categories, real failure stories. Where evidence is thin or split, say so. Don't pad.

**What I've built.** A read-only valuation bot for eBay UK. It pulls real sold prices for
an item, takes a conservative value, subtracts every fee, and outputs the most I should
bid. I bid by hand. It works today on graded sports cards. The category is a parameter, so
I can re-point it at something else without a rewrite — IF that something has a clean
enough identity to value automatically.

**The question.** What should I actually sell? Cards were a starting point, not a
conviction. I want the category and angle with the best fit to my constraints below.

**My constraints — weight everything to these. They are the whole point.**
- **High margin per flip, low volume.** I'd rather make £40–£100+ on one clean flip than
  £3 on fifty. Total throughput doesn't excite me; profit per unit of effort does.
- **Time is scarce.** I won't be buying and shipping 400 things. A realistic week is a
  handful of buys. The model has to surface a few strong opportunities, not a firehose.
- **Storage and size matter.** I don't have warehouse space and I don't want to handle
  big, heavy, bulky items. Small, dense, easy-to-store and easy-to-post is strongly
  preferred. Nothing gritty, fragile-and-huge, or logistically painful.
- **Clean identity for valuation.** The bot needs comparable sold items to value against.
  Categories where two items are near-interchangeable (exact model number, sealed/new,
  graded slab, stated grade) work. Categories where condition is everything and every item
  is a one-off do not — unless the angle below handles it.
- UK marketplace, small budget, solo, read-only, within eBay's terms.

## Part A — the bad-listing arbitrage angle (I think this is the real edge)

My hypothesis: the most underpriced items are **badly listed ones** — poor or missing
photos, vague or misspelled titles, thin descriptions, wrong or absent category. Buyers
and other bots skip them, so they go cheap. I have the data and the model to spot value
others miss. I want this angle stress-tested.

1. Is bad-listing arbitrage actually real and repeatable on eBay UK in 2024–2026, or
   folklore? Find first-hand accounts of people buying underpriced poorly-listed items and
   reselling well. What signals did they use (misspellings, no-photo, vague titles, ending
   at odd hours, zero watchers)?
2. What does a bad listing do to *automated valuation*? If the title is vague or misspelled
   and there are few photos, matching it to sold comps gets harder. How have people handled
   identification on messy listings — fuzzy title matching, image-based matching, model-
   number extraction, category inference? What's realistic for a solo builder?
3. Which categories have the most exploitable bad listings (sellers who don't know what
   they have), and which are too picked-over?

## Part B — category scan, scored against my constraints

For each candidate category, score it on: typical margin per flip, volume needed for
meaningful income, item size/weight/storage burden, how badly condition variance hurts
valuation, and whether identity is clean enough for the bot to value automatically. Give a
one-line verdict per category and a final ranking for *my* constraints (high margin, low
volume, small/dense, clean identity).

Candidates to cover (add others you find):
- Graded sports/TCG cards (my current baseline — be honest if something beats it).
- Sealed trading-card product (booster boxes, etc.).
- Consumer electronics: phones, GPUs, audio gear, cameras, retro/vintage tech.
- Watches (mechanical, fashion, parts).
- Sneakers / streetwear.
- Designer fashion and accessories.
- Lego (sealed sets, retired).
- Collectible coins, stamps, books/first editions, vinyl.
- Anything niche and dense with strong margins that resellers quietly rate.

## Part C — the money model, briefly
4. For the top 2–3 categories, what's the realistic monthly profit for someone doing a
   handful of flips a week, after eBay fees and postage? Where do people actually lose money
   (overpaying, fakes, returns, dead stock, grading costs)?
5. Fakes and authentication risk per category — which categories are a minefield for an
   automated buyer (sneakers, watches, designer) and which are relatively safe?

## Sources to dig
Reddit (r/flipping, r/Flipping, r/eBaySellers, r/SportsCards, r/watchexchange, r/sneakers,
r/lego trading, r/coins, niche reseller subs), X/Twitter reseller and flipper accounts,
YouTube reseller case studies with real numbers, Hacker News / Indie Hackers, and any
data-backed reselling write-ups.

## Output format
- A scored category table (category × margin-per-flip × volume-needed × size/storage ×
  condition-risk × identity-cleanness × verdict).
- The bad-listing angle: is it real, the signals that work, and what it demands of the
  valuation model.
- A clear final pick: the one or two categories that best fit high-margin, low-volume,
  small/dense, clean-identity — with the reasoning, and an honest note on what I'd give up.
- Flag anything thin, outdated, or split. Recent and first-hand over generic.
