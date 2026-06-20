"""
A small but REAL business database + a natural-language question bank with gold SQL.

The database is the verifier: a candidate answer is correct iff its SQL, executed here,
returns the same result set as the gold SQL. No labels typed by hand, no LLM judge —
gold answers are computed by executing gold SQL against real rows at load time.
"""
from __future__ import annotations
import os
import random
import sqlite3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "nozzle.db")

SCHEMA = """
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, country TEXT, segment TEXT);
CREATE TABLE products  (id INTEGER PRIMARY KEY, name TEXT, category TEXT, unit_price REAL);
CREATE TABLE orders    (id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, status TEXT);
CREATE TABLE order_items(id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, qty INTEGER, unit_price REAL);
"""

_COUNTRIES = ["US", "US", "US", "UK", "DE", "IN", "CA", "AU"]
_SEGMENTS = ["SMB", "Enterprise", "Consumer"]
_PRODUCTS = [
    ("Widget Pro", "Hardware", 49.0),
    ("Widget Lite", "Hardware", 19.0),
    ("CloudSync", "Software", 120.0),
    ("CloudSync Plus", "Software", 240.0),
    ("Support Gold", "Services", 500.0),
    ("Support Silver", "Services", 200.0),
]
_STATUS = ["completed", "completed", "completed", "cancelled", "pending"]


def build_db(path: str = DB_PATH, seed: int = 13) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    rng = random.Random(seed)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)

    customers = [(i + 1, f"Customer {i+1}", rng.choice(_COUNTRIES), rng.choice(_SEGMENTS)) for i in range(8)]
    con.executemany("INSERT INTO customers VALUES (?,?,?,?)", customers)
    products = [(i + 1, n, c, p) for i, (n, c, p) in enumerate(_PRODUCTS)]
    con.executemany("INSERT INTO products VALUES (?,?,?,?)", products)

    orders, items, oid, iid = [], [], 0, 0
    for _ in range(45):
        oid += 1
        cust = rng.randint(1, 8)
        month = rng.randint(1, 12)
        year = rng.choice([2024, 2025, 2025, 2025])
        date = f"{year}-{month:02d}-{rng.randint(1,28):02d}"
        status = rng.choice(_STATUS)
        orders.append((oid, cust, date, status))
        for _ in range(rng.randint(1, 3)):
            iid += 1
            pid = rng.randint(1, len(_PRODUCTS))
            qty = rng.randint(1, 5)
            unit = _PRODUCTS[pid - 1][2]
            items.append((iid, oid, pid, qty, unit))
    con.executemany("INSERT INTO orders VALUES (?,?,?,?)", orders)
    con.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", items)
    con.commit()
    con.close()
    return path


def schema_text() -> str:
    return (
        "customers(id, name, country, segment)\n"
        "products(id, name, category, unit_price)\n"
        "orders(id, customer_id, order_date, status)  -- order_date is 'YYYY-MM-DD', status in (completed,cancelled,pending)\n"
        "order_items(id, order_id, product_id, qty, unit_price)"
    )


# Natural-language questions with GOLD SQL. Difficulty is a hint for analysis only;
# the controller must PREDICT it, not read it.
QUESTIONS = [
    {"id": "q1", "difficulty": "easy",   "q": "How many customers are there?",
     "gold": "SELECT COUNT(*) FROM customers"},
    {"id": "q2", "difficulty": "easy",   "q": "How many products do we sell?",
     "gold": "SELECT COUNT(*) FROM products"},
    {"id": "q3", "difficulty": "easy",   "q": "List the distinct product categories.",
     "gold": "SELECT DISTINCT category FROM products ORDER BY category"},
    {"id": "q4", "difficulty": "medium", "q": "What is total revenue from completed orders?",
     "gold": "SELECT ROUND(SUM(oi.qty*oi.unit_price),2) FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE o.status='completed'"},
    {"id": "q5", "difficulty": "medium", "q": "How many completed orders were placed in 2025?",
     "gold": "SELECT COUNT(*) FROM orders WHERE status='completed' AND order_date LIKE '2025-%'"},
    {"id": "q6", "difficulty": "medium", "q": "What is the average order value for completed orders?",
     "gold": "SELECT ROUND(SUM(oi.qty*oi.unit_price)*1.0/COUNT(DISTINCT o.id),2) FROM order_items oi JOIN orders o ON o.id=oi.order_id WHERE o.status='completed'"},
    {"id": "q7", "difficulty": "hard",   "q": "Which product category generated the most revenue from completed orders?",
     "gold": "SELECT p.category FROM order_items oi JOIN orders o ON o.id=oi.order_id JOIN products p ON p.id=oi.product_id WHERE o.status='completed' GROUP BY p.category ORDER BY SUM(oi.qty*oi.unit_price) DESC LIMIT 1"},
    {"id": "q8", "difficulty": "hard",   "q": "Which country has the highest completed-order revenue?",
     "gold": "SELECT c.country FROM order_items oi JOIN orders o ON o.id=oi.order_id JOIN customers c ON c.id=o.customer_id WHERE o.status='completed' GROUP BY c.country ORDER BY SUM(oi.qty*oi.unit_price) DESC LIMIT 1"},
    {"id": "q9", "difficulty": "hard",   "q": "Name the top customer by completed-order revenue.",
     "gold": "SELECT c.name FROM order_items oi JOIN orders o ON o.id=oi.order_id JOIN customers c ON c.id=o.customer_id WHERE o.status='completed' GROUP BY c.id ORDER BY SUM(oi.qty*oi.unit_price) DESC LIMIT 1"},
    {"id": "q10", "difficulty": "hard",  "q": "What is the completed-order revenue from Enterprise customers in 2025?",
     "gold": "SELECT ROUND(SUM(oi.qty*oi.unit_price),2) FROM order_items oi JOIN orders o ON o.id=oi.order_id JOIN customers c ON c.id=o.customer_id WHERE o.status='completed' AND c.segment='Enterprise' AND o.order_date LIKE '2025-%'"},
]


def run_sql(path: str, sql: str, timeout_s: float = 2.0):
    """Execute read-only SQL; return (rows, error). Rows are tuples; None error on success."""
    low = sql.strip().lower()
    if not low.startswith(("select", "with")):
        return None, "non-SELECT rejected"
    if any(tok in low for tok in (";--", "insert ", "update ", "delete ", "drop ", "alter ", "create ", "attach ")):
        return None, "write/DDL rejected"
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=timeout_s)
        con.execute("PRAGMA query_only=ON")
        cur = con.execute(sql)
        rows = cur.fetchall()
        con.close()
        return rows, None
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def load_questions(path: str = DB_PATH) -> list[dict]:
    """Attach the gold result set (executed live) to each question."""
    out = []
    for item in QUESTIONS:
        rows, err = run_sql(path, item["gold"])
        if err:
            raise RuntimeError(f"gold SQL failed for {item['id']}: {err}")
        out.append({**item, "gold_rows": rows})
    return out


if __name__ == "__main__":
    p = build_db()
    qs = load_questions(p)
    print(f"built {p} with {len(qs)} questions")
    for q in qs:
        print(f"  [{q['difficulty']:6}] {q['q']}  -> gold={q['gold_rows']}")
