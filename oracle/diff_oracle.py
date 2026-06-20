"""
The Diff Oracle: a DETERMINISTIC, LABEL-FREE verifier for data migrations.

This is the core IP of GreenWall. It scores a candidate migration purely against
conservation invariants derived from the SOURCE data + target schema -- no ground
truth, no LLM judge. A correct migration must satisfy every hard invariant.

Why this matters for the hackathon: the judge panel distrusts LLM-as-judge on sight.
Here the verifier is math. Selection driven by this oracle climbs monotonically with
N, while an LLM-judge selector reward-hacks and falls. That contrast is the demo.
"""
from __future__ import annotations

REV_EPS = 0.005  # revenue tolerance in dollars

# The hard invariants that must ALL pass for a migration to be accepted.
HARD_INVARIANTS = [
    "order_count",      # no orders lost or duplicated
    "revenue",          # total revenue conserved (catches price/type mangling)
    "fk_integrity",     # every order points at a real customer; no null FKs
    "pk_unique",        # primary keys unique
    "customer_count",   # customers correctly de-duplicated
    "no_null",          # no null/empty required fields
]


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def check_invariants(candidate: dict, task: dict) -> dict:
    """Return {invariant_name: {"pass": bool, "detail": str}} for every invariant."""
    customers = candidate.get("customers", []) or []
    orders = candidate.get("orders", []) or []
    out = {}

    # order_count
    n_orders = len(orders)
    out["order_count"] = {
        "pass": n_orders == task["n_source_orders"],
        "detail": f"{n_orders} orders vs {task['n_source_orders']} expected",
    }

    # revenue conservation
    rev = 0.0
    rev_ok = True
    for o in orders:
        q, p = _num(o.get("qty")), _num(o.get("unit_price"))
        if q is None or p is None:
            rev_ok = False
            continue
        rev += q * p
    rev = round(rev, 2)
    out["revenue"] = {
        "pass": rev_ok and abs(rev - task["source_revenue"]) < REV_EPS,
        "detail": f"${rev:.2f} vs ${task['source_revenue']:.2f} expected",
    }

    # referential integrity (no null FK, every FK resolves)
    cust_ids = {c.get("customer_id") for c in customers}
    bad_fk = [o.get("order_id") for o in orders
              if not o.get("customer_id") or o.get("customer_id") not in cust_ids]
    out["fk_integrity"] = {
        "pass": len(bad_fk) == 0,
        "detail": "all FKs resolve" if not bad_fk else f"{len(bad_fk)} dangling/null FK(s): {bad_fk[:3]}",
    }

    # primary key uniqueness (orders + customers)
    o_ids = [o.get("order_id") for o in orders]
    c_ids = [c.get("customer_id") for c in customers]
    pk_ok = len(o_ids) == len(set(o_ids)) and len(c_ids) == len(set(c_ids))
    out["pk_unique"] = {
        "pass": pk_ok,
        "detail": "unique" if pk_ok else "duplicate primary key(s) found",
    }

    # customer de-duplication
    n_cust = len(customers)
    out["customer_count"] = {
        "pass": n_cust == task["n_distinct_customers"],
        "detail": f"{n_cust} customers vs {task['n_distinct_customers']} expected",
    }

    # no null / empty required fields
    req_o = ["order_id", "customer_id", "product", "qty", "unit_price", "order_date"]
    req_c = ["customer_id", "name", "email"]
    nulls = 0
    for o in orders:
        nulls += sum(1 for k in req_o if o.get(k) in (None, ""))
    for c in customers:
        nulls += sum(1 for k in req_c if c.get(k) in (None, ""))
    out["no_null"] = {
        "pass": nulls == 0,
        "detail": "complete" if nulls == 0 else f"{nulls} null/empty field(s)",
    }

    return out


def oracle_pass(candidate: dict, task: dict) -> bool:
    inv = check_invariants(candidate, task)
    return all(inv[name]["pass"] for name in HARD_INVARIANTS)


def oracle_score(candidate: dict, task: dict) -> float:
    """
    Ranking score among candidates. Pessimistic: passing all hard invariants
    dominates; ties broken by revenue closeness and fewer nulls. The oracle cannot
    see ground truth, so two fully-passing candidates are indistinguishable here
    (this is the honest ceiling the demo should acknowledge).
    """
    inv = check_invariants(candidate, task)
    passed = sum(1 for name in HARD_INVARIANTS if inv[name]["pass"])
    # secondary, continuous tie-breakers in [0,1)
    rev = 0.0
    prod_rev = {}
    for o in candidate.get("orders", []) or []:
        q, p = _num(o.get("qty")), _num(o.get("unit_price"))
        if q is not None and p is not None:
            rev += q * p
            prod_rev[o.get("product")] = prod_rev.get(o.get("product"), 0.0) + q * p
    rev_close = 1.0 / (1.0 + abs(round(rev, 2) - task["source_revenue"]))
    # per-product revenue conservation: a richer label-free signal that separates
    # otherwise-passing candidates (e.g. swapped product labels) from the real thing.
    src_pr = task.get("source_product_revenue", {})
    drift = sum(abs(round(prod_rev.get(k, 0.0), 2) - v) for k, v in src_pr.items())
    prod_close = 1.0 / (1.0 + drift)
    return passed * 1.0 + prod_close * 0.01 + rev_close * 0.001
