# HANDOFF — eBay Valuation Bot, after session 7
Date: 2026-06-17. Read this first next time.

## One line
The cameras lane is wired end to end. Exact-model identity now drives the same pipeline
the cards lane uses, both lanes run side by side on mock data, and the one open gap — a UK
sold-comp source for cameras — has a decision. Still waiting on Ben's eBay keyset for live data.

## eBay developer status: STILL WAITING
The keyset is not ready, so everything that needs live eBay data stayed parked this session:
the account-deletion notification step, wiring `EBAY_APP_ID`/`EBAY_CERT_ID`, switching the
live source to Browse, and the real-auction self-test. All of that is unchanged from the
session-6 plan and runs the moment the keys land. No code blocks it.

## What changed this session
1. **Exact-model matching wired in (ADR-011).** `camera.py` was an orphan parser; it now
   drives the lane. Added an `identity: card | camera` switch to `config.yaml`. The cameras
   sector sets `identity: camera`, which routes a listing title to an exact `CameraItem`
   (brand + model) at the source boundary. A title that doesn't resolve to a specific body
   or lens is dropped before valuation — resolve-or-skip, the cameras version of the cards
   confidence gate. `CameraItem` already exposes `key()`/`label()`/`matches()`, so the whole
   downstream (value → gate → fees → rank → alert) runs unchanged. Wired through the mock,
   third-party and Browse sources plus the watchlist loader.
2. **Cameras run end to end on mock.** Rebuilt `data/mock_cameras.json` into a real pipeline
   fixture (targets + GBP sold comps, messy spellings of one model collapsing to one key).
   `run.py --sector cameras-lenses --mock-data data/mock_cameras.json` produces two alerts
   (Sony A7 III, Canon RF 50mm f1.8), skips thin comps (Canon EOS R6) and fair-value (X-T4),
   and drops the junk-lot target. Added `data/watchlist.cameras.example.csv` for targets mode.
3. **Sold-comp source decided (ADR-011).** No clean official UK sold feed exists. Staged
   call: **start on the Browse active-listing proxy** (official, free, rides in on the keyset,
   median asking × ~0.85 ratio), **upgrade to the Apify eBay sold-listings actor** for real
   GBP sold prices once the lane earns it. Rejected RapidAPI `ecommet` (unverifiable price,
   opaque single provider). Config scaffold for the sold endpoint is in `config.yaml` under
   the cameras sector, ready for whichever provider drops in.
4. **Tests: 58 passing** (was 38 in the s6 handoff, 51 after a prior session's camera-parser
   tests). Added `tests/test_cameras_pipeline.py` (7 tests): identity switch, resolve-or-skip,
   exact-model comp matching, end-to-end alerts, watchlist load + rejection of ambiguous titles.
5. **Polish:** alert labels render models cleanly (`Sony A7 3`, `Canon RF 50mm f1.8`,
   `Fujifilm XT4`) while the match key stays lowercase-normalised. Alert header is now
   "Underpriced listing", not "card", so it reads right for both lanes.

## The decision (build on this)
- Cards lane is the proven baseline. Untouched. Run it as-is.
- Cameras identity = exact model, resolve-or-skip. Rare/odd model spellings go to manual
  review rather than mis-valuing — that's intended.
- Sold comps for cameras: Browse proxy now (ratio ~0.85), Apify sold data later (ratio 1.0).
  Switching is a config edit, not a rebuild.

## Open issues / priority
1. **eBay keyset + compliance.** Unchanged from s6. Once approved: account-deletion
   notification step (opt out — read-only, stores no user data), create production keyset,
   add `EBAY_APP_ID`/`EBAY_CERT_ID` as repo secrets, run `--mode browse`. The deletion
   notification is the one real hoop.
2. **Self-test the Browse auction fields.** Still unverified against a real GB auction:
   confirm `currentBidPrice` / `bidCount` / `itemEndDate` come back populated before trusting.
3. **Cameras sold source is decided but not wired live.** Browse proxy needs the keyset;
   Apify needs a signup when you want it. Config block is staged and waiting.
4. **Calibrate the cameras ratio.** The ~0.85 Browse-proxy ratio and the ~6.9% camera FVF
   are placeholders — confirm FVF on eBay's business calculator, calibrate the ratio from
   real sold outcomes in the read-only week. Set ratio → 1.0 when real sold data is wired.
5. **Identity coverage.** `parse_camera` handles the common Sony/Canon/Nikon/Fuji/Panasonic/
   Olympus patterns. Watch the first real week for models that fall to manual review and add
   patterns as needed.
6. Carried from s6: rotate the exposed RapidAPI key; keep the workflow schedule disabled
   until a live source is wired.

## Tasks for Ben
1. Finish eBay developer approval. Tell Claude when the keyset's ready.
2. Push session-7 changes via Claude Code (Cowork GitHub connector is read-only). Changed:
   `config.yaml`, `src/valbot/camera.py`, `src/valbot/ebay_client.py`, `src/valbot/targets.py`,
   `src/valbot/formatting.py`, `targets.py`, `data/mock_cameras.json`,
   `data/watchlist.cameras.example.csv`, `tests/test_camera.py`,
   `tests/test_cameras_pipeline.py`, `docs/adr/ADR-011-cameras-identity-and-sold-comps.md`.
3. When you want real camera sold data: sign up for Apify, drop its actor host + field paths
   into the cameras `thirdparty.sold` block, add the key. Until then the Browse proxy covers it.

## Tasks for Claude (next session)
1. When the keyset lands: account-deletion notification step, wire the eBay keys, switch live
   source to Browse, self-test a GB auction (cards and cameras both).
2. Wire the chosen cameras sold source live (Browse proxy first; Apify when Ben signs up) and
   calibrate the ratio.
3. Calibration script once real outcomes exist (cards and cameras share it).
4. Tighten `parse_camera` patterns once the first real week shows mismatches.

## How to run (current)
```bash
python run.py --mode mock --dry-run                                                  # cards (baseline)
python run.py --mode mock --sector cameras-lenses --mock-data data/mock_cameras.json --dry-run   # cameras
python targets.py --watchlist data/watchlist.example.csv --mode mock                 # cards, watchlist
python targets.py --watchlist data/watchlist.cameras.example.csv --sector cameras-lenses --mode mock --mock-data data/mock_cameras.json
python -m pytest -q                                                                  # 58 passing
```

## Opening message to paste next time
Picking the eBay valuation bot back up. Read OUTPUTS/eBay Valuation Bot/HANDOFF-session-7.md,
then CONTEXT.md and the ADRs. Cameras lane is wired: exact-model identity drives the shared
pipeline, both lanes run on mock, 58 tests green. Sold-comp source decided — Browse proxy now,
Apify sold data later. My eBay developer status: [approved? keyset ready?]. If yes, do the
account-deletion step, wire the keys, switch to Browse, self-test a GB auction, then wire the
cameras sold source live and calibrate. Keep it read-only.
