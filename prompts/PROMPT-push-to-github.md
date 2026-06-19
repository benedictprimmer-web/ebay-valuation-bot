# Paste into Claude Code to push the latest changes

Run this from inside your local clone of `benedictprimmer-web/ebay-valuation-bot`
(the folder that has `.git`). Claude Code uses your own write credentials, so it can
push where the Cowork connector can't.

---

Push the latest valbot work to GitHub. Steps, in order:

1. First copy in any changed files from my Cowork working folder
   ("Claude Cowork/OUTPUTS/eBay Valuation Bot") if this clone is separate — match the
   tree exactly. Key changed/new paths from sessions 5–6:
   - `config.yaml` (new `sectors` block + `active_sector`; business-seller + ratio fixes)
   - `src/valbot/config.py` (`apply_sector` + `_deep_merge`)
   - `src/valbot/targets.py`, `targets.py` (targets mode, Option 3)
   - `src/valbot/formatting.py` (`format_targets`, `target_to_dict`)
   - `run.py`, `targets.py` (`--sector` flag)
   - `src/valbot/camera.py` (camera identity matcher), `src/valbot/calibrate.py` + `calibrate.py` (calibration)
   - `tests/test_targets.py`, `tests/test_sectors.py`, `tests/test_camera.py`, `tests/test_calibrate.py` (new)
   - `data/watchlist.example.csv`, `data/mock_cameras.json` (new)
   - `prompts/` (push + next-session prompts)
   - `HANDOFF-session-5.md`, `HANDOFF-session-6.md`
   - `.gitignore` (ignores `data/targets_results.json`)
   - new docs folders `research/` and `reports/` (see step 4)

2. Run the test suite and only continue if it's green:
   `python -m pytest -q`  (expect 38 passing)

3. Stage everything, commit, push to `main`:
   `git add -A`
   `git commit -m "Sessions 5–6: targets mode, sector profiles, fee/ratio fixes, research"`
   `git push origin main`

4. Decision before you push: `research/` (research prompts + results) and `reports/`
   (the PDFs + HTML) are documentation, not code. If you'd rather keep the repo
   code-only, add them to `.gitignore` instead of committing. Ask me which I prefer if
   unsure; default to committing them so the repo is self-documenting.

5. Confirm the push landed and paste me the commit URL.
