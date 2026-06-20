"""
The effort-manager (your adaptive-compute research, applied to a crisis).

Given a strict LATENCY budget, decide how many refinement passes THIS emergency deserves:
a cheap probe estimates how hard/ambiguous it is, then we allocate just enough passes to
be confident — few on routine cases, many on ambiguous multi-factor ones. Routine answers
stay instant; hard cases get more thinking; nothing blows the latency budget.
"""
from __future__ import annotations
import random

PER_PASS_MS = 35          # one refinement pass on a fast diffusion model (proxy)
LATENCY_BUDGET_MS = 1000  # speak within ~1 second
MAX_PASSES = LATENCY_BUDGET_MS // PER_PASS_MS
LADDER = [2, 4, 8, 16, 24]  # escalation rungs, all within the latency budget
PROBE_SAMPLES = 5
TARGET_CONF = 0.9


def latency_ms(passes: int) -> int:
    return passes * PER_PASS_MS


def decide_passes(scenario, protocol, verifier_is_correct, generate_fn, rng: random.Random):
    """Anytime escalation: start cheap, add refinement passes only until the answer is
    confidently protocol-correct (or the latency budget is hit). Easy emergencies stop
    early; ambiguous ones escalate. Returns (passes, regime, confidence)."""
    chosen, conf_at = LADDER[-1], 0.0
    for k in LADDER:
        if k * PER_PASS_MS > LATENCY_BUDGET_MS:
            break
        hits = sum(1 for _ in range(PROBE_SAMPLES)
                   if verifier_is_correct(generate_fn(scenario, protocol, k, rng), protocol))
        conf = hits / PROBE_SAMPLES
        chosen, conf_at = k, conf
        if conf >= TARGET_CONF:
            break
    regime = "routine" if chosen <= 4 else ("moderate" if chosen <= 8 else "critical")
    return chosen, regime, round(conf_at, 2)
