# Labelling test stage — a data-driven tuning plan

**Goal:** collect enough human labels on real alerts to see *where* the model is wrong,
then tune **per-niche value** and **alert thresholds** from that evidence — not from
guesses. Keep alerts **loose** for now (maximise label volume and cover the decision
boundary); tighten later, only where the data says.

This is deliberately **simple labels first** (good / bad). Trial-and-error volume → analyse
→ act. We don't act on single labels (they're noisy); we act on *patterns*.

---

## Phase 0 — Instrumented ✅ (done)
- Every alert carries a short **ref code**; `verdict.py <ref> good|bad [reason] [--fair £]`
  records it into `outcomes.json` (`human_verdict`).
- `calibrate.py` already surfaces: 👍/👎 totals, **distrusted niches** (per-niche 👎 rate),
  and **your fair vs our value** per niche.
- `observations.jsonl` logs condition / shutter / seller / postage for every assessment.

## Phase 1 — Collect (now) 🔵
- **Keep searches loose** — do NOT tighten yet. Volume and marginal alerts are the signal;
  we want labels spread across the good/bad boundary, not just obvious wins.
- **Simple labels only:** `good` / `bad`. Optional `--fair £` when you have a number in
  your head — it's the single strongest signal, but never required.
- **Dedicated intake channel** (a separate Claude session — see
  `prompts/PROMPT-verdict-intake.md`) so labelling never clutters the build session. Each
  label is auto-recorded and committed to `main`.
- **Volume gate to move on:** roughly **≥ 40 labels total** AND **≥ 5 per niche that's
  actually alerting**. (Adjust — some niches alert rarely.)

## Phase 2 — Analyse (once the gate is met) 🟡
All from `python calibrate.py` + `observations.jsonl`:
- **Precision:** 👍 / (👍+👎), overall and per niche — what share of alerts you actually liked.
- **Distrusted niches:** per-niche 👎 rate — high = we systematically mis-serve it.
- **Value error:** median(`your_fair` / `our_point_value`) per niche — `<1` = we over-value,
  `>1` = under-value, and by how much.
- **Reason-coding** (simple tag on each 👎): **VALUE** (overpriced) vs **QUALITY**
  (worn / seller / condition) vs **NICHE** (just don't want it). This decides which lever.

## Phase 3 — Act (data-driven, one lever at a time) 🟢
- **VALUE errors** → nudge that niche's `sold_to_asking_ratio` / discount by the measured
  factor (e.g. fair/our = 0.78 ⇒ pull the niche's ratio down ~20%). Re-measure.
- **QUALITY 👎** → tighten the condition / shutter / seller gates, or that niche's floors.
- **NICHE 👎** (you don't want it) → drop or down-rank that query.
- **Too many low-value alerts overall** → raise `profit_floor` / `margin_floor` — but ONLY
  after the data confirms it. Right now, volume = signal, so we stay loose on purpose.
- After each change, watch the 👎 rate: did it fall? Keep it, or revert. That's the loop.

## Guardrails
- **One lever at a time**, so each change's effect is attributable.
- **Never auto-edit config from labels.** `calibrate.py` *suggests*; you approve. Single
  labels are noisy — only systematic patterns move the model.
- Keep raw labels + observations forever — they are the dataset.

---

_Status: Phase 0 shipped. Phase 1 (collect) starts as soon as the dedicated intake channel
is running. Phases 2–3 are gated on label volume._
