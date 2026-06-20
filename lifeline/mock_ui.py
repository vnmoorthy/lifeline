"""Local UI preview (no GPU) — serves the real polished PAGE with a realistic MOCK engine,
so the product UI/UX can be built and demoed without the model. Same /ask contract as the
real diffusion_server, so the UI is identical to production.

    python3 -m lifeline.mock_ui     # http://localhost:8090
"""
from __future__ import annotations
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from lifeline.triage import recognize, CANON, PROTO_NAME  # noqa: E402
from lifeline.ui_page import PAGE  # noqa: E402

PORT = int(os.environ.get("LIFELINE_PORT", "8090"))
# Illustrative per-case difficulty for the UI preview only (how many tries the effort-manager
# spends). Real verify rates are re-measured on the GPU with the fixed negation-aware verifier;
# burn was previously over-counted because correct "do not apply ice" answers were wrongly rejected.
DIFFICULTY = {"cpr": 1, "choke": 1, "bleed": 1, "od": 1, "burn": 4}


def mock_answer(text: str) -> dict:
    key = recognize(text)
    if key is None:
        return {"recognized": False, "spoken": "I can't identify this emergency. Call 911 now and describe what you see.",
                "answer": ["Call 911 now."], "candidates": [], "verified": True, "fallback": False}
    need = DIFFICULTY.get(key, 1)
    cands = [{"ok": False, "preview": ""} for _ in range(need - 1)] + [{"ok": True, "preview": ""}]
    cands = cands[:8]
    fallback = not any(c["ok"] for c in cands)
    regime = "routine" if len(cands) <= 2 else ("moderate" if len(cands) <= 5 else "critical")
    time.sleep(0.25 * len(cands))  # simulate generation time
    return {"recognized": True, "protocol": PROTO_NAME[key], "key": key, "regime": regime,
            "n_used": len(cands), "denoising_steps": 16, "candidates": cands,
            "verified": not fallback, "fallback": fallback, "answer": CANON[key],
            "latency_ms": int(len(cands) * 1800), "transcript": text}


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
        self._send(200, PAGE, "text/html; charset=utf-8") if self.path in ("/", "/index.html") else self._send(404, "nf", "text/plain")

    def do_POST(self):
        if self.path != "/ask":
            self._send(404, "nf", "text/plain"); return
        n = int(self.headers.get("Content-Length", 0))
        res = mock_answer(str(json.loads(self.rfile.read(n) or b"{}").get("text", "")))
        self._send(200, json.dumps(res), "application/json")


if __name__ == "__main__":
    print(f"Lifeline UI preview (mock) on http://localhost:{PORT}")
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()
