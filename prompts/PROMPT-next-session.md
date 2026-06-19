# Paste into a fresh Cowork session to pick the project back up

---

Picking the eBay valuation bot back up. Read OUTPUTS/eBay Valuation Bot/HANDOFF-session-8.md,
then CONTEXT.md and the ADRs.

The eBay production keyset is **live** — account-deletion exemption done, `EBAY_APP_ID` +
`EBAY_CERT_ID` are in GitHub secrets, App ID is `Benedict-valbot-PRD-1dcf40d80-548ec3c8`.
Both lanes (cards + cameras) run on mock, 58 tests green, sold-comp source decided
(Browse proxy now, Apify later).

Before doing anything, **ask me**:
1. Did the `.env` loading get added, and did I create a local `.env` with the keys?
2. Did the Browse self-test run, and what did it print — are `currentBidPrice` /
   `bidCount` / `itemEndDate` populated on real GB auctions?

Then walk me through the pre-launch checklist in HANDOFF-session-8.md, one item at a time,
and let's get it running read-only. Keep it read-only — no bids, no live WhatsApp until I say.
