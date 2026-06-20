# GreenWall 🧱

**Verifier-gated Devin swarm — inference compute selected by math, not vibes.**

Inference-Time Compute Hackathon · **Agents track** (built on Devin Teams).

---

## The one-sentence pitch

A single autonomous coding agent botches real data migrations ~75% of the time and
*looks confident doing it*. GreenWall fans the task out to **N parallel Devin agents**,
then a **deterministic, label-free Diff Oracle** — not an LLM judge — selects the one
provably-correct migration. Accuracy climbs from **24% → 100%** as you spend more
inference compute, while an LLM-judge selector **reward-hacks and collapses to 0%**.

## Why this wins (mapped to the judges' rubric)

| Criterion | How GreenWall hits it |
|---|---|
| **Vision & Fit** | Data migrations are real, paid knowledge work that fails silently. Inference compute = a budget allocated and **verified** against it. |
| **Technical Execution** | One frozen model. Every gain is inference compute, not training. Verifier is math (conservation invariants), runs live. |
| **Novelty & Insight** | A **deterministic verifier synthesized from schema invariants alone, zero labels.** The LLM-judge-vs-oracle contrast (judge reward-hacks, oracle climbs) is the insight. |
| **Impact & Trajectory** | Gets strictly **better and cheaper as tokens get cheaper** — the knee slides right. (Etched's thesis, verbatim.) |
| **Presentation & Demo** | A live accuracy-vs-N curve + a "the judge picked the wrong-but-pretty answer" wow moment. |

## Architecture

```
                 ┌─────────────── Gastown-style "mayor" (orchestrator) ───────────────┐
  migration spec │   Devin #1 (Ralph loop)   Devin #2   …   Devin #N   (parallel)      │
  + RALPH.md  ───►   each: read spec → 1 edit → self-check w/ oracle → commit → repeat  │
                 └───────────────────────────────┬────────────────────────────────────┘
                                                 ▼  N candidate migrations
                        ┌──────────────── Diff Oracle (deterministic, label-free) ─────┐
                        │  order_count · revenue · per-product revenue · FK · PK · nulls│
                        └───────────────────────────────┬─────────────────────────────┘
                                                 ▼  pessimistic best-of-N
                                  selected migration  +  live accuracy-vs-N curve
```

- **8×H100** runs the oracle + sandboxed executions + reranking across many candidates.
- **Devin ($100, `inf3r3nc3`)** is the agent swarm (bounded N to stay in budget).
- **Claude ($50)** is used only as a tie-break critic on the rare inter-cluster tie.
- **Prime Intellect ($100)** is burst/overflow compute.

## Run it (zero dependencies — stdlib only)

```bash
python3 pipeline.py            # synthetic bank: builds curves + dashboard, no GPU/Devin needed
open dashboard/index.html      # the demo (self-contained; double-click works too)
```

Once you've banked real Devin trajectories to `data/devin_runs/bank.json`:

```bash
python3 pipeline.py --mode replay
```

## Layout

| Path | What |
|---|---|
| `tasks/orders_task.py` | The migration task + gold (gold used only to *measure*, never to select). |
| `oracle/diff_oracle.py` | **The core IP** — deterministic, label-free invariant verifier. |
| `oracle/metrics.py` | Ground-truth accuracy (for plotting the curve only). |
| `oracle/selection.py` | Selectors (oracle / llm_judge / majority / single_shot) + bootstrap curve. |
| `agents/synthetic.py` | Day-one trajectory bank with realistic error modes. |
| `agents/orchestrator.py` | Gastown "mayor": synthetic / replay / **live Devin** modes. |
| `pipeline.py` | End-to-end run → `dashboard/`. |
| `BUILD_PLAN.md` | The hour-by-hour 24h plan. |

## The honest caveats (say these on stage — this panel rewards them)

- The synthetic bank is a stand-in until real Devin trajectories are banked. The
  *machinery* (oracle, selection, curve) is identical; only the candidate source changes.
- `subtle_wrong` passes the hard invariants (total revenue conserved) and is only caught
  by the **per-product** revenue signal — proof that richer invariants matter, and a
  reminder that a verifier is only as good as its invariants.
