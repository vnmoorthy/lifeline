"""
The grounded verifier: the guide may ONLY speak guidance that matches the protocol.

This is NOT an LLM judging itself. It mechanically checks the generated steps against
the documented protocol: are the critical steps present and in order, is "call 911"
included when required, and are any dangerous/forbidden actions present? Pass or fail.
That check is what makes "never confidently wrong" real.
"""
from __future__ import annotations


def _has(text_steps, needle) -> bool:
    n = needle.lower()
    return any(n in s.lower() for s in text_steps)


def check_guidance(guidance: list[str], protocol: dict) -> dict:
    crit = protocol["critical"]
    present = [c for c in crit if _has(guidance, c)]
    missing = [c for c in crit if not _has(guidance, c)]

    # order: indices of critical items as they appear in the guidance must be non-decreasing
    order_ok = True
    last = -1
    joined = [s.lower() for s in guidance]
    for c in crit:
        idx = next((i for i, s in enumerate(joined) if c.lower() in s), None)
        if idx is None:
            continue
        if idx < last:
            order_ok = False
            break
        last = idx

    has_911 = (not protocol["must_call_911"]) or _has(guidance, "call 911") or _has(guidance, "911")
    forbidden_hit = [f for f in protocol["forbidden"] if _has(guidance, f)]

    passed = (len(missing) == 0) and order_ok and has_911 and (len(forbidden_hit) == 0)
    score = len(present) / len(crit) if crit else 1.0
    return {
        "pass": passed,
        "score": round(score, 3),
        "missing_critical": missing,
        "order_ok": order_ok,
        "has_911": has_911,
        "forbidden_present": forbidden_hit,
    }


def is_correct(guidance: list[str], protocol: dict) -> bool:
    return check_guidance(guidance, protocol)["pass"]
