# Quality, condition, seller & resale — full analysis

_Prompted by two real observations: a WhatsApp alert fired on a "parts / not working"
body, and a candidate had a very high shutter count. Both expose the same gap — we were
valuing **items** as if they were fungible, when used-camera value is **condition-dominated**._

## 1. The core insight (and the trap you caught)

For graded cards, the slab grade **is** the condition — a PSA 10 is a PSA 10. For used
cameras there is no grade: the *same model* trades over a **2–3× range** purely on
condition. Our sold-comp median is therefore "average used", a blend of mint-boxed and
beaten-to-death examples.

That creates one edge and one trap:

- **The edge (alpha):** an *above-median-condition* item priced *below* median — a lazy
  listing, bad photos, an auction ending at 3am. That's genuine mispricing.
- **The trap (false positive):** a *below-median-condition* item priced below median.
  It isn't a bargain — you're paying fair for a worse thing. The extreme case is
  **for-parts / not working**: dirt cheap, so it scores as a *huge* "profit" against
  working comps. That's the alert you saw. The discount is condition, not mispricing.

We can't fully close this without seeing the item, but we can stop the obvious own-goals
and surface the signals so a human eyeballs the rest.

## 2. What now ships (P0 — done)

Implemented in this change:

- **Capture** `condition`, `conditionId`, and **seller feedback** (% + count) from the
  Browse item onto every `Listing` (previously discarded).
- **Gate the target** in `_fetch_camera_targets` — never auto-alert on:
  - `conditionId 7000` ("For parts or not working") or condition text matching
    `exclude_target_conditions` (for parts / not working / spares / faulty);
  - a **title** containing `exclude_target_title_keywords` (spares, faulty, cracked,
    damaged, broken, untested, "read description", "no power", …) — catches sellers who
    label a broken item "Used" but confess in the title;
  - a seller **below `min_seller_feedback_pct`** (default 98%) — return/scam risk.
- **Show it in the alert**: the WhatsApp now carries a `Condition: Used · seller 99% (1500)`
  line so you can sanity-check before bidding.

All three gates are **config**, tunable per sector. This mirrors what we already do when
cleaning *comps* — now the **buy side** is protected too.

## 3. The dimensions of quality → price & resale

### Camera bodies
| Signal | Price/resale impact | Where it lives |
|---|---|---|
| **Functional status** (working / faulty / for-parts) | Biggest single factor. For-parts ≈ 10–30% of working value | conditionId, condition, title |
| **Shutter actuations** | Bodies rated 100k–300k. Near end-of-life discounts; very low count is a premium | Description / EXIF (not structured) |
| **Cosmetic grade** (mint↔brassed) | ±20–40% within "Used" | Description, photos |
| **Sensor issues** (dust, scratches, hot pixels) | Moderate to severe | Description, photos |
| **Completeness** (battery, charger, box, caps) | Missing charger/battery ≈ −£20–40; boxed = premium | Description |
| **Warranty / shop-refurbished** | Premium + lower risk | conditionId 2500, seller type |

### Lenses
| Signal | Impact | Where |
|---|---|---|
| **Optics** (fungus, haze, separation, scratches) | Fungus/haze = severe; a "cleaning marks" copy is much cheaper | Description, photos |
| **Mechanics** (focus/zoom feel, aperture oil, OSS/IS) | Moderate–severe | Description |
| **Cosmetic + caps/hood/box** | ±10–20% | Description |

**Key point for valuation:** condition affects **both sides** — what you'd safely pay
*and* what it resells for *and how fast it sells*. A mint boxed copy sells in days near the
top of the range; a scuffed one sits and clears at the bottom. Our fee model already nets
resale fees, but it assumes a single "average" resale price.

## 4. What's capturable, and at what cost

| Tier | Signals | Cost |
|---|---|---|
| **Free, structured** (already fetched) | conditionId/condition, seller feedback %/score, item location (UK vs import), returns-accepted, top-rated-seller, actual shipping cost | £0 — **use all of it** |
| **Free, from title** (already parsed) | spares/faulty/mint/boxed keywords, "shutter count 12k", "read description" | £0 — regex |
| **Cheap, one extra call** | Full **description** via Browse `getItem` (free) for candidates that pass the first gate → parse shutter count, faults, accessories | 1 free call per *shortlisted* candidate (not per search) |
| **Expensive / manual** | Photo assessment (sensor dust, brassing), true optical state | Human review, or vision model later |

The design rule from the cards lane still holds: **value automatically only when confident;
otherwise flag for manual review.** Condition is exactly where "flag, don't auto-bid" earns
its keep.

## 5. Prioritised roadmap

- **P0 — done:** capture condition + seller, gate broken/for-parts/low-feedback targets,
  show condition in the alert.
- **P1 — cheap, high value:**
  1. ✅ **Shutter-count parsing** from title (`shutter count 12,345`, `SC 12k`, `actuations`).
     Skips auto-alert past `shutter_max_fraction` (0.70) of `shutter_rating_default` (~150k);
     shown in the alert. Unknown (the common case) never penalises. _Title-only for now;
     P2 reads the description for the rest._
  2. ✅ **Real per-listing postage** from Browse (`shippingOptions`) overrides the flat
     £3.50 `postage_in` in the profit/max-bid maths; shown in the alert.
  3. **UK-only / returns-accepted** filters (drop imports; prefer returnable = can send a dud back).
  4. **Condition tag in the alert note** derived from title (mint/boxed vs worn) so ranking
     can prefer clean copies.
- **P2 — deeper:**
  5. **Fetch the description** (Browse `getItem`) for shortlisted candidates and parse
     shutter count / faults / included accessories; feed a **condition multiplier** into
     the valuation (e.g. −15% if "well used", +10% if "mint boxed low shutter").
  6. **Condition-tiered comps:** value against same-tier sold comps where the feed exposes
     per-comp condition, instead of one blended "used" pool.
- **P3 — learning:**
  7. Calibrate the condition multipliers and seller-risk from `outcomes.json` once real
     flips resolve (what did a "well used" copy actually resell for?).

## 6. Other things we're missing / could improve (beyond condition)

- **Auction price is a moving target.** A fresh auction at £1 with 47h left looks
  massively "profitable" and can alert early, then get bid up past your max. Options:
  only alert pure auctions **near close**, or tag early-auction alerts as speculative.
  (Buy-It-Now alerts don't have this problem — they're snap-buyable now.)
- **Real postage, both ways** — Browse gives per-listing shipping; the flat £3.50 estimate
  can flip a marginal deal.
- **Sell-through / liquidity** — some models sit for weeks. Weight by how fast a niche
  actually sells (we have the scatter scan; add velocity).
- **Seasonality & trend** — sold medians drift (new model launches crater the old one).
  The 30-day cache smooths noise but can lag a real drop; watch during launches.
- **Duplicate/near-identical alerts** — dedupe is by listing id; the same model from three
  sellers can alert three times. Optionally cap alerts per model per day.
- **Import/VAT** — non-UK sellers add import charges + risk; filter to UK item location.
- **Confidence already gates**, but n-comps and dispersion don't yet account for condition
  spread — a wide comp range may be *condition* variance, not mispricing noise.

---

_Status: §2 (P0) implemented. §5 P1–P3 and §6 are proposals awaiting prioritisation._
