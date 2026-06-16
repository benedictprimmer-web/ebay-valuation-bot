# CONTEXT — eBay Valuation Bot

Living glossary + decision log. Built during planning. Terms are locked as we agree them; nothing here is filler.

_Last updated: 2026-06-16_

---

## Glossary (locked terms)

| Term | Definition |
|------|------------|
| _Item_ | TBD — listing vs product vs SKU |
| _Snipe_ | In v1, a **snipe = an alert**, not an action. The bot surfaces an underpriced auction near its end; Ben places the bid manually. (Reserved for redefinition if automation is added later.) |
| _Worth / Valuation_ | The estimated resale value of an item. v1 source: **median of active listing asking prices, adjusted by a manually-calibrated sold-vs-asking ratio per category.** |
| _Alert_ | A notification fired when a live item's price sits under `valuation − margin − fees`. Contains the listing, the computed max bid, and expected margin. |
| _Item (v1)_ | A **graded sports card** (e.g. PSA/BGS slab), identified by player + set + grade. Near-fungible at a given grade. |
| _Max bid_ | `valuation − margin − sell fees − buyer-protection fee − postage(in) − postage(out)`. The most Ben should pay; the alert states it. |
| _Fees (baked-in)_ | **Conservative all-in:** business-seller sell fee (~12.8% + ~£0.40), UK buyer-protection fee on purchase, postage both ways. Private-seller £0 sell fees treated as upside, not assumed. Exact rates confirmed against eBay's live calculator before launch. |
| _Margin floor_ | Minimum margin % for an alert to surface (placeholder ~25%). Quality gate. |
| _Profit floor_ | Minimum absolute £ profit for an alert to surface (placeholder ~£15). Worth-the-effort gate. |
| _Price cap (v1)_ | Temporary max item price (placeholder ~£50). Risk control, **not** a ranking input. Lifts as calibration proves out. |

---

## Decisions locked

### D1 — Valuation source (v1)
**Active listings + manual sold seed.** Pull current active listings via eBay's free Browse API. Anchor to a small hand-recorded set of sold comps to calibrate a sold-vs-asking ratio per category. Accuracy improves as real sold outcomes get logged.

- **Why not Marketplace Insights:** access-gated, slow/often-denied approval, blocks v1 on an external gatekeeper.
- **Why not scraping:** breaks eBay's user agreement, IP-ban risk, fragile to HTML changes.
- **Trade-off accepted:** lower precision at launch in exchange for shipping legally and now. (See ADR-001.)

### D2 — Bidding model (v1)
**Valuation + alerts, human confirms.** The bot values items and fires an alert when price drops under threshold. Ben places the bid himself. No web automation, no ToS breach, no autonomous spend.

- **Why not full auto-snipe:** breaks eBay's user agreement, account-ban risk, fragile to UI changes, and forces debugging automation before the valuation is even proven.
- **Why not 3rd-party snipe service:** external dependency and still automated bidding; unnecessary for v1.
- **Knock-on effects:** runtime no longer needs second-level precision; risk controls simplify (no autonomous money movement). (See ADR-002.)

### D3 — Category scope (v1)
**Graded sports cards (PSA/BGS slabs).** Chosen for valuation honesty, not margin size: grading removes condition variance (the biggest killer of automated valuation), comps line up cleanly, liquidity is high, and it overlaps Ben's football knowledge. Data model treats _category_ as a parameter so a second category can be cloned later; v1 runs **one** calibration. (See ADR-003.)

### D4 — Alert ranking model (v1)
**Sort by expected £ profit, with two floors.**
- Sort: expected £ profit per flip.
- Floor 1 (quality): margin ≥ ~25%.
- Floor 2 (worth-the-effort): profit ≥ ~£15.
- The v1 _price cap_ is a separate risk control, not a ranking input.
- v2 toggle: switch sort to ROI (£ profit ÷ £ invested) if capital becomes the binding constraint instead of time. (See ADR-004.)

Placeholder thresholds (25%, £15, £50) are to be calibrated from logged predicted-vs-actual sold outcomes, not fixed.

### D5 — Fee model (v1)
**Conservative all-in.** Bake every cost between winning bid and final profit into the max-bid formula: business-seller sell fees (~12.8% + ~£0.40), UK buyer-protection fee on purchase, and postage both ways. Private-seller £0 sell fees are treated as upside, not assumed. Rates itemised (not a flat haircut) so it's clear which cost eats margin, and confirmed against eBay's live calculator before launch. (See ADR-005.)

### D6 — Runtime (v1)
**GitHub Actions scheduled workflow.** A cron workflow (every ~15–30 min) polls the Browse API for graded cards ending in the next few hours, values them, and fires alerts. Free at this volume, no server to maintain, runs laptop-closed on GitHub's infra, secrets in repo secrets. State ("already alerted") in a committed JSON file for v1, migrate to a free hosted DB (e.g. Turso) only if needed. (See ADR-006.)

- **Why not VPS:** more control but adds cost + upkeep not needed yet.
- **Why not local cron:** doesn't run laptop-closed; Ben is travelling this year.
- **Tradeoff accepted:** Actions cron can drift a few minutes — irrelevant given no second-level timing requirement.

### D7 — Alert channel (v1)
**WhatsApp via CallMeBot.** Ben lives in WhatsApp, so alerts land where he'll see them in time. CallMeBot is a free, no-registration WhatsApp API — one HTTPS GET from the Actions job after a one-time activation. Single recipient (him), personal-use, third-party relay (acceptable for public listing data). Upgrade path: Meta WhatsApp Cloud API when robustness/multi-user is needed. (See ADR-007.)

### D8 — Confidence gate (v1 risk control)
**Strict gate + confidence shown.** With manual buy-confirmation, the real risk is a bad valuation, not runaway spend. So the bot only alerts when the comps support the number: require ≥8 comparable active listings AND price spread under a threshold; skip thin/scattered data. Every alert shows max bid, margin, comp count and spread so Ben sees why it's confident. Kill switch = disable the workflow. (See ADR-008.)

### D9 — Sell side (v1 scope)
**Out of the bot; manual.** The bot's job ends at the buy alert. _Valuation_ already equals the expected eBay resale price at that grade, so the sell price is implied, not separately computed. Relisting, timing and marketplace are manual in v1. Returns/duds risk is minimal by design — graded slabs (D3) remove the condition uncertainty that drives bad buys. Realised sell outcomes get logged to calibrate the valuation ratio (D1).

---

## v1 system shape (one pass)

1. **Poll** (GitHub Actions cron, ~15–30 min) — query Browse API for graded sports-card auctions ending in the next few hours.
2. **Value** — for each, gather comparable active listings; compute worth = median asking × sold-vs-asking ratio (per-category calibration).
3. **Gate** — drop items with <8 comps or too-wide spread.
4. **Threshold** — compute max bid = valuation − margin − all-in fees − postage both ways. Drop if below margin floor (~25%) or profit floor (~£15) or above the v1 price cap (~£50).
5. **Rank** — sort surviving items by expected £ profit.
6. **Alert** — WhatsApp (CallMeBot) with card, max bid, expected margin, comp count, spread.
7. **Ben acts** — places the bid manually if he likes it.
8. **Log** — record outcome (won/lost, final price, eventual resale) to calibrate the ratio and tune the floors.

## Next steps (build)
- Spin up the GitHub repo; commit CONTEXT.md + docs/adr/.
- Get eBay developer keys; confirm Browse API access for the cards category.
- Confirm exact fee rates against eBay's live calculator; set the placeholder thresholds.
- Build the poll→value→gate→threshold→rank→alert pipeline as a single script.
- Wire CallMeBot; do the one-time activation.
- Run read-only for a week (alerts only, no bids) and log predicted-vs-actual to calibrate before acting on it.
- Risk controls beyond the price cap: budget cap, kill switch.
- Runtime: where it runs (no longer needs second-level precision).
- Alert channel: how Ben gets notified (email / push / Slack / WhatsApp).
