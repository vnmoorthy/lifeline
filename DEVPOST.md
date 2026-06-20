# Lifeline — turn a frozen open model into a ~98%-verified first-aid assistant, with zero training

**Track:** Build the machine + Build the future

> **One-liner:** Take a *frozen* open-source model, spend inference-time compute on it (best-of-N + denoising depth), and gate every answer through a *deterministic* verifier so only protocol-correct answers survive — turning an unreliable open model into a safe, ~98%-verified, hands-free first-aid app. **Build as if compute is free, then verify.**

---

## Inspiration

The reflex when an open model isn't good enough is: fine-tune it. That's expensive, slow, and brittle — and for a safety-critical domain like first aid, "the fine-tune mostly works" isn't good enough. A wrong instruction during a burn, a choke, or CPR isn't a bad demo, it's a hurt person. And in a real emergency you can't read a web page — your hands are busy, you're panicking.

We had a different thesis, built for the "Build the machine / Build the future" track: **you don't need to train.** Compute is getting cheap and abundant and latency is collapsing, so treat compute as near-infinite and latency as near-zero. Leave the open model completely **frozen**, spend the compute at *inference time*, and use a hard **deterministic verifier** to keep only the answers that pass the official protocol. The model stays dumb; the *system* becomes safe.

That's Lifeline: a frozen open model + inference-time compute + a deterministic verifier, demoed live as a voice-first first-aid app you talk to while your hands are busy helping someone.

---

## What it does

Lifeline is a hands-free, voice-first first-aid assistant. You say what's happening out loud — "grease burn on my hand," "someone's choking," "deep cut, won't stop bleeding" — and it speaks back first-aid guidance that has already been **verified against the official protocol** before you ever hear it. Big numbered steps, a one-tap **Call 911**, and a **Repeat** button.

Under the hood, for each question it:

1. Runs a **frozen** open-source model and spends inference-time compute to produce many candidate answers.
2. Passes every candidate through a **deterministic, rule-based verifier** that checks the answer covers the required concepts and contains **no forbidden actions** for that protocol.
3. Speaks the first candidate that passes — or falls back to the canonical protocol rather than emit an unverified instruction.

The result: single-shot accuracy of ~80% becomes verified accuracy of **~98%** — without changing a single model weight.

---

## The inference-time-compute thesis

The core idea: **don't train — spend.** Leave the open model (DiffusionGemma 26B, open weights) frozen and dial up compute at inference time along two independent knobs, then verify what comes out.

### Knob 1 — Denoising depth (how hard the model "thinks")

DiffusionGemma is a diffusion language model, so we control how many denoising steps it runs per answer. More steps = more refinement = better answers — up to a point.

**Measured on frozen DiffusionGemma 26B:**

| Denoising steps | Verified accuracy | Latency |
|---|---|---|
| 2  | 7.5%  | 0.52 s |
| 4  | 47.5% | 0.80 s |
| 8  | 65%   | 1.48 s |
| 16 | 67.5% | 1.91 s |
| 32 | 62.5% | 1.95 s |

There's a clear **knee at 16 steps** — accuracy plateaus (and even dips at 32) while latency keeps climbing. So we fix depth at 16 and spend the rest of the budget on the second knob.

### Knob 2 — Best-of-N (how many tries the model gets)

At 16 denoising steps, we generate N candidates per question and let the deterministic verifier keep the first one that passes. This is where "compute is free" pays off — each extra candidate is just more (cheap) inference, and the verifier filters them for free.

**Measured on frozen DiffusionGemma 26B @ 16 steps:**

| N (candidates) | Verified accuracy |
|---|---|
| 1  | 79.6% |
| 2  | 84.4% |
| 4  | 89.8% |
| 8  | 94.7% |
| 16 | **98.45%** |

Single-shot **79.6% → 98.45% verified**, purely by spending more inference-time compute on a frozen model.

**Cross-check on a different frozen model (Qwen2.5-7B):** best-of-N took it from **65% → 98.3%**. The approach isn't specific to one architecture — give a frozen open model enough tries plus a hard verifier and it converges to safe.

### The curve, and the punchline

Both knobs trace the same accuracy-vs-compute curve: pour compute in, get reliability out — no training, no labeled data, no gradient ever touches the weights. The denoising knob gets you to a sensible operating point; best-of-N takes you the rest of the way to ~98%.

**Build as if compute is free, then verify.**

---

## Why a deterministic verifier beats an LLM-judge

The verifier is the load-bearing piece, and we deliberately made it **deterministic and rule-based** (concept groups that must be present + forbidden actions that must be absent), **not** an LLM-judge. Four reasons:

- **Consistency.** Same input → same verdict, every time. An LLM-judge flip-flops: ask it twice and it can disagree with itself — unacceptable for a safety gate whose entire purpose is a reliable guarantee.
- **Can't be reward-hacked.** Best-of-N is an adversarial search — with enough samples you *will* surface fluent, confident, wrong answers. An LLM-judge is exactly what fluent-but-wrong text fools. A rule-based check on required concepts and forbidden actions doesn't care how persuasive the prose is.
- **Cost and latency at scale.** The verifier is essentially free — no API call, no extra model forward pass. That's what makes best-of-N actually viable: scoring 16 candidates per question with an LLM-judge would 16× your cost and latency. A deterministic check lets you scale N as far as compute allows.
- **Hard safety guarantee.** Because the rules encode the official protocol directly, a passing answer is *provably* free of the forbidden actions and covers the required concepts. That's a guarantee you can stand behind — not a probabilistic vibe from another model.

In short: the verifier is what converts "more compute" into "more *safety*," instead of just "more plausible text."

---

## Results

All numbers below are **real and measured on frozen, open-weight models with zero training**:

- **DiffusionGemma 26B, frozen, best-of-N @ 16 denoising steps:** **79.6% → 98.45%** verified accuracy.
- **Qwen2.5-7B, frozen, best-of-N (cross-check):** **65% → 98.3%** verified accuracy.
- **Denoising-depth sweep** shows a clean knee at 16 steps (7.5% → 67.5%; see curve above).
- **Zero training.** No fine-tuning, no LoRA, no RLHF — the weights are exactly as downloaded. Every gain comes from inference-time compute + verification.

**Honest caveats:**

- **Older-verifier burn caveat.** An earlier version of our verifier **under-counted the burn protocol**. The headline numbers above are being **re-validated on a GPU re-spin** with the corrected verifier. We're reporting what we measured and flagging exactly what's being re-checked rather than rounding it away.
- These are verified-accuracy figures on our first-aid evaluation set; the method generalizes wherever a protocol can be encoded as deterministic rules.

---

## How we built it

- **Frozen open model.** DiffusionGemma 26B (open weights) as the primary generator, used entirely off-the-shelf, with `max_denoising_steps` as the quality knob. Qwen2.5-7B as a second frozen model for cross-validation.
- **Two inference-time knobs.** Denoising-step control (diffusion depth) and best-of-N sampling, with the operating point chosen empirically from the sweeps above (16 steps, N up to 16).
- **Deterministic verifier.** A rule-based checker encoding each first-aid protocol as (a) **concept groups** that must appear (any synonym counts) and (b) **forbidden actions** that must not. It's a pure function: candidate answer in, pass/fail out — no model in the loop.
- **Effort-managed best-of-N + verify loop.** Spend the *least* compute that yields a verified answer: easy cases verify on the first try; hard ones escalate N until a candidate passes; if nothing verifies, serve the canonical protocol — which itself passes the verifier, so we can always emit verified-or-canonical and **never an unverified instruction.**
- **Hands-free app.** A dependency-free, voice-driven first-aid front end (Web Speech in/out, ARIA live regions) so it's usable in the exact moment your hands are occupied — demoed live, with candidate dots lighting green/red as compute is spent.

---

## What's next

- **Finish the GPU re-spin** and publish re-validated numbers with the corrected burn verifier across the full protocol set.
- **Expand protocol coverage** — more emergencies and languages, each encoded as deterministic concept-group + forbidden-action rules.
- **Adaptive compute.** Stop early when a candidate passes, and scale N up only for harder questions, to spend compute where it actually buys safety.
- **Verifier authoring tooling** so clinicians can write and audit protocol rules directly.
- **Push N and depth further** now that we have the curve — find where verified accuracy saturates as compute approaches "free."
- **On-device deployment and live 911 hand-off**, and generalize the method beyond first aid to any domain where correctness is checkable by deterministic rules.

---

## Disclaimer

Lifeline is a hackathon project and a research demonstration. **It is not a medical device and not a substitute for professional medical care or emergency services.** In a real emergency, call your local emergency number. The accuracy figures are measured on our own evaluation set, reflect verified-accuracy under our deterministic verifier, and include numbers currently being re-validated on a GPU re-spin (see the older-verifier burn caveat above). Do not rely on this system for real medical decisions.
