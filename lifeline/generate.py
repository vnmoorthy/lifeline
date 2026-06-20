"""
The generator = the diffusion model that drafts guidance and refines it over passes.

The inference-time-compute knob is `passes` (refinement/denoising rounds). More passes
-> the draft converges to the correct protocol. Hard/ambiguous scenarios need MORE passes.

Backends:
  * mock      -> OFFLINE, $0. Produces REAL step-lists (correct or corrupted) so the
                 verifier genuinely evaluates them; only the *generator* is simulated.
                 Build & debug the whole pipeline for free, then flip to the real model.
  * diffusion -> a real diffusion LM via an OpenAI-compatible endpoint (dlmserve on your
                 Prime Intellect GPU). Set LIFELINE_BASE_URL / LIFELINE_MODEL.

The mock convergence is a logistic in (passes - difficulty): few passes on a hard case
-> usually corrupted (verifier fails); enough passes -> correct (verifier passes).
"""
from __future__ import annotations
import copy
import math
import os
import random


def _p_correct(passes: int, difficulty: float) -> float:
    return 1.0 / (1.0 + math.exp(-0.7 * (passes - difficulty)))


def _corrupt(steps: list[str], protocol: dict, rng: random.Random) -> list[str]:
    """Inject a realistic error so the verifier fails: drop a critical step / drop 911 /
    swap order / insert a forbidden (dangerous) action."""
    s = copy.deepcopy(steps)
    mode = rng.choice(["drop_critical", "drop_911", "swap", "forbidden"])
    if mode == "drop_critical" and protocol["critical"]:
        bad = rng.choice(protocol["critical"])
        s = [x for x in s if bad.lower() not in x.lower()] or s[:-1]
    elif mode == "drop_911":
        s = [x for x in s if "911" not in x.lower()]
    elif mode == "swap" and len(s) >= 2:
        i = rng.randrange(len(s) - 1)
        s[i], s[i + 1] = s[i + 1], s[i]
    elif mode == "forbidden" and protocol["forbidden"]:
        s = [protocol["forbidden"][0].capitalize()] + s
    return s


def mock_generate(scenario: dict, protocol: dict, passes: int, rng: random.Random) -> list[str]:
    gold = protocol["steps"]
    if rng.random() < _p_correct(passes, scenario["difficulty"]):
        return list(gold)
    return _corrupt(gold, protocol, rng)


# ---- real diffusion backend (stdlib urllib; nothing to install) ----
def diffusion_generate(scenario: dict, protocol: dict, passes: int) -> list[str]:
    import json
    import urllib.request

    base = os.environ.get("LIFELINE_BASE_URL", "http://localhost:8000/v1").rstrip("/")
    model = os.environ.get("LIFELINE_MODEL", "diffusion-gemma")
    key = os.environ.get("LIFELINE_API_KEY", "EMPTY")
    prompt = (
        f"Emergency: \"{scenario['say']}\". Give numbered first-aid steps that EXACTLY follow "
        f"standard protocol for {protocol['name']}. Always include calling 911 if life-threatening. "
        f"One step per line, no commentary."
    )
    # `passes` -> diffusion denoising/refinement steps (the inference-time-compute knob).
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 256,
        "extra_body": {"diffusion_steps": passes},  # dlmserve-style knob; adjust to server
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read().decode())
    text = out["choices"][0]["message"]["content"]
    return [ln.strip(" -*0123456789.") for ln in text.splitlines() if ln.strip()]


def generate(scenario, protocol, passes, backend="mock", rng=None):
    if backend == "mock":
        return mock_generate(scenario, protocol, passes, rng or random.Random(0))
    if backend == "diffusion":
        return diffusion_generate(scenario, protocol, passes)
    raise ValueError(backend)
