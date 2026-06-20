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
    # "didn't prevent" / "nothing prevented" = continuation, still an emergency
    check(recognize("the tourniquet didn't prevent the bleeding") == "bleed", "'didn't prevent the bleeding' dropped")
    check(recognize("nothing stopped the bleeding") == "bleed", "'nothing stopped the bleeding' dropped")
    # hypothetical / resolved phrasing -> None, but a REAL concurrent emergency must NOT be suppressed
    check(recognize("i'm afraid of having a stroke someday") is None, "'afraid of having a stroke' should be None")
    check(recognize("she was having a stroke but she's ok now") is None, "resolved case should be None")
    check(recognize("i'm afraid he's having a stroke") == "stroke", "real 'afraid he's having a stroke' was suppressed")
    # opioid OD with arrest must route to OD (naloxone), not generic CPR
    check(recognize("she took too much, she's got pinpoint pupils and not breathing") == "od", "pinpoint+arrest must be OD not CPR")
    check(recognize("he overdosed and isn't breathing") == "od", "overdose+arrest must be OD not CPR")
    check(recognize("he took something and his lips are blue and he's not breathing") == "od", "'took something'+arrest must be OD")
    # "blood sugar" must not match the bleed cue 'blood'
    check(recognize("blood sugar is really low i feel dizzy and weak") == "hypoglycemia", "'blood sugar' misrouted to bleed")
    # cold exposure disambiguates 'slurred speech' to hypothermia, not stroke
    check(recognize("he was lost in the snow for hours shivering with slurred speech") == "hypothermia", "cold+slurred misrouted to stroke")
    check(recognize("pulled from the pool, not breathing") == "drown", "drowning 'pulled from the pool' misrouted")
    check(recognize("he's burning up and not making sense") == "heatstroke", "'burning up' misrouted to burn")
    check(recognize("got heatstroke from being outside too long") == "heatstroke", "'heatstroke' misrouted to stroke")
    check(recognize("epistaxis, won't stop bleeding") == "nosebleed", "'epistaxis' misrouted to bleed")


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
    # a poisoning answer that omits Poison Control must NOT verify on a bare '911' alone
    poison_no_pc = "Call 911. Identify the substance and keep the container. Do not induce vomiting."
    check(not verify(poison_no_pc, "poison"), "poison answer without Poison Control wrongly verified")
    # require-group completeness: incomplete answers must NOT verify (they fall back to canon)
    check(not verify("Call 911. Give back blows.", "choke"), "choke without thrusts wrongly verified")
    check(not verify("Apply pressure to the wound. Elevate the limb.", "bleed"), "bleed without 911 wrongly verified")
    check(not verify("Cool the burn under cool running water for 20 minutes.", "burn"), "burn without coverage wrongly verified")
    # ...but COMPLETE answers must still verify (no over-rejection)
    check(verify("Call 911. Give 5 back blows between the shoulder blades, then 5 abdominal thrusts (Heimlich).", "choke"), "complete choke answer rejected")
    check(verify("Call 911. Apply firm direct pressure to the wound with a clean cloth.", "bleed"), "complete bleed answer rejected")
    check(verify("Cool the burn under cool running water for 20 minutes, then cover loosely with a clean dressing.", "burn"), "complete burn answer rejected")
    # CPR without depth, bleed tourniquet-without-pressure, OD recovery-without-breathing must fall back
    check(not verify("Call 911. Push hard in the center of the chest at 100-120 per minute.", "cpr"), "CPR without depth wrongly verified")
    check(not verify("Call 911. Apply a tourniquet above the wound.", "bleed"), "bleed tourniquet-only (no direct pressure) wrongly verified")
    check(not verify("Call 911. Give naloxone. Place them in the recovery position.", "od"), "OD without breathing check wrongly verified")
    # ...complete versions still verify
    check(verify("Call 911. Push hard in the center of the chest at 100-120 per minute, about 2 inches deep.", "cpr"), "complete CPR answer rejected")
    check(verify("Call 911. Give naloxone. If not breathing, start rescue breaths or CPR.", "od"), "complete OD answer rejected")
    # CPR with WRONG numbers (50/min, 1 inch) must not verify; cloth-removal advice must be forbidden
    check(not verify("Call 911. Push on the chest 50 times per minute, 1 inch deep.", "cpr"), "CPR with wrong rate/depth wrongly verified")
    check(not verify("Call 911. Apply direct pressure, then remove the cloth to check the bleeding.", "bleed"), "bleed 'remove the cloth' wrongly verified")


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
