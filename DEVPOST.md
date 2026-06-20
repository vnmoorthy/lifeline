# Lifeline — verified, hands-free emergency first aid on DiffusionGemma

> Spend inference-time compute to be *sure* it's right. Never speak an unverified step.

**Track:** Real-Time & Interactive

## Inspiration
In a real emergency you can't read a web page. Your hands are busy and bloody, you're panicking,
and a wrong instruction can kill. People still pull out a phone and frantically search "how to do
CPR / Heimlich / what to do for an overdose." We wanted the opposite of a search box: something you
**talk to**, that answers **out loud and hands-free**, and that you can **trust** because every step
is checked against official protocols before it's spoken.

## What it does
Lifeline is a voice-first first-aid assistant covering **17 emergencies** (cardiac arrest, choking,
severe bleeding, opioid overdose, burns, anaphylaxis, stroke, seizure, heart attack, drowning, low
blood sugar, heat stroke, hypothermia, poisoning, head injury, nosebleed, fracture).

You say what's happening. Lifeline recognizes the emergency, generates guidance on **Google's
DiffusionGemma**, **verifies** each candidate answer against the official protocol, and **speaks**
the steps — big, numbered, with a one-tap **Call 911** and a **Repeat** button. If the model can't
produce a verifiable answer, it **falls back to the canonical protocol** rather than guess.

## How inference-time compute is the whole point
This is a Real-Time, inference-time-compute project. Lifeline has three compute knobs and an
effort-manager that decides how much to spend:

1. **Denoising steps** — DiffusionGemma is a block-diffusion model; more denoising = higher quality
   (and more latency). We measured the curve and pick the knee.
2. **Best-of-N** — sample several candidates in parallel; keep one that verifies.
3. **Grounded verifier** — a negation-aware **concept-group checker** (not an LLM judge): each
   protocol requires every essential concept (any synonym counts) and forbids dangerous actions.

The **effort-manager spends the least compute that yields a verified answer**: an easy emergency
verifies on the first try (instant); a hard one escalates best-of-N until a candidate passes; if
nothing verifies, it serves the official protocol. The UI makes this *visible* — candidate dots
light green/red as compute is spent ("verified after N tries · 16 denoising steps").

**Safety invariant:** every canonical fallback itself passes the verifier, so Lifeline can always
emit a verified-or-canonical answer and **never an unverified instruction**.

## Results (measured on DiffusionGemma)
- Denoising accuracy: **12.5%** (2 steps) → **~72%** (16 steps).
- Best-of-N at 16 steps lifts a protocol from **~80% → 98.5%** verified.
- Latency **0.5s → ~1.9s** across the compute range.

*(These are from real runs on the original protocol set. We then fixed a negation bug in the
verifier — it was wrongly rejecting correct "do not apply ice" answers — and added 11 protocols;
the final pre-submission run re-validates all 17 with the corrected verifier.)*

## How we built it
- **Model:** `DiffusionGemmaForBlockDiffusion` (transformers), single-A100 placement
  (`device_map={'':0}`), `max_denoising_steps` as the quality knob.
- **Engine:** Python — `recognize` (principled triage ladder) → adaptive best-of-N → `verify`
  (concept groups + clause-scoped negation) → speak or fall back.
- **UI:** dependency-free mobile-first HTML/JS — Web Speech for input + spoken output, ARIA live
  regions, reduced-motion support, the live effort-manager visual.
- **Multi-agent build:** we used parallel agents (Gastown) to design + medically cross-check the 12
  new protocols, and an adversarial critic loop (Ralph) to harden recognition and the verifier.
- **Tested without a GPU:** `tests/test_lifeline.py` + `check.sh` gate recognition routing, the
  safety invariant (every fallback self-verifies), and verifier safety.

## Challenges
- vLLM can't serve the diffusion architecture → raw HF transformers + correct single-GPU placement.
- A negation-blind verifier rejected correct advice and inflated "hard" difficulty → clause-scoped
  negation handling.
- Triage priority: a not-breathing **overdose** or **drowning** victim must get its own protocol
  (which leads with naloxone / rescue breaths), not generic CPR.

## What's next
More protocols and languages, on-device deployment, live 911 hand-off, and confidence-calibrated
follow-up questions ("is the person breathing?").

## Disclaimer
Lifeline is decision support, not a medical device, and not a replacement for emergency services.
Always call 911.
