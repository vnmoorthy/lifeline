"""
Execution verifier: the database is the oracle.

A candidate is scored by EXECUTING its SQL and comparing the result set — never by an
LLM's opinion. Selection is by execution-consensus: cluster candidates by the result
they actually produce, pick the largest cluster. Correctness (for the curve only) is
result-set equality against the gold rows.
"""
from __future__ import annotations
from collections import Counter

from nozzle.db import run_sql


def canonical(rows) -> str:
    """Order-insensitive, type-normalized signature of a result set."""
    if rows is None:
        return "ERROR"
    norm = []
    for r in rows:
        cells = []
        for v in r:
            if isinstance(v, float):
                cells.append(f"{round(v, 2):.2f}")
            else:
                cells.append(str(v).strip())
        norm.append(tuple(cells))
    norm.sort()
    return repr(norm)


def execute_candidate(db_path: str, sql: str) -> dict:
    rows, err = run_sql(db_path, sql)
    return {"sql": sql, "rows": rows, "error": err, "sig": canonical(rows) if err is None else "ERROR"}


def is_correct(candidate_sig: str, gold_rows) -> bool:
    return candidate_sig != "ERROR" and candidate_sig == canonical(gold_rows)


def consensus_select(executed: list[dict]) -> dict | None:
    """Pick the candidate from the largest result-set cluster (ignoring errors).
    Returns the representative executed candidate, or None if all errored."""
    valid = [e for e in executed if e["sig"] != "ERROR"]
    if not valid:
        return None
    counts = Counter(e["sig"] for e in valid)
    winner_sig, _ = counts.most_common(1)[0]
    for e in valid:
        if e["sig"] == winner_sig:
            return e
    return None


def agreement(executed: list[dict]) -> float:
    """Fraction of (non-error) candidates that agree with the plurality result.
    This is the cheap, label-free difficulty signal the controller uses."""
    valid = [e for e in executed if e["sig"] != "ERROR"]
    if not valid:
        return 0.0
    counts = Counter(e["sig"] for e in valid)
    top = counts.most_common(1)[0][1]
    return top / len(valid)
