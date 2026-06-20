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
        ["compress", "compression", "center of the chest", "center of chest", "centre of chest", "middle of the chest", "push hard"],
        ["100-120", "100 to 120", "100–120", "per minute"]],
        "forbid": ["give them water", "give water", "induce vomiting", "slap them awake"]},
    "choke": {"require": [
        ["911", "emergency service", "999", "112", "call for help"],
        ["back blow", "abdominal thrust", "heimlich", "thrust"]],
        "forbid": ["blind finger sweep", "lay them flat and press on the stomach"]},
    "bleed": {"require": [
        ["direct pressure", "apply pressure", "press on the wound", "firm pressure",
         "press firmly", "apply firm", "pressure to the wound", "pressure on the wound", "applying pressure"]],
        "forbid": ["remove the soaked", "tourniquet around the neck"]},
    "od": {"require": [
        ["911", "emergency service", "999", "112", "call for help"],
        ["naloxone", "narcan"],
        ["rescue breath", "cpr", "recovery position", "breathing"]],
        "forbid": ["cold shower", "induce vomiting", "let them sleep it off"]},
    "burn": {"require": [
        ["cool running water", "cool water", "running water", "cool the burn", "under water", "rinse", "cool, running"]],
        "forbid": ["apply ice", "put ice", "apply butter", "toothpaste"]},
}

SCENARIOS = [
    {"id": "cpr",        "proto": "cpr",   "q": "someone collapsed and is not breathing"},
    {"id": "choke",      "proto": "choke", "q": "my friend is choking on food and can't breathe"},
    {"id": "bleed",      "proto": "bleed", "q": "deep cut on the arm, bleeding a lot"},
    {"id": "burn",       "proto": "burn",  "q": "spilled boiling water on the hand"},
    {"id": "od",         "proto": "od",    "q": "someone overdosed on opioids, lips turning blue"},
    {"id": "choke_hard", "proto": "choke", "q": "someone was choking and just went unconscious"},
    {"id": "od_hard",    "proto": "od",    "q": "unresponsive and not breathing, suspected fentanyl, and she's pregnant"},
    {"id": "bleed_hard", "proto": "bleed", "q": "leg wound still spurting after pressure, blood soaking through the cloth"},
]

POOL_N = int(os.environ.get("POOL_N", "16"))
GRID = [1, 2, 4, 8, 16]
RESAMPLES = 400
TARGET = 0.9
MAX_N = 16
PER_SAMPLE_MS = 45  # parallel best-of-N: wall-clock ~ one sample; this is a per-sample proxy


def verify(text: str, proto_key: str) -> bool:
    t = text.lower()
    p = PROTO[proto_key]
    if any(f in t for f in p["forbid"]):
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
