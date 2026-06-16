# HANDOFF — eBay Valuation Bot, build session

Planning's done. This session builds the thing. Goal: ship a **read-only v1 today** that values graded sports cards and WhatsApps Ben when one's underpriced. No bidding, no automation of money. Alerts only.

## Do this first
1. Read every file in `ABOUT ME/` (about-me, anti-ai-writing-style, my-company). Audit all written output against the anti-ai file.
2. Read `OUTPUTS/eBay Valuation Bot/CONTEXT.md` and every ADR in `OUTPUTS/eBay Valuation Bot/docs/adr/`. That's the locked plan. Don't relitigate settled decisions; build them.
3. Paste the opening message at the bottom and go.

## Where we are
v1 is fully specced. Eight decisions locked (D1–D9 in CONTEXT.md):
- Valuation from active listings + a manual sold-vs-asking ratio.
- Alerts only, Ben confirms every buy.
- Graded sports cards, one category.
- Rank by expected £ profit, gated by margin and profit floors.
- Conservative all-in fee model.
- Runs as a GitHub Actions cron.
- Alerts to WhatsApp via CallMeBot.
- Strict confidence gate.

What's missing and what this session adds: a **proper valuation metric with uncertainty baked in**. The plan had a point estimate. That's not enough. Spec below.

## The valuation metric (build this properly)

Don't output a single number. Output a distribution and bid against its conservative end. This is how uncertainty stops Ben overpaying on noise.

**Per item, compute:**
- `comps` — active listings of the *same* card: match on player + set + parallel/variant + grader + grade. Strict match. A PSA 9 is not a PSA 10.
- `point_value` = median(comp asking prices) × `sold_to_asking_ratio` (the per-category calibration; seed it by hand, refine from logged outcomes).
- `dispersion` = a robust spread measure (MAD or IQR), not standard deviation, so one mad listing doesn't blow it up.
- `n` = comp count.
- `confidence` = a function of `n` and relative dispersion (dispersion ÷ point_value). High `n` and tight spread means high confidence.
- `conservative_value` = `point_value` discounted by uncertainty. Concretely: `point_value − k × dispersion` (start k ≈ 1), or equivalently a lower percentile of the comp distribution. Wider spread or fewer comps pulls this down automatically.

**Then the money decision uses `conservative_value`, never `point_value`:**
```
max_bid = conservative_value − target_margin − all_in_fees − postage(in) − postage(out)
```
Alert only if `max_bid` still clears the margin floor (~25%) and profit floor (~£15), AND the confidence gate passes (≥8 comps, dispersion under threshold). The alert shows: card, max bid, point value, conservative value, confidence, n, spread. Ben sees how sure the bot is.

Why this matters: uncertainty isn't a separate warning label, it's priced straight into the bid. Confident card with tight comps gets a near-full bid. Thin, scattered card either gets a much lower bid or no alert at all. That's the whole point.

## Build order (and where Ben plugs in)

The agent builds the code. The connection steps only Ben can do are marked **[BEN]**. Do the build, then hand Ben the exact steps in order.

1. **[BEN]** Create the GitHub repo. Commit CONTEXT.md + docs/adr/ into it.
2. **[BEN]** eBay developer account → get production keys for the Browse API. *This is the one thing that can block "today" — see below.*
3. Build the pipeline as one script: poll → match comps → value (with uncertainty) → gate → threshold → rank → format alert.
4. Build it to run against **mocked/sandbox data first** so the logic is testable without waiting on eBay keys.
5. **[BEN]** CallMeBot one-time activation: message their number from your phone, get your personal API key.
6. Wire the WhatsApp alert (one HTTPS GET).
7. **[BEN]** Add secrets to the repo (eBay keys, CallMeBot key).
8. Add the GitHub Actions cron workflow (every ~15–30 min).
9. Add outcome logging: write every alert and, later, its real result to a committed JSON file (or Turso) to calibrate the ratio and tune floors.
10. Flip to live, read-only. Alerts fire, nobody bids. Watch for a week.

## Can it ship today? Honest read.
Mostly yes. The valuation logic, gate, alert, workflow, and CallMeBot are all same-day. The one real risk is **eBay production API access** — a developer account is quick, but production key approval can be instant or can take a review cycle. So: build and test against sandbox/mocked data today regardless, get it fully working, and swap to live keys the moment they land. If keys come through today, it ships today. If not, everything but the live data feed ships today and goes live the hour eBay approves.

## After it works
Once the read-only week shows the valuation tracks reality (logged predicted-vs-actual converging), the next call is whether to add bidding automation. That's a separate decision with its own ToS weight. Don't build it into v1.

---

## Opening message to paste

> I'm building the eBay valuation bot we planned. Read my ABOUT ME files, then read OUTPUTS/eBay Valuation Bot/CONTEXT.md and every ADR in docs/adr/ — that's the locked plan, build it, don't relitigate it. Goal: ship a read-only v1 today. It values graded sports cards from active-listing comps and WhatsApps me (via CallMeBot) when one's underpriced after all fees. No bidding.
>
> The one thing to build beyond the plan: a proper valuation metric with uncertainty priced in. Don't output a point estimate. Output a distribution — point value, robust spread, comp count, confidence — and compute the max bid off the *conservative* end (point value minus k × spread), not the middle. Thin or scattered comps must shrink the bid or kill the alert automatically. Spec is in the handoff.
>
> Run autonomously. Build the whole pipeline against mocked/sandbox data so it's testable now, then give me the exact connection steps I need to do myself in order: GitHub repo, eBay production keys, CallMeBot activation, repo secrets. Flag honestly if eBay key approval is what stands between us and shipping today. Let's get it read-only and live.
