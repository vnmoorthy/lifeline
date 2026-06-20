# Devin task — Lifeline evaluation suite + dashboard

Build a standalone **evaluation suite** for Lifeline (a verified emergency first-aid assistant).
This is **additive only**. Work on a branch and open a PR.

## Hard guardrails (do not violate)
- **Do NOT modify** `lifeline/triage.py`, `lifeline/real_run.py` (the `PROTO`/`verify` logic),
  `lifeline/ui_page.py`, or `lifeline/diffusion_server.py`. These are hardened and tested — treat
  them as read-only APIs. Import from them; never edit them.
- `./check.sh` must still pass unchanged after your work (`python3 tests/test_lifeline.py`).
- New code is **standard-library only** for the GPU-free parts (no new pip deps). The dashboard is
  a single self-contained HTML file (vanilla JS, no build step).
- Everything except the live-model accuracy run must work **without a GPU**.

## What exists (use, don't change)
- `lifeline.triage.recognize(text) -> protocol key | None`, plus `CANON`, `PROTO_NAME`, `CUES`.
- `lifeline.real_run.verify(text, key) -> bool`, plus `PROTO`, `SCENARIOS`, `PROMPT`.
- `lifeline.diffusion_run` generates from DiffusionGemma at a given `max_denoising_steps` (GPU only).
- Result JSONs already live in `dashboard_lifeline/`; mirror that style.

## Deliverables

### 1. `lifeline/benchmark.py` — recognition benchmark (GPU-free)
- Programmatically generate a large, varied test set (target **300+** phrasings) covering all 17
  protocols: realistic bystander wording, ASR-style messiness, negations ("no chest pain"),
  multi-symptom sentences, and a set of true-negatives (non-emergencies that must return `None`).
- Run `recognize()` over the set; compute per-protocol precision/recall, the overall confusion
  matrix, and the false-negative / false-positive lists.
- Write `dashboard_eval/recognition.json`. Print a summary table. Add a `--fail-under <pct>` flag
  for CI.

### 2. `lifeline/eval_accuracy.py` — best-of-N + denoising accuracy (GPU, but degrades gracefully)
- For all `SCENARIOS`, sweep `max_denoising_steps` and best-of-N; measure verified accuracy with
  the **current (corrected) `verify`**, plus latency and per-protocol fallback rate.
- Write `dashboard_eval/accuracy.json`. If no GPU/model is reachable, exit cleanly with a clear
  message and write nothing (do not crash, do not fake numbers).

### 3. `dashboard_eval/index.html` — self-contained dashboard
- Loads the two JSONs and charts: recognition accuracy + confusion matrix; the denoising curve;
  best-of-N accuracy vs N; per-protocol fallback rate; latency. Vanilla JS/SVG or a single CDN
  charting lib. Dark theme to match the product. No server needed (double-click to open).

### 4. `tests/test_benchmark.py` + wire into `check.sh`
- A fast test asserting the recognition benchmark runs and overall accuracy is above a threshold
  (pick a defensible number from the actual run). Keep total `check.sh` runtime reasonable.

## Acceptance criteria
- `./check.sh` passes (existing 54 assertions + your new ones).
- `python3 -m lifeline.benchmark` runs GPU-free and writes `dashboard_eval/recognition.json`.
- `dashboard_eval/index.html` opens standalone and renders the charts from the JSONs.
- No edits to the four hardened files. PR description summarizes results + how to reproduce.
