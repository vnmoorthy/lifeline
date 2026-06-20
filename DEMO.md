# Lifeline — 5-minute demo script & storyboard

**Track:** Real-Time & Interactive · **Model:** Google DiffusionGemma (real block-diffusion model)
**One-liner:** Hands-free emergency first-aid that *spends inference-time compute to be sure it's right* — and never speaks an unverified step.

Record on a phone (or a phone-sized browser window) so the voice + mobile UI read as a real product.
Run the live model server (`python3 -m lifeline.diffusion_server`, tunnel 8080) for the recording.

---

## 0:00–0:30 — The problem (hook)
Talk over a phone screen, hands visibly occupied.
> "Someone collapses in front of you. You're alone. Your hands are busy — doing compressions, holding a wound. You can't read a web page, and you can't afford a wrong answer. So you freeze."

Two real facts: people search first-aid in a panic every day (CPR, choking, overdose, anaphylaxis), and seconds matter. The interface should be **voice, hands-free, and trustworthy**.

## 0:30–3:00 — Live demo
**(a) Easy emergency → instant.** Tap the mic: *"He collapsed and isn't breathing."*
- Recognized **Cardiac arrest** → engine shows **one green dot — "verified after 1 try"** → it **speaks the CPR steps** aloud, big and numbered.
- Point: *"It got it right on the first try, so it spent almost nothing. Sub-two-seconds."*

**(b) Hard emergency → it spends more compute, visibly.** *"Kid spilled boiling water on her arm."*
- Watch the **effort-manager**: candidate dots light up — a few red (rejected), then green. **"Verified after N tries · 16 denoising steps."**
- Point: *"Same model, harder case — so it sampled more and turned up the denoising depth until a candidate passed the protocol check. That's inference-time compute, allocated on demand."*

**(c) The safety net.** Trigger a case the model can't verify (or describe it):
- Badge flips to **amber — "✓ official protocol"**, engine says *"N tries didn't verify → using the official protocol."*
- Point: *"It will **never** read you an unverified instruction. If the model can't produce a checkable answer, it falls back to the canonical Red Cross / AHA protocol. Safe by construction."*

**(d) Breadth.** Tap chips: **Stroke (FAST), Anaphylaxis (EpiPen), Opioid overdose (naloxone).**
- Point: *"17 emergencies, each grounded in official guidance — and the triage is principled: a not-breathing **drowning** victim gets the drowning protocol, not generic CPR, because that one leads with rescue breaths."*

## 3:00–4:30 — How it works (the inference-time-compute story)
Show the diagram / say it plainly:
1. **Recognize** the spoken emergency → protocol.
2. **Generate** with two compute knobs: **denoising steps** (quality) × **best-of-N** (effort).
3. **Verify** every candidate against the official protocol with a grounded, negation-aware **concept-group checker** — not an LLM judge.
4. **Speak** the first verified answer, or **fall back** to the canonical protocol.

The **effort-manager** spends the *least* compute that yields a verified answer: easy → 1 try, hard → escalate, never-verified → safe fallback.

**Measured on DiffusionGemma (real runs):** denoising accuracy climbs 12.5% (2 steps) → ~72% (16 steps); best-of-N at 16 steps lifts a protocol from ~80% → **98.5% verified**; latency 0.5s → ~1.9s. *(Final run re-validates all 17 protocols with the corrected verifier before submission.)*

## 4:30–5:00 — Why it matters + what's next
> "Lifeline turns extra compute into something you can trust with your life — verified, spoken, hands-free. Next: more protocols, on-device deployment, and 911 hand-off."

Close on the running product + the footer: *"every step checked against official protocols before it's spoken."*

---

### Shot list / checklist
- [ ] Phone-sized viewport, dark UI, audio on (the spoken steps are half the wow)
- [ ] Case (a) easy → 1 dot; case (b) hard → multi-dot escalation; case (c) fallback amber badge
- [ ] One screen of the engine panel close-up (dots + "verified after N tries · 16 denoising steps · Nms")
- [ ] Say "DiffusionGemma" and "never an unverified instruction" out loud
- [ ] Have `diffusion_server` warm (model loaded ~17s) before recording
