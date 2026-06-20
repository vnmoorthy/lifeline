"""
The live single-turn engine: spoken emergency -> verified guidance.

recognize -> effort-manager picks how many refinement passes -> generate -> VERIFY.
Safety rule: we NEVER speak an unverified step. If the model's draft fails the protocol
check, we fall back to reading the documented protocol itself (always correct). The demo
story is how often the model's OWN output is verified vs needs the fallback — that's what
more inference compute buys.
"""
from __future__ import annotations
import os
import random

from lifeline.recognize import recognize
from lifeline.protocols import PROTOCOLS
from lifeline.generate import generate
from lifeline.verifier import check_guidance
from lifeline.controller import decide_passes, PER_PASS_MS


def _backend():
    return "diffusion" if os.environ.get("LIFELINE_BASE_URL") else "mock"


def answer(transcript: str, backend: str | None = None, seed: int = 0) -> dict:
    backend = backend or _backend()
    pid, difficulty = recognize(transcript)
    if pid is None:
        return {
            "recognized": False,
            "spoken": "I can't identify this emergency. Call 911 now and describe what you see.",
            "steps": ["Call 911 now"], "verified": True, "regime": "unknown",
            "passes": 0, "latency_ms": 0, "protocol": None, "fallback": False,
            "transcript": transcript,
        }

    proto = PROTOCOLS[pid]
    scenario = {"id": "live", "say": transcript, "protocol": pid, "difficulty": difficulty}
    rng = random.Random(seed)
    gen = lambda s, p, k, r: generate(s, p, k, backend=backend, rng=r)
    is_ok = lambda g, p: check_guidance(g, p)["pass"]

    passes, regime, conf = decide_passes(scenario, proto, is_ok, gen, rng)
    draft = gen(scenario, proto, passes, rng)
    chk = check_guidance(draft, proto)

    if chk["pass"]:
        steps, fallback = draft, False
    else:
        steps, fallback = list(proto["steps"]), True   # safe fallback: the documented protocol

    return {
        "recognized": True,
        "protocol": proto["name"],
        "regime": regime,
        "passes": passes,
        "latency_ms": passes * PER_PASS_MS,
        "verified": True,                 # what we SPEAK is always verified (model-checked or canonical)
        "model_verified": chk["pass"],    # was the MODEL's own draft the verified one?
        "fallback": fallback,
        "steps": steps,
        "transcript": transcript,
        "backend": backend,
    }


if __name__ == "__main__":
    import sys
    print(answer(" ".join(sys.argv[1:]) or "he collapsed and isn't breathing"))
