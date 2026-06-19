# Camera Niches — One Tier Down Research
_Agent research run, June 2026. Replaces blue-chip shortlist for cameras lane._

## Why the previous targets failed
Sony A7 III (auction £680-900, max bid ~£401), Canon RF 50mm, Fujifilm X-T4 — all priced too efficiently. Bot's max bid never gets close to clearing price. Moved to APS-C and older full-frame bodies where auction scatter is real.

## Top 5 — ranked by auction scatter + deal frequency

| Rank | Model | Auction range | BIN ceiling | Auctions/wk | Config queries |
|---|---|---|---|---|---|
| 1 | **Sony A6000** | £90–£200 | £320–£380 | 40–60 | "Sony A6000 body" |
| 2 | **Canon EOS 6D (Mk I)** | £120–£230 | £280–£340 | 20–35 | "Canon EOS 6D body" |
| 3 | **Sony A7 II** | £160–£280 | £320–£380 | 20–30 | "Sony A7 II body" |
| 4 | **Nikon D610** | £140–£240 | £280–£360 | 15–25 | "Nikon D610 body" |
| 5 | **Fujifilm X-T30** | £150–£280 | £320–£380 | 15–25 | "Fujifilm X-T30 body" |

## Niche profiles

### Sony A6000 (BEST)
- **BIN/asking:** MPB £344–£459; CameraPriceBuster from £319; UsedLens from £243
- **Auction range:** £90–£200. Biggest scatter of any mirrorless in range.
- **Why bargains appear:** Decade of supply from upgrading Sony shooters. Body-only auctions start at £0.99. Lots of "untested/sold as seen" listings that are actually working. High volume means odd-hour endings produce low competition.
- **parse_camera key:** `sony|body|a6000` ✓

### Canon EOS 6D Mark I
- **BIN/asking:** MPB £164–£349; CameraPriceBuster 28 listings £194–£349
- **Auction range:** £120–£230. 20–35 auctions end per week.
- **Why bargains appear:** Canon RF upgraders listing on auction without research, using titles like "Canon 6D digital camera" not "full frame body." Often confused with 6D II in search results. Ends at estate sale hours.
- **parse_camera key:** `canon|body|6d` ✓ (distinct from 6D II = `canon|body|6d 2`)

### Sony A7 II
- **BIN/asking:** UsedLens from £269; CameraPriceBuster 75 listings from £249; idealo from £389
- **Auction range:** £160–£280. 20–30 auctions/week.
- **Why bargains appear:** Often listed as "Sony A7" (not "A7 II"). Videographer upgrades to A7 IV/FX. Older IBIS stigma depresses price beyond functional impact.
- **Note:** Auction floor £160–200 is well within £250 cap; top end £280 occasionally exceeds cap — that's fine, those are fairly priced.
- **parse_camera key:** `sony|body|a7 2` ✓

### Nikon D610
- **BIN/asking:** CameraPriceBuster 8 listings £139–£370; MPB £274–£364
- **Auction range:** £140–£240. 15–25 auctions/week.
- **Why bargains appear:** Early oil/shutter recall created lasting stigma. Recall was fixed; informed buyers know it's fine. Sellers who don't know the recall history either misprice or scare off buyers. Often listed without "full frame" in title.
- **parse_camera key:** `nikon|body|d610` ✓

### Fujifilm X-T30 (original, not X-T30 II)
- **BIN/asking:** CameraPriceBuster from £373; MPB £280–£380; UsedLens £229–£614
- **Auction range:** £150–£280. 15–25 auctions/week.
- **Why bargains appear:** Fuji community drives BIN prices up but non-community sellers don't know value. Often listed as "Fujifilm mirrorless camera" without model name, hiding from Fuji buyers.
- **parse_camera key:** `fujifilm|body|xt30` ✓

## Models that didn't make the cut

| Model | Reason |
|---|---|
| Sony A6300/A6400/A6600 | BIN £414–£819, auctions outside £250 cap |
| Canon 80D/90D | Auctions £280–350, too close to cap for margin |
| Nikon D750 | Floor £220–240, extremely tight against £250 cap |
| Fujifilm X-T20 | BIN from £418, less liquid than X-T30 |
| Canon AE-1/Nikon FM2 | Film cameras: condition impossible to assess remotely (bot risk) |
| Canon 50mm f/1.8 STM | Too low absolute value (£25–70 auction → £60–90 BIN) |

## Apify sold comps — field mapping (researched same session)
Actor: `harvestlab/ebay-scraper` — $0.003/result, UK GBP confirmed
- `priceValue` → float, sold price
- `currency` → "GBP" when `ebayDomain: "ebay.co.uk"`
- `title`, `itemId`, `url`, `sold` (bool), `soldDate`
- Input: `{ "searchQuery": "...", "ebayDomain": "ebay.co.uk", "categoryId": "31388" }`
- Once wired: set `sold_to_asking_ratio: 1.0` (real sold prices)
