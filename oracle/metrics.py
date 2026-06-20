"""
Ground-truth accuracy. Used ONLY to plot the demo curves (the y-axis), never to
select a candidate. Selection is the oracle's job; this just tells us, after the
fact, how good the selected migration actually was.
"""
from __future__ import annotations


def _eq(a, b) -> bool:
    fa, fb = None, None
    try:
        fa, fb = float(a), float(b)
    except (TypeError, ValueError):
        pass
    if fa is not None and fb is not None:
        return abs(fa - fb) < 1e-6
    return str(a).strip() == str(b).strip()


def true_accuracy(candidate: dict, task: dict) -> float:
    """Fraction of correctly-reproduced cells across both tables, in [0, 1]."""
    gold_o = {o["order_id"]: o for o in task["gold_orders"]}
    gold_c = {c["customer_id"]: c for c in task["gold_customers"]}
    cand_o = {o.get("order_id"): o for o in candidate.get("orders", []) or []}
    cand_c = {c.get("customer_id"): c for c in candidate.get("customers", []) or []}

    fields_o = ["customer_id", "product", "qty", "unit_price", "order_date"]
    fields_c = ["name", "email"]

    total = correct = 0

    for oid, g in gold_o.items():
        c = cand_o.get(oid)
        for f in fields_o:
            total += 1
            if c is not None and _eq(c.get(f), g[f]):
                correct += 1
    # penalize extra/spurious orders
    total += max(0, len(cand_o) - len(gold_o)) * len(fields_o)

    for cid, g in gold_c.items():
        c = cand_c.get(cid)
        for f in fields_c:
            total += 1
            if c is not None and _eq(c.get(f), g[f]):
                correct += 1
    total += max(0, len(cand_c) - len(gold_c)) * len(fields_c)

    return correct / total if total else 0.0


def is_correct(candidate: dict, task: dict) -> float:
    """Binary business metric: is the migration FULLY correct? (1.0 / 0.0)."""
    return 1.0 if true_accuracy(candidate, task) >= 0.999 else 0.0
