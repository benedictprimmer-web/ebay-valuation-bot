# ADR-006 — Runtime for v1

**Status:** Accepted
**Date:** 2026-06-16

## Context
The bot must poll eBay on a schedule and fire alerts even with the laptop closed. The alerts-only model (ADR-002) removed any second-level timing requirement — this is just a periodic job. Constraints: easiest and cheapest to build on; Ben is travelling this year so local-only won't do.

## Decision
Run v1 as a **GitHub Actions scheduled workflow** (cron every ~15–30 min). State ("already alerted on this listing") lives in a committed JSON file for v1; migrate to a free hosted DB (e.g. Turso) only if it outgrows that.

## Consequences
- Free at this volume; no server to provision or maintain.
- Runs on GitHub's infra → laptop-closed is a non-issue.
- Code already lives in the repo (alongside CONTEXT.md and ADRs); the bot runs from the same place. Lowest friction to shipping.
- Secrets (eBay API keys) handled by repo secrets.
- Tradeoff: Actions cron can drift a few minutes and has no in-run persistence — both irrelevant here (no real-time need; state externalised to a file/DB).
- Upgrade path: lift-and-shift to a VPS or cloud function later if polling frequency or compute grows.
