# ✚ Lifeline — verified, hands-free emergency first aid

A voice-first first-aid assistant that **spends inference-time compute to be sure it's right**, and
**never speaks an unverified step**. Built on Google's **DiffusionGemma** (real block-diffusion model).

*Decision support, not a medical device. Always call 911.* · **Track:** Real-Time & Interactive

---

## What it does
Say what's happening ("he collapsed and isn't breathing", "my kid spilled boiling water"). Lifeline
recognizes the emergency, generates guidance on DiffusionGemma, **verifies** each candidate against the
official protocol, and **speaks** large numbered steps — with one-tap **Call 911** and **Repeat**.
**17 emergencies:** cardiac arrest, choking, severe bleeding, opioid overdose, burns, anaphylaxis,
stroke, seizure, heart attack, drowning, low blood sugar, heat stroke, hypothermia, poisoning, head
injury, nosebleed, fracture.

## The inference-time-compute idea
Three compute knobs + an effort-manager that spends the *least* compute that yields a verified answer:
1. **Denoising steps** — DiffusionGemma's quality/latency knob.
2. **Best-of-N** — sample candidates in parallel; keep one that verifies.
3. **Grounded verifier** — a negation-aware concept-group checker (not an LLM judge): every protocol
   requires its essential concepts (any synonym) and forbids dangerous actions.

Easy emergency → verifies on the first try (instant). Hard → escalate best-of-N. Nothing verifies →
fall back to the canonical protocol. **Safety invariant:** every canonical fallback itself passes the
verifier, so the system can always emit a verified-or-canonical answer — never an unverified one.

## Run it

**Local preview — no GPU** (real UI, mock engine):
```bash
python3 -m lifeline.mock_ui      # http://localhost:8090
```

**Tests / pre-flight — no GPU:**
```bash
./check.sh                       # syntax + recognition routing + safety invariant
```

**The real product — on a GPU** (1× A100-80GB):
```bash
export HF_TOKEN=hf_...            # your (rotated) token
bash scripts/setup_diffusion_gpu.sh
scp -r lifeline <box>:~/          # then on the box:
python3 -m lifeline.diffusion_server         # port 8080
# from your Mac: ssh -L 8080:localhost:8080 <box>  ->  http://localhost:8080
```

## Layout
| File | Role |
|------|------|
| `lifeline/triage.py` | recognition (priority ladder + negation) · canonical fallback steps · names |
| `lifeline/real_run.py` | the grounded verifier (`verify`) · protocol concept-groups · eval scenarios |
| `lifeline/ui_page.py` | the mobile-first accessible voice UI (single source of truth) |
| `lifeline/diffusion_server.py` | the live product on DiffusionGemma (the GPU server) |
| `lifeline/mock_ui.py` | local GPU-free preview (same `/ask` contract) |
| `tests/test_lifeline.py`, `check.sh` | GPU-free test gate |
| `DEMO.md`, `DEVPOST.md` | demo storyboard + submission writeup |
| `DIFFUSION_RESULTS.md`, `RESULTS.md` | measured results from real runs |

## Results (measured on DiffusionGemma)
Denoising accuracy 12.5% (2 steps) → ~72% (16 steps); best-of-N at 16 steps lifts a protocol from
~80% → **98.5% verified**; latency 0.5s → ~1.9s. *(Final pre-submission run re-validates all 17
protocols with the corrected verifier.)*

## How it was built
Parallel multi-agent design (Gastown) generated + medically cross-checked the protocols; an adversarial
critic loop (Ralph) hardened recognition and the verifier. Everything except live model accuracy is
testable without a GPU.
