# Lifeline on DiffusionGemma — REAL denoising-compute results

**Model:** `unsloth/diffusiongemma-26B-A4B-it` — Google's block-diffusion model (released ~early
June 2026, ~10 days old). Run via HF transformers (`DiffusionGemmaForBlockDiffusion`) on one
A100-80GB. **Inference-time-compute knob = `max_denoising_steps`** (actual diffusion refinement
passes — the real thing, not best-of-N). **Verifier:** grounded concept-group protocol check.

## The headline: more denoising → more correct (measured, real output)

| denoising steps | verified-correct accuracy |
|---|---|
| 2 | **12.5%** (output is garbled) |
| 4 | 50% |
| 8 | 62.5% |
| 16 | **71.9%** (peak) |
| 32 | 62.5% (plateau) |

- **Native effort-manager** (the model's own `confidence_threshold` early-stop): **68.75%** — it
  stops denoising early on easy emergencies, keeps going on hard ones.
- Honest ceiling ~72%: a small fast model + a *strict* grounded verifier + genuinely hard
  multi-factor cases (burns, post-tourniquet bleeding). We did NOT loosen the verifier to inflate it.

## The visceral demo (same prompt, "not breathing", different denoising budgets)

**4 steps — under-denoised garbage (verified=False):**
> "…3. Call Call 111 immediately… 5. Place the of of hand hand the center of the chest… Push and
> fast fast at at at at at0000000000… chest chest recoil…"

**32 steps — coherent, verified-correct CPR (verified=True):**
> "1. Call 911 immediately or tell someone else to. 2. Lay the person flat… 3. Place the heel of
> one hand in the center of their chest… 5. Push hard and fast at a rate of 100-120 beats per
> minute. 6. Allow the chest to recoil completely… 7. Continue until medical help arrives."

Watching the answer resolve from noise into correct, verified first-aid **as you add denoising
compute** is the live wow — and it's unique to a diffusion model.

## Reproduce
```bash
# on the GPU box (one A100-80GB), model cached:
GEN_TIMEOUT=90 SAMPLES=4 STEPS_GRID=2,4,8,16,32 python3 -m lifeline.diffusion_run
# one-off qualitative demo:
python3 -m lifeline.diffusion_run --test      # prints garbled@4 vs correct@32
```

## Note vs the Qwen baseline
`RESULTS.md` has a cleaner best-of-N curve (65%→98%) on Qwen — but that's a standard LM run
autoregressively. **This** is the genuine fresh diffusion model with the real denoising knob —
more novel and more on-theme, at the cost of a noisier, lower-ceiling curve. Lead the demo with
DiffusionGemma (novelty + the garbled→correct moment); cite Qwen best-of-N as the comparison.
