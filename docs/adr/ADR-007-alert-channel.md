# ADR-007 — Alert channel for v1

**Status:** Accepted
**Date:** 2026-06-16

## Context
Alerts must reach Ben fast enough to act before an auction ends, and be easy to send from a GitHub Actions job. Ben's daily messenger is WhatsApp, so that's where he'll notice an alert in time. Twilio's WhatsApp API carries setup overhead and per-message cost.

## Decision
v1 sends alerts to **WhatsApp via CallMeBot** — a free, no-registration personal WhatsApp API. One HTTPS GET from the Actions job after a one-time activation message.

## Consequences
- Zero cost, zero infra, lands where Ben already is.
- Limitations (all acceptable for v1): single recipient (just Ben), personal-use only, and a third party relays the message — fine for public auction-listing data, not for anything sensitive.
- Upgrade path: Meta WhatsApp Cloud API (first 1,000 service conversations/month free; business verification + per-message cost for business-initiated templates) when robustness or multi-user is needed.
- Decision is cheap to reverse — it's one function at the end of the pipeline.
