# ADR-002 — Bidding model for v1

**Status:** Accepted
**Date:** 2026-06-16

## Context
eBay's API has no open path for placing bids. True auto-sniping requires browser automation, which breaks eBay's user agreement and risks account bans. The valuation engine is the legitimate, high-value part; the bidding piece is where the constraints bite.

## Decision
v1 is **valuation + alerts with human confirmation**. The bot finds underpriced auctions, computes a max bid, and alerts Ben. Ben places the bid manually.

## Consequences
- No ToS conflict, no ban risk, no autonomous spend.
- Ships faster — the hard, valuable part (knowing what something's worth) is built first and proven before any automation.
- Runtime no longer needs second-level timing; alerts can fire with a comfortable buffer before auction end.
- Risk controls simplify, since no money moves without a human.
- Clean upgrade path: automation (own or 3rd-party) can be layered on later once valuation accuracy is trusted.
