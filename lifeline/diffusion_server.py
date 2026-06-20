"""
THE LIFELINE PRODUCT — live emergency first-aid voice assistant on real DiffusionGemma.

Loads DiffusionGemma once, serves the polished UI (lifeline.ui_page) + a /ask endpoint that
runs the full engine: recognize (lifeline.triage) -> adaptive best-of-N at a good denoising
depth -> verify each candidate against the protocol -> speak the FIRST verified answer, or
fall back to the canonical protocol (NEVER an unverified step). Easy emergencies resolve in
1 try (instant); hard ones escalate to MAX_N then fall back. Runs ON the GPU box.

    python3 -m lifeline.diffusion_server      # then tunnel 8080 and open http://localhost:8080
"""
from __future__ import annotations
import copy
import json
import os
import signal
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import torch
from transformers import AutoTokenizer
from transformers.models.diffusion_gemma import DiffusionGemmaForBlockDiffusion

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from lifeline.real_run import PROMPT, verify          # noqa: E402  (concept-group verifier)
from lifeline.triage import recognize, CANON, PROTO_NAME  # noqa: E402
from lifeline.ui_page import PAGE, MANIFEST, ICON_SVG, SW_JS  # noqa: E402

MODEL = os.environ.get("LIFELINE_MODEL", "unsloth/diffusiongemma-26B-A4B-it")
STEPS = int(os.environ.get("STEPS", "16"))   # denoising depth (peak quality/latency point)
MAX_N = int(os.environ.get("MAX_N", "8"))    # effort-manager cap (fail-fast to safe fallback)
PORT = int(os.environ.get("LIFELINE_PORT", "8080"))

print(f"loading {MODEL} …", flush=True)
_t = time.time()
TOK = AutoTokenizer.from_pretrained(MODEL)
MODEL_OBJ = DiffusionGemmaForBlockDiffusion.from_pretrained(MODEL, dtype=torch.bfloat16, device_map={"": 0})
MODEL_OBJ.eval()
BASE_GC = MODEL_OBJ.generation_config
print(f"ready in {time.time()-_t:.0f}s — Lifeline product on http://localhost:{PORT}", flush=True)


def gen_one(q: str, steps: int) -> str:
    enc = TOK.apply_chat_template([{"role": "user", "content": PROMPT.format(q=q)}],
                                  add_generation_prompt=True, return_tensors="pt", return_dict=True)
    ids = enc["input_ids"].to(MODEL_OBJ.device)
    gc = copy.deepcopy(BASE_GC)
    gc.max_denoising_steps = steps
    gc.max_new_tokens = 256

    def _to(s, f):
        raise TimeoutError()
    signal.signal(signal.SIGALRM, _to)
    signal.alarm(int(os.environ.get("GEN_TIMEOUT", "60")))
    try:
        with torch.no_grad():
            out = MODEL_OBJ.generate(input_ids=ids, generation_config=gc)
    finally:
        signal.alarm(0)
    seq = out.sequences if hasattr(out, "sequences") else out
    return TOK.decode(seq[0][ids.shape[1]:], skip_special_tokens=True)


def answer(transcript: str) -> dict:
    key = recognize(transcript)
    if key is None:
        return {"recognized": False, "spoken": "I can't identify this emergency. Call 911 now and describe what you see.",
                "answer": ["Call 911 now."], "candidates": [], "verified": True, "fallback": False}

    t0 = time.time()
    cands, chosen = [], None
    for _ in range(MAX_N):
        try:
            txt = gen_one(transcript, STEPS)
        except Exception:  # noqa: BLE001  (timeout/gen error -> failed candidate; fall back to canon)
            cands.append({"ok": False, "preview": "generation timed out"})
            continue
        ok = verify(txt, key)
        first = next((ln.strip(" -*0123456789.") for ln in txt.splitlines() if ln.strip()), "")
        cands.append({"ok": ok, "preview": first[:80]})
        if ok:
            chosen = txt
            break

    fallback = chosen is None
    steps_out = ([ln.strip(" -*0123456789.") for ln in chosen.splitlines() if ln.strip()][:7] if chosen else CANON[key])
    regime = "routine" if len(cands) <= 2 else ("moderate" if len(cands) <= 5 else "critical")
    return {"recognized": True, "protocol": PROTO_NAME.get(key, key), "key": key, "regime": regime,
            "n_used": len(cands), "denoising_steps": STEPS, "candidates": cands,
            "verified": not fallback, "fallback": fallback, "answer": steps_out,
            "latency_ms": int((time.time() - t0) * 1000), "transcript": transcript}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        p = self.path
        if p in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif p == "/manifest.webmanifest":
            self._send(200, MANIFEST, "application/manifest+json")
        elif p == "/icon.svg":
            self._send(200, ICON_SVG, "image/svg+xml")
        elif p == "/sw.js":
            self._send(200, SW_JS, "text/javascript")
        else:
            self._send(404, "nf", "text/plain")

    def do_POST(self):
        if self.path != "/ask":
            self._send(404, "nf", "text/plain"); return
        n = int(self.headers.get("Content-Length", 0))
        try:
            res = answer(str(json.loads(self.rfile.read(n) or b"{}").get("text", "")))
            self._send(200, json.dumps(res), "application/json")
        except Exception:  # noqa: BLE001  (never break the UI contract — return a safe fallback)
            self._send(200, json.dumps({"recognized": False, "spoken": "Technical issue. Call 911 now.",
                                        "answer": ["Call 911 now."], "candidates": [], "verified": True,
                                        "fallback": False}), "application/json")


def main():
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()


if __name__ == "__main__":
    main()
