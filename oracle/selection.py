"""
Selection policies + the bootstrap scaling curve.

The headline result: as the number of trajectories N grows, the ORACLE selector's
true accuracy climbs monotonically, while the LLM-JUDGE selector peaks then DROPS
(it increasingly picks the clean-but-revenue-wrong candidate). single_shot is flat.

Each candidate is expected to carry precomputed fields (added in pipeline.py):
  _true_acc, _oracle_pass, _oracle_score, judge_score
"""
from __future__ import annotations
import json
import random
import statistics


def _sig(cand: dict) -> str:
    orders = sorted(
        (o.get("order_id"), o.get("customer_id"), o.get("product"),
         o.get("qty"), round(float(o.get("unit_price", 0) or 0), 2), o.get("order_date"))
        for o in cand.get("orders", []) or []
    )
    custs = sorted(
        (c.get("customer_id"), c.get("name"), c.get("email"))
        for c in cand.get("customers", []) or []
    )
    return json.dumps([orders, custs], default=str)


# ---- selectors: take a list of candidates, return the chosen one ----
def select_single_shot(sample):
    return sample[0]  # sample is already a random subset -> equivalent to a random pick


def select_majority(sample):
    groups = {}
    for c in sample:
        groups.setdefault(_sig(c), []).append(c)
    best = max(groups.values(), key=len)
    return best[0]


def select_llm_judge(sample):
    return max(sample, key=lambda c: c["judge_score"])


def select_oracle(sample):
    passers = [c for c in sample if c["_oracle_pass"]]
    if passers:
        return max(passers, key=lambda c: c["_oracle_score"])
    return select_llm_judge(sample)  # conservative fallback: never worse than judge


SELECTORS = {
    "single_shot": select_single_shot,
    "majority": select_majority,
    "llm_judge": select_llm_judge,
    "oracle": select_oracle,
}


def bootstrap_curve(pool, selector, ks, resamples=400, seed=11):
    """For each k in ks, mean true accuracy of the selector over many random k-subsets."""
    rng = random.Random(seed)
    curve = []
    for k in ks:
        accs = []
        for _ in range(resamples):
            sample = rng.sample(pool, k)
            chosen = selector(sample)
            accs.append(chosen["_correct"])  # binary: was the SELECTED migration fully correct?
        curve.append(round(statistics.mean(accs), 4))
    return curve


def find_knee(curve, ks, eps=0.02):
    """Smallest k whose marginal gain drops below eps (diminishing returns)."""
    for i in range(1, len(curve)):
        if curve[i] - curve[i - 1] < eps:
            return ks[i]
    return ks[-1]
