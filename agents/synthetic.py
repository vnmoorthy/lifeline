"""
Synthetic trajectory bank.

Day-one de-risk: this lets the ENTIRE pipeline + dashboard run with zero Devin/GPU
dependency, so a demo-heavy team can build and rehearse the show immediately, then
swap in real Devin Teams trajectories via the orchestrator's replay mode.

Each candidate is a copy of the gold migration with a realistic error mode injected.
The error modes are chosen so that:
  * the Diff Oracle catches every wrong one  (-> oracle curve climbs with N)
  * an LLM-judge prefers the "clean but revenue-wrong" one  (-> judge curve falls)
  * one "subtle_wrong" passes all invariants  (-> honest oracle ceiling < 1.0)
"""
from __future__ import annotations
import copy
import random

from tasks.orders_task import load_task

# (error_mode, probability, simulated LLM-judge base score)
# An LLM judge rewards surface "cleanliness": no nulls, formatted prices, plausible
# structure. It cannot see that revenue is wrong -> it ranks clean_wrong highest.
ERROR_MODES = [
    ("correct",       0.22, 0.85),
    ("clean_wrong",   0.22, 0.95),   # mangled prices, looks immaculate -> judge bait
    ("row_drop",      0.18, 0.50),
    ("fk_violation",  0.13, 0.20),
    ("bad_dedup",     0.18, 0.70),
    ("subtle_wrong",  0.07, 0.84),   # passes all invariants; product labels swapped
]


def _apply(error_mode: str, task: dict) -> dict:
    customers = copy.deepcopy(task["gold_customers"])
    orders = copy.deepcopy(task["gold_orders"])

    if error_mode == "correct":
        pass
    elif error_mode == "clean_wrong":
        # truncate the cents on every Gadget ($25.50 -> $25.00): revenue breaks, looks clean
        for o in orders:
            if o["product"] == "Gadget":
                o["unit_price"] = 25.00
    elif error_mode == "row_drop":
        orders = [o for o in orders if o["order_id"] != "O5"]  # lost during dedup
    elif error_mode == "fk_violation":
        orders[3] = {**orders[3], "customer_id": None}         # dangling FK
    elif error_mode == "bad_dedup":
        customers = customers + [{"customer_id": "c6", "name": "ALICE SMITH", "email": "alice@x.com"}]
    elif error_mode == "subtle_wrong":
        # swap product labels of O1 <-> O7 only. TOTAL revenue is conserved (a relabel),
        # so it sails past the total-revenue invariant -- but PER-PRODUCT revenue drifts,
        # which the oracle's richer signal catches. The judge can't see any of this.
        orders[0] = {**orders[0], "product": orders[6]["product"]}
        orders[6] = {**orders[6], "product": task["gold_orders"][0]["product"]}
    else:
        raise ValueError(error_mode)

    return {"customers": customers, "orders": orders, "error_mode": error_mode}


def generate_pool(task: dict | None = None, size: int = 240, seed: int = 7) -> list[dict]:
    task = task or load_task()
    rng = random.Random(seed)
    modes = [m for m, _, _ in ERROR_MODES]
    weights = [w for _, w, _ in ERROR_MODES]
    judge_base = {m: j for m, _, j in ERROR_MODES}

    pool = []
    for i in range(size):
        mode = rng.choices(modes, weights=weights, k=1)[0]
        cand = _apply(mode, task)
        cand["agent_id"] = i
        cand["judge_score"] = round(max(0.0, min(1.0, judge_base[mode] + rng.gauss(0, 0.03))), 4)
        pool.append(cand)
    return pool


if __name__ == "__main__":
    from collections import Counter
    pool = generate_pool()
    print(Counter(c["error_mode"] for c in pool))
