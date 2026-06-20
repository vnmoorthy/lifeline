"""
Sample task: messy denormalized orders CSV  ->  normalized {customers, orders}.

This is a *deterministically checkable* data-migration task. The whole GreenWall
thesis rests on the fact that a correct migration must obey algebraic conservation
laws (row counts, revenue, referential integrity) that can be checked WITHOUT any
ground-truth labels. The gold tables here are used ONLY to score true accuracy for
the demo curves -- never for selection.

Swap this file out for a harder / real task and the rest of the pipeline is unchanged.
"""
from __future__ import annotations
import csv
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- Gold (ground truth). Used only to MEASURE accuracy, never to select. ----
GOLD_CUSTOMERS = [
    {"customer_id": "c1", "name": "Alice Smith", "email": "alice@x.com"},
    {"customer_id": "c2", "name": "Bob Jones",   "email": "bob@y.com"},
    {"customer_id": "c3", "name": "Carol White", "email": "carol@z.com"},
    {"customer_id": "c4", "name": "Dan Brown",   "email": "dan@w.com"},
    {"customer_id": "c5", "name": "Eve Black",   "email": "eve@v.com"},
]

GOLD_ORDERS = [
    {"order_id": "O1",  "customer_id": "c1", "product": "Widget", "qty": 2,  "unit_price": 10.00, "order_date": "2026-01-02"},
    {"order_id": "O2",  "customer_id": "c2", "product": "Gadget", "qty": 1,  "unit_price": 25.50, "order_date": "2026-01-03"},
    {"order_id": "O3",  "customer_id": "c1", "product": "Widget", "qty": 3,  "unit_price": 10.00, "order_date": "2026-01-05"},
    {"order_id": "O4",  "customer_id": "c3", "product": "Gizmo",  "qty": 5,  "unit_price": 4.00,  "order_date": "2026-01-06"},
    {"order_id": "O5",  "customer_id": "c2", "product": "Widget", "qty": 2,  "unit_price": 10.00, "order_date": "2026-01-08"},
    {"order_id": "O6",  "customer_id": "c4", "product": "Gadget", "qty": 1,  "unit_price": 25.50, "order_date": "2026-01-09"},
    {"order_id": "O7",  "customer_id": "c5", "product": "Gizmo",  "qty": 10, "unit_price": 4.00,  "order_date": "2026-01-11"},
    {"order_id": "O8",  "customer_id": "c3", "product": "Widget", "qty": 1,  "unit_price": 10.00, "order_date": "2026-01-12"},
    {"order_id": "O9",  "customer_id": "c4", "product": "Gizmo",  "qty": 2,  "unit_price": 4.00,  "order_date": "2026-01-14"},
    {"order_id": "O10", "customer_id": "c5", "product": "Gadget", "qty": 4,  "unit_price": 25.50, "order_date": "2026-01-15"},
]

_CUST_BY_ID = {c["customer_id"]: c for c in GOLD_CUSTOMERS}

# ---- Source: messy, denormalized rows the agent must clean up. ----
# Issues injected on purpose: inconsistent casing, padded emails, "$" prices,
# string quantities, and two exact-duplicate rows (O3, O7) that must be deduped.
def _messy_row(o, *, upper=False, pad_email=False):
    c = _CUST_BY_ID[o["customer_id"]]
    name = c["name"].upper() if upper else c["name"]
    email = ("  " + c["email"] + " ") if pad_email else c["email"]
    return {
        "order_id": o["order_id"],
        "customer_name": name,
        "customer_email": email,
        "product": o["product"],
        "qty": str(o["qty"]),
        "price": f"${o['unit_price']:.2f}",
        "order_date": o["order_date"],
    }

SOURCE_ROWS = (
    [_messy_row(GOLD_ORDERS[0])]
    + [_messy_row(GOLD_ORDERS[1], pad_email=True)]
    + [_messy_row(GOLD_ORDERS[2], upper=True)]
    + [_messy_row(GOLD_ORDERS[2], upper=True)]          # duplicate of O3
    + [_messy_row(GOLD_ORDERS[3])]
    + [_messy_row(GOLD_ORDERS[4], pad_email=True)]
    + [_messy_row(GOLD_ORDERS[5])]
    + [_messy_row(GOLD_ORDERS[6], upper=True)]
    + [_messy_row(GOLD_ORDERS[6], upper=True)]          # duplicate of O7
    + [_messy_row(GOLD_ORDERS[7])]
    + [_messy_row(GOLD_ORDERS[8])]
    + [_messy_row(GOLD_ORDERS[9], pad_email=True)]
)

# ---- Source-derived invariants (label-free: computed from SOURCE only). ----
N_SOURCE_ORDERS = len({r["order_id"] for r in SOURCE_ROWS})            # = 10
N_DISTINCT_CUSTOMERS = len({r["customer_email"].strip().lower() for r in SOURCE_ROWS})  # = 5
SOURCE_REVENUE = round(
    sum(
        o["qty"] * o["unit_price"]
        for o in GOLD_ORDERS  # equals the de-duplicated source revenue by construction
    ),
    2,
)  # = 301.00


def write_source_csv(path: str | None = None) -> str:
    path = path or os.path.join(BASE, "data", "orders_raw.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cols = ["order_id", "customer_name", "customer_email", "product", "qty", "price", "order_date"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(SOURCE_ROWS)
    return path


def _source_product_revenue() -> dict:
    rev = {}
    for o in GOLD_ORDERS:  # equals de-duplicated source per-product revenue by construction
        rev[o["product"]] = round(rev.get(o["product"], 0.0) + o["qty"] * o["unit_price"], 2)
    return rev


def load_task() -> dict:
    """Return the full task bundle used by the rest of the pipeline."""
    return {
        "name": "orders_normalization",
        "description": "Normalize a messy denormalized orders CSV into {customers, orders}.",
        "source_rows": SOURCE_ROWS,
        "gold_customers": GOLD_CUSTOMERS,
        "gold_orders": GOLD_ORDERS,
        # label-free expected invariants:
        "n_source_orders": N_SOURCE_ORDERS,
        "n_source_rows": len(SOURCE_ROWS),
        "n_distinct_customers": N_DISTINCT_CUSTOMERS,
        "source_revenue": SOURCE_REVENUE,
        "source_product_revenue": _source_product_revenue(),
    }


if __name__ == "__main__":
    p = write_source_csv()
    t = load_task()
    print(f"wrote {p}")
    print(f"source rows={t['n_source_rows']} distinct orders={t['n_source_orders']} "
          f"distinct customers={t['n_distinct_customers']} revenue=${t['source_revenue']:.2f}")
