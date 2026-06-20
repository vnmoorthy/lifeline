"""
THE REAL denoising experiment on DiffusionGemma (the 10-day-old Google block-diffusion model).

Inference-time-compute knob = max_denoising_steps (actual diffusion refinement passes, NOT
best-of-N). Effort-manager = the model's native confidence_threshold (stop denoising early
when confident -> few steps on easy emergencies, more on hard ones). Verifier = the same
grounded concept-group protocol check. Runs ON the GPU box (HF transformers, device_map=auto).

    python3 -m lifeline.diffusion_run --test          # one generation, prints output + timing
    python3 -m lifeline.diffusion_run                  # full sweep -> dashboard_lifeline/diffusion_results.json
"""
from __future__ import annotations
import copy
import json
import os
import signal
import statistics
import sys
import time

import torch
from transformers import AutoTokenizer
from transformers.models.diffusion_gemma import DiffusionGemmaForBlockDiffusion
from transformers.models.diffusion_gemma.generation_diffusion_gemma import DiffusionGemmaGenerationConfig

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from lifeline.real_run import PROTO, SCENARIOS, PROMPT, verify  # noqa: E402

MODEL = os.environ.get("LIFELINE_MODEL", "unsloth/diffusiongemma-26B-A4B-it")
STEPS_GRID = [int(x) for x in os.environ.get("STEPS_GRID", "4,8,16,32,64").split(",")]
SAMPLES = int(os.environ.get("SAMPLES", "2"))
MAX_NEW = int(os.environ.get("MAX_NEW", "256"))

print(f"loading {MODEL} (this takes a minute)…", flush=True)
_t = time.time()
tok = AutoTokenizer.from_pretrained(MODEL)
model = DiffusionGemmaForBlockDiffusion.from_pretrained(MODEL, dtype=torch.bfloat16, device_map={"": 0})
model.eval()
try:
    BASE_GC = model.generation_config  # native DiffusionGemmaGenerationConfig w/ sane defaults
except Exception:
    BASE_GC = DiffusionGemmaGenerationConfig()
print(f"loaded in {time.time()-_t:.0f}s; default gen config: max_denoising_steps="
      f"{getattr(BASE_GC,'max_denoising_steps',None)}, conf_thr={getattr(BASE_GC,'confidence_threshold',None)}", flush=True)


def generate(q: str, max_steps: int, conf: float | None = None) -> str:
    msgs = [{"role": "user", "content": PROMPT.format(q=q)}]
    enc = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True)
    ids = enc["input_ids"].to(model.device)
    gc = copy.deepcopy(BASE_GC)
    gc.max_denoising_steps = max_steps
    gc.max_new_tokens = MAX_NEW
    if conf is not None:
        gc.confidence_threshold = conf

    def _timeout(signum, frame):
        raise TimeoutError("generation exceeded GEN_TIMEOUT")
    signal.signal(signal.SIGALRM, _timeout)
    signal.alarm(int(os.environ.get("GEN_TIMEOUT", "90")))
    try:
        with torch.no_grad():
            out = model.generate(input_ids=ids, generation_config=gc)
    finally:
        signal.alarm(0)
    seq = out.sequences if hasattr(out, "sequences") else out
    text = tok.decode(seq[0][ids.shape[1]:], skip_special_tokens=True)
    return text


def main():
    if "--test" in sys.argv:
        for steps in (4, 32):
            t0 = time.time()
            txt = generate(SCENARIOS[0]["q"], steps)
            ok = verify(txt, SCENARIOS[0]["proto"])
            print(f"\n=== steps={steps}  ({time.time()-t0:.1f}s)  verified={ok} ===\n{txt[:600]}", flush=True)
        return

    # accuracy vs denoising steps
    curve = {}
    for s in STEPS_GRID:
        per = []
        for sc in SCENARIOS:
            hits = [1.0 if verify(generate(sc["q"], s), sc["proto"]) else 0.0 for _ in range(SAMPLES)]
            per.append(statistics.mean(hits))
            print(f"  steps={s} {sc['id']}: {per[-1]:.2f}", flush=True)
        curve[s] = round(statistics.mean(per), 4)
        print(f"== steps={s} -> acc={curve[s]:.3f}", flush=True)

    # native adaptive effort-manager: confidence-based early stop (cap at max steps)
    conf = float(os.environ.get("CONF", "0.9"))
    ctrl = []
    for sc in SCENARIOS:
        hits = [1.0 if verify(generate(sc["q"], STEPS_GRID[-1], conf=conf), sc["proto"]) else 0.0 for _ in range(SAMPLES)]
        ctrl.append(statistics.mean(hits))
        print(f"  [adaptive conf={conf}] {sc['id']}: {ctrl[-1]:.2f}", flush=True)
    ctrl_acc = round(statistics.mean(ctrl), 4)

    data = {"project": "Lifeline", "real": True, "model": MODEL, "knob": "max_denoising_steps",
            "grid": STEPS_GRID, "curve": [curve[s] for s in STEPS_GRID],
            "single_lowstep": curve[STEPS_GRID[0]], "best": curve[STEPS_GRID[-1]],
            "adaptive": {"confidence_threshold": conf, "acc": ctrl_acc}}
    out = os.path.join(BASE, "dashboard_lifeline")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "diffusion_results.json"), "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n  steps {STEPS_GRID}: acc {[curve[s] for s in STEPS_GRID]}")
    print(f"  adaptive (conf={conf}): {ctrl_acc}")
    print(f"  -> dashboard_lifeline/diffusion_results.json")


if __name__ == "__main__":
    main()
