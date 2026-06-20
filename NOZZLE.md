# Nozzle — the build

**Provably-right answers — compute aimed by the controller, verified by the database.**

A real-time analytics copilot. Ask a business question in English; a difficulty
**controller** decides how much compute it deserves; candidate SQL is generated wide,
**executed against a real database** (the oracle — not an LLM judge), and the answer is
the verified consensus. The hero artifact is a **measured** accuracy-vs-compute curve.

On-theme line (say it in the first 15s):
> *"I don't want less inference — I want more inference aimed correctly.
> The firehose is the GPU; my controller is the nozzle."*

## Status
- ✅ Real SQLite business DB + 10 NL questions with gold answers ([nozzle/db.py](nozzle/db.py))
- ✅ Execution verifier + consensus selection ([nozzle/verifier.py](nozzle/verifier.py))
- ✅ Difficulty controller (probe→N) ([nozzle/controller.py](nozzle/controller.py))
- ✅ End-to-end run → measured curve + dashboard ([nozzle/run.py](nozzle/run.py))
- ✅ Model adapter: vLLM (Lambda) / Anthropic / smoke ([nozzle/generate.py](nozzle/generate.py))
- ⬜ **The one thing that decides win/lose: run it against a real model** (below)

## Make the curve REAL (do this first — Hour 0)
The DB/verifier/consensus/controller math is all real; only the *generator* needs a real
model. Stand up vLLM on Lambda with a dense coder model, then:

```bash
export VLLM_BASE_URL="http://<lambda-ip>:8000/v1"
export VLLM_MODEL="Qwen/Qwen2.5-Coder-32B-Instruct"
python3 -m nozzle.run --backend vllm
open dashboard_nozzle/index.html      # banner turns green: "REAL RUN"
```

Until then, `--backend smoke` runs the pipeline offline but stamps every number
**SIMULATED** — never present those.

## Why it wins (the honest version)
- **Unforgeable verifier** — execution, not opinion. This panel distrusts LLM-judges.
- **Measured curve** — accuracy climbs with compute, single-shot flat. Real numbers.
- **Controller = your moat** — near-max accuracy at a fraction of the samples, justified by
  your two-regime cliff. The part no other solo can fabricate.
- **Etched-aligned** — more inference aimed correctly; the knee slides right as tokens cheapen.

## 5-min demo
1. Ask an easy question → 1 sample, instant. Ask a hard one → watch N erupt, the verifier
   strike out wrong candidates, the right answer land.
2. The measured accuracy-vs-N curve climbs; single-shot baseline flat below.
3. The controller star: same accuracy as fixed best-of-N at a fraction of the compute.
4. State which numbers are live. Close on the nozzle line + Etched knee.

## Contingency gates (from the stress-test)
- **By Hour 4–6:** if you don't have one *real* (vllm) curve banked, stop polishing and
  keep the working text demo — do not chase a live voice loop.
- **Voice shell is optional and LAST** (~3h): pre-recorded clips → offline ASR → existing
  text engine → one cached TTS call. It decides track (Real-Time vs Applied-AI); the engine
  is identical either way.
