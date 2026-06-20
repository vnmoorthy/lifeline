"""
The controller (the nozzle): decide how much compute each question deserves.

Cheap probe: generate a small k of candidates, execute them, measure how much they AGREE
(fraction in the plurality result cluster). High agreement => easy => stop cheap. Low
agreement => hard => escalate to large N. This is the difficulty-conditioned allocation —
spend inference only where it changes the answer. The thresholds are where your measured
two-regime cliff goes; tune them on a dev split.
"""
from __future__ import annotations

# agreement >= HIGH  -> trivial, accept the probe consensus (N = probe_k)
# agreement >= MID   -> escalate modestly
# else               -> hard, go wide
HIGH, MID = 0.85, 0.55
PROBE_K = 4
N_MID, N_HARD = 8, 32


def decide_n(probe_agreement: float) -> tuple[int, str]:
    """Return (target_total_N, regime_label) given the probe agreement."""
    if probe_agreement >= HIGH:
        return PROBE_K, "easy"
    if probe_agreement >= MID:
        return N_MID, "medium"
    return N_HARD, "hard"
