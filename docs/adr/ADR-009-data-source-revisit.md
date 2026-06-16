# ADR-009 — Data source revisit: default to third-party sold data

**Status:** Accepted (supersedes the default in ADR-001; ADR-001's reasoning still stands)
**Date:** 2026-06-16

## Context
ADR-001 chose active listings via the official Browse API plus a hand-calibrated
sold-to-asking ratio, because real sold data (Marketplace Insights) is access-gated.
Two things surfaced after building it:

- The official Browse API's production access needs an eBay developer account and a
  review that can be slow or refused — the thing flagged as the one same-day blocker.
- Third-party providers on RapidAPI expose both live eBay search and real sold prices
  for a small monthly cost, with no eBay developer account. Confirmed available 2026-06.

Sold prices are the true valuation signal; the asking-to-sold ratio in ADR-001 was the
weakest assumption in the bot.

## Decision
Default the data source to a **third-party RapidAPI provider**: live search for targets
(auctions ending soon) and real sold listings for comps. Keep the official Browse API as
a **free fallback** behind the same `ListingSource` interface, selected by `--mode`.

Provider-specific response shape lives in `config.yaml` under `thirdparty` (host, two
endpoint URLs, four field paths), so swapping providers is config, not code.

## Consequences
- Removes the developer-account blocker; ships without waiting on eBay approval.
- Upgrades valuation from guessed-asking to real-sold; the sold-to-asking ratio becomes
  ~1 and eventually drops out of the maths.
- Adds a small monthly cost and a dependency on the provider's uptime — mitigated by the
  official Browse fallback staying one config switch away.
- The valuation engine, fee model, gate, ranking and alerting are unchanged: they were
  built source-agnostic, so only the feed swapped.
- The title-based identity match (grader + grade strict, player/set tokens present)
  carries the same approximation caveat for any source that returns freeform titles.
