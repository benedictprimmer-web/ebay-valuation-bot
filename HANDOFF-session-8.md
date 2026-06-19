# HANDOFF — eBay Valuation Bot, after session 8

Date: 2026-06-19. Read this first next time.

## One line
The eBay keyset is **live**. Production credentials exist, the account-deletion hoop is cleared by exemption, and both keys are in GitHub secrets. The only thing left before a real read-only run is the local self-test, which is mid-flight in Claude Code. No code blocks it.

## eBay developer status: APPROVED ✅ (was: STILL WAITING)
This is the unblock the last five sessions waited on.

- Developer account approved. Production keyset **`valbot`** created.
- **App ID (Client ID):** `Benedict-valbot-PRD-1dcf40d80-548ec3c8` (not secret; it's the public client id).
- **Cert ID (Client Secret):** held by Ben only, never written down here. Rotate link is on the Application Keys page if it ever leaks.
- **Dev ID:** unused. Browse is REST-only; Dev ID is for the old XML/Trading API. Ignore it.
- **Marketplace account deletion:** cleared by **exemption** ("I do not persist eBay data"). The bot reads public listing data and stores no eBay member PII, so the exemption is correct. No notification endpoint to build — this removes the one task that worried us in s6/s7.

## What changed this session

1. **eBay production access went live.** Account approved, `valbot` keyset created, exemption submitted, keyset flipped from disabled to active. App ID + Cert ID now exist.
2. **Keys wired into GitHub.** `EBAY_APP_ID` and `EBAY_CERT_ID` added as repository secrets (Settings → Secrets and variables → Actions). The Browse client (`src/valbot/ebay_client.py`, `BrowseAPISource`) already reads both via `config.secret()` and does the OAuth client-credentials token itself — so "wire the keys" needed **zero code change**. Pre-existing secrets `CARDAPI_KEY` and `EBAY_LIVE_API` left in place.
3. **`.env` loading handed to Claude Code.** `config.secret()` reads straight from `os.environ`; the app does **not** auto-load `.env`, so a local run can't see the keys yet. Claude Code was given a prompt to add `python-dotenv` loading in `run.py`/`targets.py`, add it to requirements, confirm `.env` is gitignored, then run the Browse self-test dry-run and report whether real GB auction fields come back populated.
4. **Model + next-steps one-pager created.** `reports/model-and-next-steps-onepager.html` and `reports/eBay-Bot-Model-and-Next-Steps.pdf`. Explains the pricing model (robust median + conservative cut, not a crude average and not ML), the calibration loop (human-in-the-loop, `calibrate.py`), every tunable in `config.yaml`, and the go-live sequence. Plain-English reference for Ben.

## Open issues / priority

1. **Browse self-test not yet confirmed.** The session-7 open item stands until Claude Code runs it: do real GB auctions return `currentBidPrice`, `bidCount`, `itemEndDate` populated? Both lanes. This is the gate before trusting any live number.
2. **`.env` loading.** Confirm Claude Code added `python-dotenv` (or equivalent), that `run.py`/`targets.py` load it at startup, and `.env` stays gitignored. Without this, local live runs silently fail to see the keys.
3. **Cameras sold source still on the Browse proxy** (ratio ~0.85, active-listing median). Apify sold-data upgrade (ratio → 1.0) is a config edit when Ben signs up. Unchanged from s7.
4. **Ratios + FVF are still placeholders.** Cameras ratio ~0.85, cameras FVF ~6.9%, cards FVF ~10.9%. Confirm FVF on eBay UK's business-seller calculator; calibrate ratios from the read-only week.
5. **Secret name mismatch.** `EBAY_LIVE_API` (in GitHub) ≠ `RAPIDAPI_KEY` (what the thirdparty route reads in `config.yaml`). Irrelevant to Browse; fix only if the RapidAPI/thirdparty route is ever used.
6. **Carried from s6:** keep the GitHub Actions schedule **disabled** until the self-test passes and the read-only week is done. Rotate the old RapidAPI key if it was ever exposed (no literal key is in the repo — grep is clean).

## Tasks for Ben

1. Finish the Claude Code run: let it add `.env` loading, create your local `.env` with `EBAY_APP_ID` + `EBAY_CERT_ID`, run the two `--mode browse --dry-run` self-tests, and **save the output** to paste next session.
2. Push session-8 changes via Claude Code (`.env` loading, `requirements.txt`, anything Claude Code touched). The Cowork GitHub connector is read-only, so pushes go through Claude Code.
3. When you want real camera sold data: sign up for Apify, drop its actor host + field paths into the cameras `thirdparty.sold` block, add the key. Until then the Browse proxy covers it.

## Tasks for Claude (next session)

1. **First, ask Ben where he is** on the `.env` file and the API keys (did `.env` loading land, did he create `.env`, did the self-test run, what did it print).
2. Read the self-test output. Confirm `currentBidPrice` / `bidCount` / `itemEndDate` are populated on real GB auctions before trusting anything. Both lanes.
3. Walk Ben through the **pre-launch checklist below**, one item at a time.
4. Once self-test passes: plan the read-only week (alerts-only, log predicted vs actual to `data/outcomes.json`), then calibrate with `calibrate.py`.

## Pre-launch checklist (work through this before it runs live)

- [ ] **1. `.env` loading wired** — `python-dotenv` added, loaded in `run.py`/`targets.py`, `.env` gitignored, local `.env` has `EBAY_APP_ID` + `EBAY_CERT_ID`.
- [ ] **2. Browse self-test passes** — `python run.py --mode browse --dry-run` and the cameras equivalent return real GB auctions with `currentBidPrice`, `bidCount`, `itemEndDate` populated.
- [ ] **3. GitHub secrets confirmed** — `EBAY_APP_ID`, `EBAY_CERT_ID` present (done). Fix `EBAY_LIVE_API` → `RAPIDAPI_KEY` only if using the thirdparty route.
- [ ] **4. Fees confirmed against eBay UK business calculator** — cameras FVF ~6.9%, cards ~10.9%, fixed £0.40, regulatory 0.35%, buyer-protection tiers, postage both ways. Update `config.yaml` if reality differs.
- [ ] **5. Cameras sold-comp source set** — Browse proxy now (ratio 0.85) or Apify wired (ratio 1.0). Confirm the cameras `thirdparty.sold` block.
- [ ] **6. Alert channel decided** — keep dry-run (no alerts) for the read-only week, OR activate CallMeBot WhatsApp (`CALLMEBOT_PHONE` + `CALLMEBOT_APIKEY` + one-time activation).
- [ ] **7. Watchlists populated** — real targets in `data/watchlist.example.csv` (cards) and `data/watchlist.cameras.example.csv` (cameras).
- [ ] **8. Read-only week** — run alerts-only, no bids, log predicted vs actual to `data/outcomes.json`.
- [ ] **9. Calibrate** — `python calibrate.py` once outcomes resolve: set sold ratio, floors, check conservative coverage. Then trust the numbers.
- [ ] **10. Enable the GitHub Actions schedule** — only after steps 2 and 9 look right. It stays disabled until then.
- [ ] **11. Tests green** — `python -m pytest -q` still passing (58 as of s7) after any changes.

## How to run (current)

```bash
python run.py --mode mock --dry-run                                                  # cards, mock (baseline)
python run.py --mode mock --sector cameras-lenses --mock-data data/mock_cameras.json --dry-run   # cameras, mock
python run.py --mode browse --dry-run                                                # cards, LIVE Browse (needs .env keys)
python run.py --mode browse --sector cameras-lenses --dry-run                        # cameras, LIVE Browse
python -m pytest -q                                                                  # tests
```

## Opening message to paste next time

Picking the eBay valuation bot back up. Read OUTPUTS/eBay Valuation Bot/HANDOFF-session-8.md, then CONTEXT.md and the ADRs. The eBay production keyset is **live** — account-deletion exemption done, `EBAY_APP_ID` + `EBAY_CERT_ID` are in GitHub secrets, App ID is `Benedict-valbot-PRD-1dcf40d80-548ec3c8`. Before doing anything, **ask me**: (1) did the `.env` loading get added, and did I create a local `.env` with the keys? (2) did the Browse self-test run, and what did it print — are `currentBidPrice` / `bidCount` / `itemEndDate` populated on real GB auctions? Then walk me through the pre-launch checklist in the handoff, one item at a time, and let's get it running read-only. Keep it read-only — no bids, no live WhatsApp until I say.
