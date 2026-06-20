"""
THE LIFELINE PRODUCT — live emergency first-aid voice assistant on real DiffusionGemma.

Loads DiffusionGemma once, then serves a voice UI + /ask endpoint that runs the full engine:
  recognize emergency -> adaptive best-of-N at a good denoising depth -> verify each candidate
  against the protocol -> speak the FIRST verified answer (or fall back to the canonical
  protocol, so it NEVER speaks an unverified step). Easy emergencies resolve in 1-2 tries
  (instant); hard ones escalate (the effort-manager). Runs ON the GPU box.

    python3 -m lifeline.diffusion_server      # then open http://localhost:8080 (via tunnel)
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
from lifeline.real_run import PROTO, PROMPT, verify  # noqa: E402  (concept-group verifier)

MODEL = os.environ.get("LIFELINE_MODEL", "unsloth/diffusiongemma-26B-A4B-it")
STEPS = int(os.environ.get("STEPS", "16"))      # denoising depth (peak quality/latency point)
MAX_N = int(os.environ.get("MAX_N", "12"))      # effort-manager cap
PORT = int(os.environ.get("LIFELINE_PORT", "8080"))

# transcript -> protocol key (PROTO keys: cpr/choke/bleed/od/burn). Unresponsive/not-breathing
# overrides to CPR (life-threatening). Canonical steps are the safe fallback (always verify-pass).
CUES = {
    "cpr":   ["not breathing", "isn't breathing", "collapsed", "unresponsive", "no pulse", "cardiac", "heart attack", "passed out", "unconscious"],
    "choke": ["choking", "can't breathe", "cant breathe", "object stuck", "something stuck", "throat"],
    "bleed": ["bleeding", "blood", "cut", "wound", "gushing", "spurting", "hemorrhage"],
    "od":    ["overdose", "opioid", "fentanyl", "heroin", "blue lips", "naloxone", "narcan", "pinpoint"],
    "burn":  ["burn", "burned", "scald", "boiling water", "steam", "fire", "hot water"],
}
CANON = {
    "cpr":   ["Call 911 and get an AED.", "Push hard and fast in the center of the chest, 100-120 per minute, about 2 inches deep.", "Let the chest recoil fully between compressions.", "Continue until an AED or help arrives."],
    "choke": ["Give 5 firm back blows between the shoulder blades.", "Give 5 abdominal thrusts (Heimlich).", "Alternate back blows and thrusts until it clears.", "If they go unconscious, call 911 and start CPR."],
    "bleed": ["Call 911 for severe bleeding.", "Apply firm direct pressure with a clean cloth.", "Do not remove soaked cloths — add more on top.", "If life-threatening limb bleeding, apply a tourniquet above the wound."],
    "od":    ["Call 911.", "Give naloxone (Narcan) if available.", "If not breathing, start rescue breaths or CPR.", "Place them in the recovery position if breathing returns."],
    "burn":  ["Cool the burn under cool running water for 20 minutes.", "Cover loosely with a clean non-stick dressing.", "Do not apply ice or butter, and do not pop blisters."],
}
URGENT = ["not breathing", "isn't breathing", "unresponsive", "passed out", "unconscious", "no pulse"]


def recognize(t: str):
    t = (t or "").lower()
    if any(u in t for u in URGENT) and not any(c in t for c in CUES["od"]):
        return "cpr"
    best, score = None, 0
    for k, cues in CUES.items():
        s = sum(1 for c in cues if c in t)
        if s > score:
            best, score = k, s
    return best if score else None


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
                "answer": ["Call 911 now."], "candidates": [], "verified": True, "fallback": False, "regime": "unknown",
                "n_used": 0, "denoising_steps": STEPS, "latency_ms": 0, "protocol": None, "transcript": transcript}

    t0 = time.time()
    cands, chosen = [], None
    for _ in range(MAX_N):
        txt = gen_one(transcript, STEPS)
        ok = verify(txt, key)
        first = next((ln.strip(" -*0123456789.") for ln in txt.splitlines() if ln.strip()), "")
        cands.append({"ok": ok, "preview": first[:80]})
        if ok:
            chosen = txt
            break

    fallback = chosen is None
    steps_out = ([ln.strip(" -*0123456789.") for ln in chosen.splitlines() if ln.strip()] if chosen else CANON[key])
    regime = "routine" if len(cands) <= 2 else ("moderate" if len(cands) <= 6 else "critical")
    return {"recognized": True, "protocol": PROTO_NAME.get(key, key), "key": key, "regime": regime,
            "n_used": len(cands), "denoising_steps": STEPS, "candidates": cands,
            "verified": not fallback, "fallback": fallback, "answer": steps_out,
            "latency_ms": int((time.time() - t0) * 1000), "transcript": transcript}


PROTO_NAME = {"cpr": "Cardiac arrest (CPR)", "choke": "Choking", "bleed": "Severe bleeding",
              "od": "Opioid overdose", "burn": "Burn"}


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
        try:
            res = answer(str(json.loads(self.rfile.read(n) or b"{}").get("text", "")))
            self._send(200, json.dumps(res), "application/json")
        except Exception as e:  # noqa: BLE001
            self._send(500, json.dumps({"error": str(e)}), "application/json")


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lifeline</title><style>
:root{--bg:#0b0f14;--panel:#13181f;--line:#222b36;--text:#e6edf3;--dim:#8b97a6;--green:#3fb950;--red:#f85149;--amber:#e3b341}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 -apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:720px;margin:0 auto;padding:26px 20px 60px;text-align:center}
h1{font-size:30px;margin:0}.tag{color:var(--dim);margin-bottom:18px}
button{cursor:pointer;border:0;border-radius:999px;padding:16px 30px;font-size:18px;font-weight:800;background:var(--red);color:#fff}
#mic.on{background:var(--amber);color:#111}
input{width:64%;padding:11px;border-radius:10px;border:1px solid var(--line);background:#0b0f14;color:var(--text);font-size:15px}
.go{padding:11px 18px;font-size:15px;background:#222b36}
.transcript{font-size:20px;min-height:26px;margin:14px 0}
.meta{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:8px 0}
.badge{font-size:13px;padding:3px 10px;border-radius:999px;border:1px solid var(--line)}
.routine{color:var(--green)}.moderate{color:var(--amber)}.critical{color:var(--red)}
.verified{background:rgba(63,185,80,.14);color:var(--green)}.fallback{background:rgba(227,179,65,.14);color:var(--amber)}
.cands{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin:12px 0}
.cell{width:18px;height:18px;border-radius:5px;background:#30363d;transition:.2s}
.cell.ok{background:var(--green)}.cell.bad{background:var(--red)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;margin-top:14px;text-align:left;display:none}
ol{margin:0;padding-left:22px}li{margin:8px 0}.hint{color:var(--dim);font-size:13px;margin-top:12px}
</style></head><body><div class="wrap">
<h1>Lifeline</h1><div class="tag">Hands-free first aid on DiffusionGemma — instant on routine, thinks harder on hard, never an unverified step.</div>
<div><button id="mic">🎙 Hold &amp; speak the emergency</button></div>
<div style="margin-top:12px"><input id="txt" placeholder="…or type, e.g. he collapsed and isn't breathing"> <button class="go" id="go">Ask</button></div>
<div class="transcript" id="t"></div>
<div class="meta" id="meta"></div>
<div class="cands" id="cands"></div>
<div class="card" id="card"><div class="dim" id="proto" style="color:var(--dim);font-size:13px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px"></div><ol id="steps"></ol></div>
<div class="hint">Speech uses your browser; the engine runs DiffusionGemma on-GPU. Decision support — always call 911.</div>
</div>
<script>
const $=i=>document.getElementById(i);
function speak(t){try{const u=new SpeechSynthesisUtterance(t);u.rate=1.05;speechSynthesis.speak(u);}catch(e){}}
async function ask(text){
  $('t').innerHTML='“ <b>'+text+'</b> ”';$('meta').innerHTML='<span class="badge">thinking…</span>';$('cands').innerHTML='';$('card').style.display='none';$('steps').innerHTML='';
  let r;try{r=await(await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})})).json();}catch(e){$('meta').innerHTML='<span class="badge critical">server error</span>';return;}
  if(!r.recognized){$('meta').innerHTML='<span class="badge critical">unrecognized</span>';$('card').style.display='block';$('proto').textContent='call 911';$('steps').innerHTML='<li>'+r.spoken+'</li>';speak(r.spoken);return;}
  $('meta').innerHTML='<span class="badge '+r.regime+'">'+r.regime+'</span>'
    +'<span class="badge">'+r.n_used+' candidate'+(r.n_used>1?'s':'')+' · '+r.denoising_steps+' denoising steps · '+r.latency_ms+'ms</span>'
    +'<span class="badge '+(r.fallback?'fallback':'verified')+'">'+(r.fallback?'✓ verified (protocol fallback)':'✓ model-verified')+'</span>';
  $('cands').innerHTML=r.candidates.map(c=>'<div class="cell '+(c.ok?'ok':'bad')+'" title="'+(c.preview||'').replace(/"/g,'')+'"></div>').join('');
  $('card').style.display='block';$('proto').textContent=r.protocol;
  const ol=$('steps');ol.innerHTML='';r.answer.forEach((s,i)=>{const li=document.createElement('li');li.textContent=s;li.style.opacity=0;ol.appendChild(li);setTimeout(()=>{li.style.transition='.3s';li.style.opacity=1;},140*i);});
  speak(r.protocol+'. '+r.answer.join('. '));
}
$('go').onclick=()=>{if($('txt').value.trim())ask($('txt').value.trim());};
$('txt').addEventListener('keydown',e=>{if(e.key==='Enter'&&$('txt').value.trim())ask($('txt').value.trim());});
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
if(SR){const rec=new SR();rec.lang='en-US';rec.interimResults=false;const m=$('mic');
 m.onclick=()=>{try{rec.start();m.classList.add('on');m.textContent='🎙 listening…';}catch(e){}};
 rec.onresult=e=>ask(e.results[0][0].transcript);rec.onend=()=>{m.classList.remove('on');m.textContent='🎙 Hold & speak the emergency';};
}else{$('mic').textContent='🎙 (type below)';$('mic').disabled=true;}
</script></body></html>
"""


def main():
    HTTPServer(("0.0.0.0", PORT), H).serve_forever()


if __name__ == "__main__":
    main()
