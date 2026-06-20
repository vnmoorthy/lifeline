# Lifeline — measured results (REAL model output)

**Model:** Qwen/Qwen2.5-7B-Instruct, served with vLLM (TP=2) on Lambda 8×A100.
**Knob:** best-of-N samples (inference-time compute). **Verifier:** grounded concept-group
protocol check (no LLM judge). Run: `python3 -m lifeline.real_run` (via SSH tunnel to the box).

## Headline (8 emergencies, pool N=24, real model output)

| N (samples) | accuracy |
|---|---|
| 1 (single answer) | **65%** |
| 2 | 79% |
| 4 | 89% |
| 8 | 95% |
| 16 | **98%** |

- **Single answer is only ~65% reliable** on emergency first-aid.
- **Best-of-16 + verification → 98%.** More inference compute → more reliable, on real output.
- **Effort-manager: 94.5% accuracy at avg N=4.4 — 96% of best accuracy using only 27% of the samples.**

## Adaptive allocation (compute spent where it's needed)

| emergency | 1-shot pass | effort-manager N | regime |
|---|---|---|---|
| choking | 96% | 1 | routine (instant) |
| moderate bleeding | 100% | 1 | routine |
| overdose | 79% | 2 | routine |
| severe bleeding | 88% | 2 | routine |
| CPR / not breathing | 67% | 3 | moderate |
| overdose (pregnant, fentanyl) | 46% | 4 | moderate |
| choking → unconscious | 33% | 6 | moderate |
| burn | 12% | 16 | critical |

The controller spends 1 sample on easy cases and up to 16 on the ones the model gets wrong
most often (burns, ambiguous multi-factor cases) — the thesis, measured.

## Reproduce
```bash
# on the GPU box: vllm serve Qwen/Qwen2.5-7B-Instruct --tensor-parallel-size 2 --host 0.0.0.0 --port 8000
# tunnel: ssh -L 8000:localhost:8000 ubuntu@<ip>
LIFELINE_BASE_URL=http://localhost:8000/v1 LIFELINE_MODEL=Qwen/Qwen2.5-7B-Instruct POOL_N=24 python3 -m lifeline.real_run
python3 -m lifeline.build_real_dashboard   # -> dashboard_lifeline/real.html
```
