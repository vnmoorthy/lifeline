"""
The live voice demo server (stdlib only — nothing to install).

    python3 -m lifeline.server          # mock engine ($0)
    LIFELINE_BASE_URL=... python3 -m lifeline.server   # uses the real diffusion model

Open http://localhost:8080 — press Speak (or type), and it talks you through verified
first-aid: instant on routine, more refinement on hard cases, never an unverified step.
Browser does speech-to-text + text-to-speech (Web Speech API); the engine runs here.
"""
from __future__ import annotations
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from lifeline.engine import answer  # noqa: E402

PORT = int(os.environ.get("LIFELINE_PORT", "8080"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, code, body, ctype):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        if self.path != "/ask":
            self._send(404, "not found", "text/plain")
            return
        n = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(n) or b"{}")
            res = answer(str(payload.get("text", "")))
            self._send(200, json.dumps(res), "application/json")
        except Exception as e:  # noqa: BLE001
            self._send(500, json.dumps({"error": str(e)}), "application/json")


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lifeline</title><style>
:root{--bg:#0b0f14;--panel:#13181f;--line:#222b36;--text:#e6edf3;--dim:#8b97a6;--green:#3fb950;--red:#f85149;--amber:#e3b341}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 -apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:680px;margin:0 auto;padding:28px 20px 60px;text-align:center}
h1{font-size:30px;margin:6px 0 2px}.tag{color:var(--dim);margin-bottom:20px}
button{cursor:pointer;border:0;border-radius:999px;padding:18px 34px;font-size:18px;font-weight:800;background:var(--red);color:#fff}
button:active{transform:scale(.97)}#mic.listening{background:var(--amber);color:#111}
.row{margin:14px 0}.transcript{font-size:20px;min-height:28px;color:var(--text)}
.meta{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin:14px 0}
.badge{font-size:13px;padding:4px 11px;border-radius:999px;border:1px solid var(--line)}
.routine{color:var(--green)}.moderate{color:var(--amber)}.critical{color:var(--red)}.unknown{color:var(--dim)}
.dial{font-variant-numeric:tabular-nums}
.verified{background:rgba(63,185,80,.14);color:var(--green);border-color:rgba(63,185,80,.4)}
.fallback{background:rgba(227,179,65,.14);color:var(--amber);border-color:rgba(227,179,65,.4)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;margin-top:16px;text-align:left}
ol{margin:0;padding-left:22px}li{margin:8px 0;opacity:0;transform:translateY(6px);transition:all .3s}
li.in{opacity:1;transform:none}.proto{color:var(--dim);font-size:13px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
input{width:70%;padding:10px;border-radius:10px;border:1px solid var(--line);background:#0b0f14;color:var(--text);font-size:15px}
.hint{color:var(--dim);font-size:13px;margin-top:10px}
</style></head><body><div class="wrap">
<h1>Lifeline</h1><div class="tag">Hands-free first aid — fast on routine, harder on hard, never an unverified step.</div>
<div class="row"><button id="mic">🎙 Hold &amp; speak the emergency</button></div>
<div class="row"><input id="txt" placeholder="…or type it, e.g. he's choking and passed out"> <button id="go" style="padding:10px 18px;font-size:15px;background:#222b36">Ask</button></div>
<div class="row transcript" id="transcript"></div>
<div class="meta" id="meta"></div>
<div class="card" id="card" style="display:none"><div class="proto" id="proto"></div><ol id="steps"></ol></div>
<div class="hint">Speech uses your browser (Chrome works best). The engine runs locally.</div>
</div>
<script>
const $=i=>document.getElementById(i);
function speak(t){try{const u=new SpeechSynthesisUtterance(t);u.rate=1.05;speechSynthesis.speak(u);}catch(e){}}
async function ask(text){
  $('transcript').textContent='“ '+text+' ”';
  $('meta').innerHTML='<span class="badge">thinking…</span>';
  $('card').style.display='none';$('steps').innerHTML='';
  const t0=performance.now();
  let r; try{ r=await (await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})})).json(); }
  catch(e){ $('meta').innerHTML='<span class="badge critical">server error</span>'; return; }
  const reg=r.regime||'unknown';
  $('meta').innerHTML=
    `<span class="badge ${reg}">${reg}</span>`+
    `<span class="badge dial">${r.passes} refinement passes · ${r.latency_ms}ms</span>`+
    `<span class="badge ${r.fallback?'fallback':'verified'}">${r.fallback?'✓ verified (protocol fallback)':'✓ model-verified'}</span>`;
  if(!r.recognized){ $('transcript').textContent='“ '+text+' ”'; speak(r.spoken); $('card').style.display='block'; $('proto').textContent='unrecognized'; addSteps([r.spoken]); return; }
  $('card').style.display='block'; $('proto').textContent=r.protocol;
  addSteps(r.steps); speak(r.protocol+'. '+r.steps.join('. '));
}
function addSteps(steps){
  const ol=$('steps'); ol.innerHTML='';
  steps.forEach((s,i)=>{ const li=document.createElement('li'); li.textContent=s; ol.appendChild(li); setTimeout(()=>li.classList.add('in'), 120*i); });
}
$('go').onclick=()=>{ if($('txt').value.trim()) ask($('txt').value.trim()); };
$('txt').addEventListener('keydown',e=>{ if(e.key==='Enter'&&$('txt').value.trim()) ask($('txt').value.trim()); });
// voice
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
if(SR){ const rec=new SR(); rec.lang='en-US'; rec.interimResults=false;
  const mic=$('mic');
  mic.onclick=()=>{ try{ rec.start(); mic.classList.add('listening'); mic.textContent='🎙 listening…'; }catch(e){} };
  rec.onresult=e=>{ const t=e.results[0][0].transcript; ask(t); };
  rec.onend=()=>{ mic.classList.remove('listening'); mic.textContent='🎙 Hold & speak the emergency'; };
} else { $('mic').textContent='🎙 (mic unsupported — type below)'; $('mic').disabled=true; }
</script></body></html>
"""


def main():
    print(f"Lifeline voice demo on http://localhost:{PORT}  "
          f"[engine={'diffusion' if os.environ.get('LIFELINE_BASE_URL') else 'mock'}]")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
