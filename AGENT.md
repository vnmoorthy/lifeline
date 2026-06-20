# AGENT.md — Lifeline development guide (for autonomous coding agents)

Lifeline is a hands-free, verified emergency first-aid voice assistant on Google DiffusionGemma.
Read this before changing anything. Used by Ralph (`prompt.md` + `prd.json` + `ralph.sh`).

## Architecture
| File | Role | Change policy |
|------|------|---------------|
| `lifeline/triage.py` | `recognize()` priority ladder + negation, `CANON`, `PROTO_NAME`, `CUES` | **Hardened/converged. Treat as read-only** unless a story explicitly targets it with a new failing test. |
| `lifeline/real_run.py` | `verify()` grounded checker, `PROTO`, `SCENARIOS`, `PROMPT` | **Hardened/converged. Read-only** unless a story explicitly targets it with a new failing test. |
| `lifeline/ui_page.py` | the single-file voice UI (`PAGE`) | Editable for UX stories. Preserve every element id + the `/ask` contract + a11y + reduced-motion. |
| `lifeline/diffusion_server.py` | live product server (GPU) | Editable; keep the `/ask` JSON shape. |
| `lifeline/mock_ui.py` | GPU-free preview (same `/ask` contract) | Editable. |
| `tests/test_lifeline.py`, `check.sh` | the test gate | Add tests; never weaken existing ones. |

## The `/ask` contract (UI ↔ server) — do not break
Response JSON: `{recognized, protocol, key, regime, n_used, denoising_steps, candidates:[{ok,preview}],
verified, fallback, answer:[step,…], latency_ms, spoken?}`.

## UI element ids the JS depends on (preserve)
`mic, miclbl, txt, go, chips, you, stage, status, elbl, ecount, dots, shim, fill, stepsCard,
stepsH, steps, actions, repeat, reset, live, main`.

## Invariants (must always hold)
- Every `CANON[key]` passes `verify(" ".join(CANON[key]), key)` (safe fallback always self-verifies).
- The UI never shows an unverified step: it shows a model answer that passed `verify`, or the canonical fallback.
- Accessibility: ARIA live regions, screen-reader read-back of input, `prefers-reduced-motion` respected.
- Dependency-free (stdlib Python; vanilla single-file HTML/JS, no build step).

## How to validate a change
1. `./check.sh` must pass (syntax + 54 assertions). Never weaken it.
2. `python3 -m py_compile lifeline/*.py`.
3. For UI stories: preview with `python3 -m lifeline.mock_ui` (port 8090) and visually confirm.
4. Keep diffs additive and localized. One story per loop.

## Conventions
- Dark clinical theme via CSS vars in `ui_page.py` (`--bg,--red,--green,--amber,--accent`…).
- No new pip dependencies. No external network in the UI except `/ask` and `tel:`.
