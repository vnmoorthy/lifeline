"""
REAL best-of-N experiment against the live model (Qwen on the Lambda box, via the tunnel).

The inference-time-compute knob is N (parallel samples). For each emergency we draw a pool
of candidates, VERIFY each against the protocol with a concept-group checker (robust to
phrasing — "call emergency services" counts as calling 911, "5 cm" counts as depth), and
measure: accuracy = P(best-of-N contains a verified-correct answer). The effort-manager
spends N adaptively. Every number here is from real model output.

    LIFELINE_BASE_URL=http://localhost:8000/v1 LIFELINE_MODEL=Qwen/Qwen2.5-7B-Instruct \
        python3 -m lifeline.real_run
"""
from __future__ import annotations
import json
import math
import os
import random
import statistics
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = os.environ.get("LIFELINE_BASE_URL", "http://localhost:8000/v1").rstrip("/")
MODEL = os.environ.get("LIFELINE_MODEL", "Qwen/Qwen2.5-7B-Instruct")

PROMPT = ("Emergency: {q}. Give the numbered first-aid steps a bystander should take RIGHT NOW, "
          "one per line, no preamble, no commentary.")

# Concept-group verifier: each protocol requires ALL groups (any synonym in a group counts),
# and must contain NO forbidden (dangerous) action. Grounded, rule-based — no LLM judging.
PROTO = {
    "cpr": {"require": [
        ["911", "emergency service", "emergency number", "999", "112", "call for help", "call ems"],
        ["compress", "compression", "center of the chest", "center of chest", "centre of chest",
         "middle of the chest", "push hard", "pump", "push on the chest", "push forcefully"],
        ["100-120", "100 to 120", "100–120", "per minute"]],
        "forbid": ["give them water", "give water", "induce vomiting", "slap them awake"]},
    "choke": {"require": [
        ["911", "emergency service", "999", "112", "call for help"],
        ["back blow", "blows between the shoulder", "blows to the back"],
        ["abdominal thrust", "abdominal thrusts", "heimlich", "thrusts"]],
        "forbid": ["blind finger sweep", "lay them flat and press on the stomach"]},
    "bleed": {"require": [
        ["911", "emergency service", "999", "112", "call for help", "ambulance"],
        ["direct pressure", "apply pressure", "press on the wound", "firm pressure", "press firmly",
         "apply firm", "pressure to the wound", "pressure on the wound", "applying pressure",
         "tourniquet", "elevate the"]],
        "forbid": ["remove the soaked", "tourniquet around the neck", "tourniquet on the neck"]},
    "od": {"require": [
        ["911", "emergency service", "999", "112", "call for help"],
        ["naloxone", "narcan"],
        ["rescue breath", "cpr", "recovery position", "breathing"]],
        "forbid": ["cold shower", "induce vomiting", "let them sleep it off"]},
    "burn": {"require": [
        ["cool running water", "cool water", "cold water", "running water", "under water", "under cool", "under cold",
         "cool the burn", "cool the area", "run it under", "running it under", "rinse", "cool it", "lukewarm water", "cool, running"],
        ["cover", "dressing", "bandage", "clean cloth", "do not apply ice", "don't apply ice", "loosely", "seek medical", "non-stick"]],
        "forbid": ["apply ice", "put ice", "apply butter", "toothpaste"]},
    "anaphylaxis": {"require": [
        ["911", "emergency services", "emergency number", "999", "112", "call for help"],
        ["epinephrine", "epi pen", "epipen", "auto-injector", "autoinjector", "adrenaline auto-injector"],
        ["lie down", "lay down", "lie back", "raise their legs", "sit up", "lay them on their side", "lie on their side"],
        ["monitor", "stay with", "watch their breathing", "until help arrives", "until emergency", "second dose"]],
        "forbid": ["give them food", "make them drink water", "have them stand up and walk", "induce vomiting"]},
    "stroke": {"require": [
        ["fast", "face drooping", "face droop", "arm weakness", "arm drift", "slurred speech", "slurred", "speech"],
        ["call 911", "call emergency", "emergency services", "call for help", "999", "112"],
        ["time", "time of onset", "when symptoms started", "last known well", "last seen normal", "when it started"],
        ["do not give", "don't give", "nothing to eat or drink", "no food or drink", "not give food", "not give them anything to eat"]],
        "forbid": ["give food", "give them water", "give aspirin", "drive them yourself", "let them sleep it off"]},
    "seizure": {"require": [
        ["time it", "note the time", "time how long", "time the seizure", "how long it lasts"],
        ["clear the area", "move away furniture", "move objects", "remove nearby objects", "protect their head",
         "cushion their head", "something soft under it", "support the head", "cushioning it"],
        ["recovery position", "roll them onto their side", "turn them on their side", "onto their side", "on their side"],
        ["call 911", "call emergency services", "call 999", "phone 911", "call for an ambulance"]],
        "forbid": ["restrain", "hold them down", "put something in their mouth", "put anything in their mouth",
                   "place something in their mouth"]},
    "heart_attack": {"require": [
        ["call 911", "call emergency services", "phone 911", "call an ambulance", "emergency services"],
        ["aspirin", "chew an aspirin", "chew aspirin", "give aspirin", "aspirin tablet"],
        ["sit down", "sit them down", "rest", "keep still", "stay still", "keep calm", "stay calm"]],
        "forbid": ["drive yourself to the hospital", "drive them to the hospital", "lie flat", "let them sleep it off"]},
    "drown": {"require": [
        ["out of the water", "get them out", "remove from the water", "onto dry ground", "to dry land", "dry ground"],
        ["911", "emergency services", "emergency number", "call for help"],
        ["check breathing", "check whether they are breathing", "look for breathing", "see if they are breathing",
         "check if they're breathing", "breathing normally"],
        ["rescue breaths", "cpr", "chest compressions", "give breaths"]],
        "forbid": ["abdominal thrusts to remove water", "push on the stomach to get water out", "hold them upside down"]},
    "hypoglycemia": {"require": [
        ["fast-acting sugar", "fast acting sugar", "sugar", "glucose", "fruit juice", "juice", "soda", "honey"],
        ["able to swallow", "awake", "alert", "conscious", "can swallow"],
        ["call 911", "emergency services", "call emergency", "999", "112"],
        ["do not give them any food or drink", "do not give food", "nothing by mouth", "do not give anything to eat", "do not feed"]],
        "forbid": ["give insulin", "inject insulin", "more insulin", "force food into their mouth", "pour liquid into their mouth"]},
    "heatstroke": {"require": [
        ["911", "emergency services", "emergency number", "999", "112", "call for help"],
        ["cool place", "shade", "shaded", "air-conditioned", "cooler place", "out of the sun", "cool environment"],
        ["cool water", "cold water", "spray", "wet cloth", "ice pack", "ice packs", "immerse", "cold compress", "wet towels", "fan"],
        ["do not give", "don't give", "avoid giving", "no fluids", "not give anything to drink", "do not offer"]],
        "forbid": ["give them alcohol", "force them to drink"]},
    "hypothermia": {"require": [
        ["call 911", "emergency services", "call emergency", "999", "112"],
        ["move to a warm", "warm, dry", "warm place", "shelter", "indoors", "out of the cold", "to warmth", "sheltered"],
        ["remove wet clothing", "remove any wet clothing", "take off wet clothes", "remove wet clothes"],
        ["warm dry layers", "warm dry", "dry blankets", "blankets", "warm clothing", "dry layers"]],
        "forbid": ["rub the limbs", "massage the limbs", "rub the arms and legs", "give them alcohol", "hot bath",
                   "heating pad", "hot water bottle", "rub the person"]},
    "poison": {"require": [
        ["call poison control", "poison control", "1-800-222-1222", "poison help line"],
        ["call 911", "call emergency services", "emergency services", "911"],
        ["identify what was swallowed", "identify the substance", "what was swallowed", "keep the container",
         "container or label", "the substance"],
        ["do not induce vomiting", "do not make them vomit", "don't induce vomiting", "do not force vomiting"]],
        "forbid": ["make them throw up", "give ipecac", "give activated charcoal"]},
    "head_injury": {"require": [
        ["call 911", "emergency services", "call emergency", "999", "112", "ambulance"],
        ["keep still", "keep the person still", "rest", "do not move around", "stay still", "remain still",
         "keep them still", "do not get up"],
        ["consciousness", "alertness", "responsive", "monitor", "vomiting", "confusion", "worsening", "drowsiness", "unresponsive", "wake"],
        ["neck", "spine", "spinal"]],
        "forbid": ["shake the person", "let them sleep it off", "give them painkillers", "move the neck"]},
    "nosebleed": {"require": [
        ["lean forward", "tip forward", "lean slightly forward", "tilt forward"],
        ["pinch the soft part", "pinch the soft", "squeeze the soft part", "pinch the soft portion",
         "pinch the fleshy part", "pinch your nostrils", "pinch the nostrils", "pinch the nose",
         "pinch nose", "pinch nostrils", "pinch the bridge"],
        ["10 to 15 minutes", "10-15 minutes", "ten to fifteen minutes", "at least 10 minutes", "10 minutes"],
        ["call 911", "seek emergency", "seek medical", "emergency services", "get medical help", "seek help"]],
        "forbid": ["tilt your head back", "tilt the head back", "lean back", "head back", "swallow the blood"]},
    "fracture": {"require": [
        ["immobilize", "splint", "keep the injured person still", "keep it still", "support the injured area", "keep them from moving"],
        ["do not move", "don't move", "do not try to straighten", "do not realign", "do not try to realign", "avoid moving", "do not straighten"],
        ["ice", "ice pack", "cold pack", "cold compress"],
        ["call 911", "call emergency services", "emergency services", "call for help"]],
        "forbid": ["realign the bone", "straighten the limb", "push the bone back", "apply ice directly to the skin",
                   "let them walk it off"]},
}

# Broaden ONLY the "call emergency services" groups so correct model phrasings don't false-fallback.
# A group qualifies only if it actually expresses calling for help — guarded so a monitoring group
# containing "until emergency" is NOT mistaken for a call group (that would let an answer skip the
# monitoring step yet still verify).
_EMERGENCY_SYNS = ["911", "call 911", "dial 911", "phone 911", "ring 911", "call emergency",
                   "call emergency services", "emergency services", "emergency number", "call for help",
                   "call an ambulance", "ring for help", "999", "112"]


def _is_call_group(grp):
    # a Poison-Control group ("call poison control") is NOT a generic 911 group — don't let it be
    # satisfied by a bare "call 911" answer that omits the poison-control number.
    if any("poison" in s for s in grp):
        return False
    return any(("911" in s or s.startswith("call ") or s in ("emergency services", "emergency number", "ambulance"))
               for s in grp)


for _p in PROTO.values():
    for _grp in _p["require"]:
        if _is_call_group(_grp):
            _grp.extend(s for s in _EMERGENCY_SYNS if s not in _grp)

SCENARIOS = [
    {"id": "cpr",        "proto": "cpr",   "q": "someone collapsed and is not breathing"},
    {"id": "choke",      "proto": "choke", "q": "my friend is choking on food and can't breathe"},
    {"id": "bleed",      "proto": "bleed", "q": "deep cut on the arm, bleeding a lot"},
    {"id": "burn",       "proto": "burn",  "q": "spilled boiling water on the hand"},
    {"id": "od",         "proto": "od",    "q": "someone overdosed on opioids, lips turning blue"},
    {"id": "choke_hard", "proto": "cpr",   "q": "someone was choking and just went unconscious"},
    {"id": "od_hard",    "proto": "od",    "q": "unresponsive and not breathing, suspected fentanyl, and she's pregnant"},
    {"id": "bleed_hard", "proto": "bleed", "q": "leg wound still spurting after pressure, blood soaking through the cloth"},
    {"id": "anaphylaxis",  "proto": "anaphylaxis",  "q": "my friend just ate peanuts and now her throat is closing and her face is swelling"},
    {"id": "anaphylaxis2", "proto": "anaphylaxis",  "q": "he got stung by a bee and is covered in hives and can barely breathe, he has an epipen"},
    {"id": "stroke",       "proto": "stroke",       "q": "my dad's face is drooping on one side and he can't lift his right arm"},
    {"id": "stroke2",      "proto": "stroke",       "q": "my wife suddenly started slurring her words and seems confused"},
    {"id": "seizure",      "proto": "seizure",      "q": "someone next to me is having a seizure, their whole body is convulsing"},
    {"id": "seizure2",     "proto": "seizure",      "q": "my brother has epilepsy and he's having a fit right now, jerking and stiff"},
    {"id": "heart_attack", "proto": "heart_attack", "q": "my dad is awake but clutching his chest with crushing pressure and his left arm hurts"},
    {"id": "heart_attack2","proto": "heart_attack", "q": "i have tightness in my chest and shortness of breath, i think i'm having a heart attack"},
    {"id": "drown",        "proto": "drown",        "q": "my kid was pulled out of the pool and isn't breathing"},
    {"id": "drown2",       "proto": "drown",        "q": "we got my friend out of the lake but he's unconscious and not breathing"},
    {"id": "hypoglycemia", "proto": "hypoglycemia", "q": "my dad is diabetic and he's shaky, sweating and confused but still awake and talking"},
    {"id": "hypoglycemia2","proto": "hypoglycemia", "q": "i'm diabetic and my blood sugar reads really low and i feel dizzy and weak"},
    {"id": "heatstroke",   "proto": "heatstroke",   "q": "my dad was working in the heat and now he's confused with hot dry skin"},
    {"id": "heatstroke2",  "proto": "heatstroke",   "q": "a runner overheated and is disoriented and very hot after the race"},
    {"id": "hypothermia",  "proto": "hypothermia",  "q": "my friend was lost in the snow for hours, shivering hard with slurred speech and freezing skin"},
    {"id": "hypothermia2", "proto": "hypothermia",  "q": "an elderly man was out in the cold overnight, he's pale, cold to the touch and confused"},
    {"id": "poison",       "proto": "poison",       "q": "my toddler got into the medicine cabinet and swallowed a bunch of pills"},
    {"id": "poison2",      "proto": "poison",       "q": "my husband accidentally drank some drain cleaner and is coughing"},
    {"id": "head_injury",  "proto": "head_injury",  "q": "my friend fell off his bike and hit his head, now he's confused and threw up twice"},
    {"id": "head_injury2", "proto": "head_injury",  "q": "an elderly man slipped and hit his head, his neck hurts and he feels dizzy"},
    {"id": "nosebleed",    "proto": "nosebleed",    "q": "my nose suddenly started bleeding and won't stop"},
    {"id": "nosebleed2",   "proto": "nosebleed",    "q": "my son has a bloody nose from getting hit during soccer"},
    {"id": "fracture",     "proto": "fracture",     "q": "my friend fell off a ladder and there's a bone sticking out of his lower leg"},
    {"id": "fracture2",    "proto": "fracture",     "q": "i slipped on ice and my wrist is swollen and bent at a weird angle"},
]

POOL_N = int(os.environ.get("POOL_N", "16"))
GRID = [1, 2, 4, 8, 16]
RESAMPLES = 400
TARGET = 0.9
MAX_N = 16
PER_SAMPLE_MS = 45  # parallel best-of-N: wall-clock ~ one sample; this is a per-sample proxy


# negation tokens that neutralize a forbidden phrase — "do NOT apply ice" is correct advice,
# not a dangerous instruction. Without this, the verifier rejects good answers and even the
# canonical fallback ("do not apply ice or butter") fails to verify.
_NEG = ("not ", "n't", "never", "avoid", "without")


def _clause_start(t: str, i: int) -> int:
    """Start index of the clause containing position i (split on . ; newline, NOT commas, so a
    negation scopes over a whole coordinated clause: 'never apply butter or toothpaste')."""
    return max((t.rfind(b, 0, i) + 1) for b in ".;\n")


def _forbidden(t: str, phrases) -> bool:
    """True only if a dangerous phrase appears in a clause with no negation before it."""
    for f in phrases:
        i = t.find(f)
        while i != -1:
            if not any(n in t[_clause_start(t, i):i] for n in _NEG):
                return True
            i = t.find(f, i + 1)
    return False


def verify(text: str, proto_key: str) -> bool:
    t = text.lower()
    p = PROTO[proto_key]
    if _forbidden(t, p["forbid"]):
        return False
    return all(any(syn in t for syn in grp) for grp in p["require"])


def gen_pool(q: str, n: int, temperature: float = 0.8):
    payload = {"model": MODEL, "messages": [{"role": "user", "content": PROMPT.format(q=q)}],
               "n": n, "temperature": temperature, "max_tokens": 240}
    req = urllib.request.Request(BASE_URL + "/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.load(r)
    return [c["message"]["content"] for c in d["choices"]]


def boot_anypass(flags, k, resamples, rng):
    if not flags:
        return 0.0
    hits = 0
    for _ in range(resamples):
        sub = [flags[rng.randrange(len(flags))] for _ in range(k)]
        hits += 1 if any(sub) else 0
    return hits / resamples


def needed_n(p, target=TARGET, cap=MAX_N):
    if p <= 0:
        return cap
    if p >= target:
        return 1
    return min(cap, max(1, math.ceil(math.log(1 - target) / math.log(1 - p))))


def main():
    rng = random.Random(0)
    print(f"REAL run · model={MODEL} · {len(SCENARIOS)} emergencies · pool N={POOL_N}\n")

    # one API call per scenario (n=POOL_N), concurrently
    def fetch(sc):
        pool = gen_pool(sc["q"], POOL_N)
        flags = [verify(c, sc["proto"]) for c in pool]
        return sc["id"], flags, pool

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(fetch, SCENARIOS))
    flags_by = {sid: f for sid, f, _ in results}
    pool_by = {sid: p for sid, _, p in results}

    # accuracy vs N (bootstrap any-pass over the pool)
    curve = {}
    for k in GRID:
        per = [boot_anypass(flags_by[sc["id"]], k, RESAMPLES, rng) for sc in SCENARIOS]
        curve[k] = round(statistics.mean(per), 4)

    single = round(statistics.mean(statistics.mean([1.0 if x else 0.0 for x in flags_by[sc["id"]]]) for sc in SCENARIOS), 4)

    # effort-manager: estimate p per scenario from the pool, allocate N, accuracy via bootstrap
    ctrl_acc, ctrl_n, per_scen = [], [], []
    for sc in SCENARIOS:
        flags = flags_by[sc["id"]]
        p = statistics.mean([1.0 if x else 0.0 for x in flags]) if flags else 0.0
        n = needed_n(p)
        acc = boot_anypass(flags, n, RESAMPLES, rng)
        ctrl_acc.append(acc)
        ctrl_n.append(n)
        per_scen.append({"id": sc["id"], "q": sc["q"], "proto": sc["proto"],
                         "single_p": round(p, 2), "chosen_n": n,
                         "latency_ms": n * PER_SAMPLE_MS, "acc": round(acc, 3),
                         "regime": "routine" if n <= 2 else ("moderate" if n <= 6 else "critical")})
    ctrl_acc_m = round(statistics.mean(ctrl_acc), 4)
    ctrl_n_m = round(statistics.mean(ctrl_n), 2)
    fixed_hi = curve[GRID[-1]]

    print(f"  {'N':>4} | {'accuracy':>9}")
    for k in GRID:
        print(f"  {k:>4} | {curve[k]:>9.3f}")
    print(f"\n  single-shot (N=1): {single:.3f}")
    print(f"  effort-manager: acc={ctrl_acc_m:.3f} at avg N={ctrl_n_m:.1f}")
    print(f"  fixed best (N={GRID[-1]}): acc={fixed_hi:.3f}")
    if fixed_hi > 0:
        print(f"  -> {ctrl_acc_m/fixed_hi*100:.0f}% of best accuracy at {ctrl_n_m/GRID[-1]*100:.0f}% of the samples")
    print("\n  per emergency:")
    for r in per_scen:
        print(f"   {r['id']:11} p1={r['single_p']:.2f} -> N={r['chosen_n']:2} ({r['regime']:8}) acc={r['acc']:.2f}")

    data = {"project": "Lifeline", "simulated": False, "backend": "vllm", "model": MODEL,
            "knob": "best-of-N samples", "grid": GRID, "curve": [curve[k] for k in GRID],
            "single_shot": single, "controller": {"acc": ctrl_acc_m, "avg_n": ctrl_n_m},
            "fixed_hi": {"n": GRID[-1], "acc": fixed_hi}, "scenarios": per_scen,
            "samples": {sc["id"]: pool_by[sc["id"]][:2] for sc in SCENARIOS}}
    out = os.path.join(BASE, "dashboard_lifeline")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "real_results.json"), "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n  -> wrote dashboard_lifeline/real_results.json")
    return data


if __name__ == "__main__":
    main()
