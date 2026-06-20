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


def test_recognition_adversarial():
    print("recognition: negation, ambiguous breathing, and unexplained collapse (critic findings)")
    # negation must not trigger a protocol
    check(recognize("no chest pain, just a bit winded") != "heart_attack", "'no chest pain' -> heart_attack")
    check(recognize("he's not choking, he's totally fine") != "choke", "'not choking' -> choke")
    check(recognize("there's no bleeding now") != "bleed", "'no bleeding' -> bleed")
    # bare breathing difficulty is ambiguous -> never force choke or CPR
    check(recognize("i can't breathe") != "choke", "'i can't breathe' -> choke")
    # but breathing difficulty WITH a choking object -> choke
    check(recognize("something is stuck in his throat and he can't breathe") == "choke", "object+can't breathe should be choke")
    # unexplained collapse with no arrest sign -> None (UI says call 911), not a wrong CPR
    check(recognize("he fainted at the gym") is None, "'fainted' should be None, not CPR")
    # arrest still routes to CPR even when a far-away contraction is in the sentence
    check(recognize("i can't get him to wake up, he's not breathing") == "cpr", "far contraction wrongly cancelled arrest")
    check(recognize("he collapsed and isn't breathing") == "cpr", "headline arrest case must be CPR")
    # word-based negation: "not having a X" (negator >1 word from cue) must be caught...
    check(recognize("she is not having a stroke") is None, "'not having a stroke' -> stroke")
    check(recognize("i'm not having a heart attack, just heartburn") != "heart_attack", "'not having a heart attack' misrouted")
    check(recognize("he's not having a seizure anymore") != "seizure", "'not having a seizure' misrouted")
    check(recognize("can't breathe but nothing is stuck") != "choke", "'nothing is stuck' -> choke")
    # ...but a far-away negation must NOT cancel a real emergency
    check(recognize("no time, he's having a stroke") == "stroke", "far 'no' wrongly cancelled real stroke")
    # "won't/can't STOP X" is affirmative (continuous), not a negation
    check(recognize("she won't stop choking") == "choke", "'won't stop choking' wrongly cancelled")
    check(recognize("he won't stop bleeding") == "bleed", "'won't stop bleeding' wrongly cancelled")


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
    # an anaphylaxis answer that SKIPS the monitoring step must NOT verify (911-synonym
    # augmentation must not leak into the monitoring concept-group)
    incomplete_ana = "Call 911. Administer the EpiPen to the thigh. Lay them on their side. Contact emergency services again if needed."
    check(not verify(incomplete_ana, "anaphylaxis"), "anaphylaxis answer missing the monitoring step wrongly verified")


def main():
    for fn in (test_recognition, test_recognition_adversarial, test_fallback_invariant, test_key_consistency, test_negation_safety):
        fn()
    n = len(SCENARIOS)
    if _fails:
        print(f"\nFAILED: {len(_fails)} check(s).")
        sys.exit(1)
    print(f"\nPASS: {n} scenarios routed, {len(CANON)} fallbacks self-verify, verifier safety holds.")


if __name__ == "__main__":
    main()
