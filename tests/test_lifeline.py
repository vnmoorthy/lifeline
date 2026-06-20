"""Lifeline test suite — dependency-free (no pytest needed). Run:  python3 tests/test_lifeline.py

Gates the whole product without a GPU: recognition routing, the verifier's negation handling,
and the critical SAFETY INVARIANT that every canonical fallback passes its own verifier (so the
product can always speak a verified-or-canonical answer, never an unverified instruction)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lifeline.triage import recognize, CANON, PROTO_NAME, CUES          # noqa: E402
from lifeline.real_run import verify, PROTO, SCENARIOS                   # noqa: E402

_fails = []


def check(cond, msg):
    if not cond:
        _fails.append(msg)
        print(f"  FAIL  {msg}")


def test_recognition():
    print("recognition: every scenario routes to its protocol")
    for sc in SCENARIOS:
        got = recognize(sc["q"])
        check(got == sc["proto"], f"{sc['id']}: want {sc['proto']} got {got}  <- {sc['q']}")
    # unrecognized input returns None (so the UI can fall back to 'call 911')
    for junk in ["what's the weather", "tell me a joke", ""]:
        check(recognize(junk) is None, f"junk should be None: {junk!r} -> {recognize(junk)}")


def test_fallback_invariant():
    print("safety invariant: every canonical fallback passes its own verifier")
    for k in CANON:
        check(verify(" ".join(CANON[k]), k), f"CANON[{k}] does not self-verify")


def test_key_consistency():
    print("consistency: CANON / PROTO / PROTO_NAME / CUES cover the same keys")
    keys = [set(CANON), set(PROTO), set(PROTO_NAME), set(CUES)]
    check(all(s == keys[0] for s in keys), f"key sets differ: {[sorted(s ^ keys[0]) for s in keys]}")


def test_negation_safety():
    print("verifier: dangerous answers rejected; correctly-negated advice accepted")
    dangerous = [
        ("burn", "Apply ice directly to the burn and rub butter on it."),
        ("hypoglycemia", "Give them insulin and call 911."),
        ("stroke", "Give aspirin and let them sleep it off."),
        ("poison", "Make them throw up to get the poison out."),
        ("fracture", "Straighten the limb and let them walk it off."),
        ("nosebleed", "Tilt your head back and lean back."),
        ("seizure", "Hold them down and put something in their mouth."),
    ]
    for k, t in dangerous:
        check(not verify(t, k), f"LEAK: dangerous {k} answer verified: {t}")
    # negated forbid phrases are correct advice, must NOT be rejected on that basis
    safe_negated = [
        ("burn", "Cool the burn under cool running water. Do not apply ice or butter."),
        ("nosebleed", "Lean forward and pinch the soft part of the nose for 10 to 15 minutes; do not tilt your head back. Seek help if it won't stop."),
    ]
    for k, t in safe_negated:
        check(verify(t, k), f"false-negative: correct {k} answer rejected: {t}")


def main():
    for fn in (test_recognition, test_fallback_invariant, test_key_consistency, test_negation_safety):
        fn()
    n = len(SCENARIOS)
    if _fails:
        print(f"\nFAILED: {len(_fails)} check(s).")
        sys.exit(1)
    print(f"\nPASS: {n} scenarios routed, {len(CANON)} fallbacks self-verify, verifier safety holds.")


if __name__ == "__main__":
    main()
