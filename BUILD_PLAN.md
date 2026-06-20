# GreenWall — 24h Build Plan

Tuned for a **product/demo-heavy team**. Strategy: the scaffold already runs end-to-end
on a synthetic bank, so your edge is the **live demo + the real Devin proof**. De-risk in
this order: (1) demo works on synthetic today, (2) bank real Devin trajectories early
because Devin is slow, (3) swap synthetic→replay, (4) polish the 5-min story.

> **Golden rule:** never let the demo depend on something running *live* that you haven't
> already captured. Bank everything; live-run only the one held-out proof.

---

## Hour 0–1 · Setup (everyone)
- [ ] `python3 pipeline.py && open dashboard/index.html` — confirm the demo runs for everyone.
- [ ] **Devin Team plan**: app.devin.ai → Team plan → coupon **`inf3r3nc3`**. Grab an API key.
- [ ] Stand up vLLM on the 8×H100 with a **dense** coder model (Llama-3.3-70B or Qwen2.5-Coder-32B; dense = Etched/Sohu-friendly). Verify prefix caching hits early.
- [ ] Claim Prime Intellect ($100) + Anthropic ($50) keys. Put all keys in `.env` (gitignored).

## Hour 1–4 · Two parallel tracks
**Track A — Systems (1 person): bank real Devin trajectories. START NOW (Devin is slow).**
- [ ] Wire `agents/orchestrator.py::_run_live` to the Devin API (see its docstring + `build_spec`).
- [ ] Feed each Devin a `RALPH.md` loop: read spec → one edit → self-check with `oracle/diff_oracle.py` → commit → repeat until invariants pass.
- [ ] Kick off N≈5 Devins on the orders task **and** 2–3 harder migration tasks. Let them run in the background; save outputs to `data/devin_runs/bank.json`.

**Track B — Demo/product (1–2 people): make the synthetic demo unmissable.**
- [ ] Polish `dashboard/index.html`: animate the curve drawing, add a "play" auto-advance of N, brand it.
- [ ] Tighten the archetype panel: clicking `clean_wrong` should land the "judge loved it, oracle caught it" beat hard.
- [ ] Add a one-screen "how it works" architecture slide (reuse the README diagram).

## Hour 4–8 · Real verifier on real outputs
- [ ] Make the Diff Oracle parse **actual Devin output** (it produces files/SQL, not clean dicts). Add a thin adapter: Devin `/out` → `{customers, orders}`.
- [ ] Add 1–2 harder tasks (more tables, a real BIRD-style schema) so N≈5 Devins genuinely disagree and the oracle matters.
- [ ] Confirm `python3 pipeline.py --mode replay` produces a curve from real Devin data.

## Hour 8–12 · The contrast (the wow moment)
- [ ] Wire a **real** LLM-judge selector: Claude ($50) scores candidates by "which migration looks best." Show it preferring the clean-but-wrong one. (Budget: a few calls per demo run — cheap.)
- [ ] Capture the curve where **oracle climbs, judge plateaus/falls** on real Devin trajectories. This is the centerpiece — bank the numbers.
- [ ] Add the **self-repair round**: feed the oracle's exact violations back to a failing Devin and show it fix the migration (tool-grounded refinement).

## Hour 12–16 · Held-out credibility
- [ ] Build a **held-out** task the demo will run live (proves it's not hardcoded). Bank a backup run in case live Devin is flaky.
- [ ] Cost axis: log tokens/$ per query; add a `$-per-correct` line so the curve has a cost x-axis option. Mark the knee.
- [ ] Stress the failure case honestly: show `subtle_wrong` slipping past total-revenue but caught by per-product revenue.

## Hour 16–20 · Polish + rehearse
- [ ] Lock the 5-min script (below). Time it. Cut anything that isn't the curve, the contrast, or the held-out run.
- [ ] Record a **backup screen capture** of a perfect run — your safety net for the live demo.
- [ ] Dry-run twice in front of someone who hasn't seen it.

## Hour 20–24 · Devpost + buffer
- [ ] Record the 5-min video (script below). Upload to Devpost.
- [ ] Write the Devpost text: problem → mechanism → the curve → "one frozen model, all inference compute" → impact ("cheaper+better as tokens drop").
- [ ] Push the repo, clean README, link the video. Leave 1h buffer for chaos.

---

## The 5-minute demo script
1. **(0:00–0:30) Problem.** "A single agent migrates this messy data and silently drops 8% of the rows / mangles a price. You don't find out until production. The expensive part isn't generating the fix — it's *verifying* it."
2. **(0:30–1:30) The swarm.** Fan out N Devin agents live (or replay). Show candidates streaming, the Diff Oracle flashing green/red on conservation invariants in real time.
3. **(1:30–3:00) The curve.** Drag N from 1→32. Oracle accuracy climbs 24%→100%. Single-shot stays flat. *Say:* "Same frozen model — every point of lift is inference compute."
4. **(3:00–4:00) WOW MOMENT.** Toggle the LLM-judge selector: it peaks then **falls below the baseline** — it keeps picking the clean-but-revenue-wrong migration. The oracle keeps climbing. "Correctness is conservation math, not an opinion."
5. **(4:00–4:30) Held-out run.** Run live on an unseen task to prove it generalizes.
6. **(4:30–5:00) Impact.** Point at the knee. "It gets better *and cheaper* as tokens get cheaper — the knee slides right. Run N=32 verified migrations per task for cents." Close on one number: **24% → 100%**.

## Don't-lose-points checklist (this judge panel specifically)
- ✅ Grounded verifier (math), not LLM-as-judge. ✅ Equal-compute baseline shown. ✅ Cost axis + knee.
- ✅ Real economic task, not GSM8K. ✅ Dense model if you invoke Etched. ✅ Demo gets *better* as inference cheapens.
- ✅ Built on Devin Teams (track requirement). ✅ Show one honest failure + rescue.
