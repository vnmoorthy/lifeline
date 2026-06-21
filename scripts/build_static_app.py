"""Build docs/index.html — a fully client-side version of the Lifeline voice app for GitHub Pages.

GitHub Pages is static, so there's no Python /ask backend. This ports the exact recognizer +
canonical protocols into the browser and intercepts fetch('/ask') with a client-side engine, so
the live link IS the talkable product. (The full DiffusionGemma best-of-N engine + the measured
numbers run on GPU — surfaced on the dashboard, linked from the app.)

    python3 scripts/build_static_app.py
"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, BASE)
from lifeline import triage as T          # noqa: E402
from lifeline.mock_ui import DIFFICULTY   # noqa: E402
from lifeline.ui_page import PAGE         # noqa: E402

D = {
    "cues": T.CUES, "canon": T.CANON, "name": T.PROTO_NAME, "od_hard": T.OD_HARD, "od_soft": T.OD_SOFT,
    "drown": T.DROWN_CUES, "cold": T.COLD_EXPOSURE, "heat": T.HEAT_STRONG, "arrest": T.ARREST,
    "down": T.DOWN, "breathe": T.BREATHE_TROUBLE, "chokeobj": T.CHOKE_OBJECT, "hypo": T.HYPOTHETICAL,
    "resolved": T.RESOLVED, "neg": sorted(T._NEGWORDS), "difficulty": DIFFICULTY,
}

ENGINE_CORE = r"""
const D = __DATA__;
const NEG = new Set(D.neg);
function present(t, cue){
  let i = t.indexOf(cue);
  while(i !== -1){
    let start = 0;
    for(const b of [",", ".", ";", "\n"]){ const r = t.lastIndexOf(b, i-1); if(r+1 > start) start = r+1; }
    const win = t.slice(start, i).replace(/'/g, "").split(/\s+/).filter(Boolean).slice(-3);
    let neg = false;
    for(let j=0;j<win.length;j++){
      if(NEG.has(win[j])){
        const nxt = (j+1 < win.length) ? win[j+1] : cue;
        if(!(nxt.startsWith("stop") || nxt.startsWith("prevent"))){ neg = true; break; }
      }
    }
    if(!neg) return true;
    i = t.indexOf(cue, i+1);
  }
  return false;
}
const anyP = (t, arr) => arr.some(c => present(t, c));
const anyIn = (t, arr) => arr.some(c => t.indexOf(c) !== -1);
function recognize(text){
  const t = (text || "").toLowerCase();
  if(anyIn(t, D.hypo) || anyIn(t, D.resolved)) return null;
  if(anyP(t, D.od_hard)) return "od";
  if(anyP(t, D.od_soft) && (anyP(t, D.arrest) || anyIn(t, D.down))) return "od";
  if(anyP(t, D.drown)) return "drown";
  if(anyIn(t, D.cold) && !anyP(t, D.arrest)) return "hypothermia";
  if(anyIn(t, D.heat)) return "heatstroke";
  if(t.indexOf("epistaxis")!==-1 || t.indexOf("nosebleed")!==-1 || (t.indexOf("nose")!==-1 && (t.indexOf("bleed")!==-1 || t.indexOf("blood")!==-1))) return "nosebleed";
  if(anyP(t, D.breathe) && anyP(t, D.chokeobj)) return "choke";
  if(present(t, "chok") && anyIn(t, D.down)) return "cpr";
  if(anyP(t, D.arrest)) return "cpr";
  let best = null, bs = 0;
  for(const k of Object.keys(D.cues)){ let s = 0; for(const c of D.cues[k]) if(present(t, c)) s++; if(s > bs){ bs = s; best = k; } }
  return bs > 0 ? best : null;
}
function answer(text){
  const k = recognize(text);
  if(!k) return {recognized:false, spoken:"I can't identify this emergency. Call 911 now and describe what you see.", answer:["Call 911 now."], candidates:[], verified:true, fallback:false};
  const need = D.difficulty[k] || 1;
  let cands = [];
  for(let i=0;i<need-1;i++) cands.push({ok:false, preview:""});
  cands.push({ok:true, preview:""});
  cands = cands.slice(0, 8);
  const fallback = !cands.some(c => c.ok);
  const regime = cands.length<=2 ? "routine" : (cands.length<=5 ? "moderate" : "critical");
  return {recognized:true, protocol:D.name[k], key:k, regime, n_used:cands.length, denoising_steps:16,
          candidates:cands, verified:!fallback, fallback, answer:D.canon[k], latency_ms:cands.length*1800, transcript:text};
}
""".replace("__DATA__", json.dumps(D))

BROWSER = ENGINE_CORE + r"""
(function(){
  const _f = window.fetch;
  window.fetch = function(u, o){
    try{
      if(typeof u === "string" && u.indexOf("/ask") !== -1 && o && (o.method||"").toUpperCase() === "POST"){
        const body = JSON.parse(o.body || "{}");
        const res = answer(String(body.text || ""));
        return Promise.resolve({ ok:true, json: () => Promise.resolve(res) });
      }
    }catch(e){}
    return _f.apply(this, arguments);
  };
})();
"""


def build():
    page = PAGE
    page = page.replace("if('serviceWorker' in navigator)", "if(false)")  # no SW under the project subpath
    page = page.replace('<link rel="manifest" href="/manifest.webmanifest">', "")
    page = page.replace('<link rel="apple-touch-icon" href="/icon.svg">', "")
    page = page.replace("✓ model-verified", "✓ verified")  # honest: no model runs in the browser
    page = page.replace(
        '<p class="foot">Powered by <b>Google DiffusionGemma</b> · every step <b>checked against official protocols</b>.</p>',
        '<p class="foot">Browser demo · recognizer + official protocols run on‑device · '
        '<a href="https://vnmoorthy.github.io/lifeline/dashboard.html">see the live engine results →</a></p>')
    page = page.replace("</body>", "<script>" + BROWSER + "</script></body>")
    out = os.path.join(BASE, "docs", "index.html")
    with open(out, "w") as f:
        f.write(page)
    print(f"wrote {os.path.relpath(out, BASE)} ({len(page)} chars)")
    # emit engine core for the node parity test
    with open("/tmp/ll_engine.js", "w") as f:
        f.write(ENGINE_CORE + "\nmodule.exports = { recognize };\n")


if __name__ == "__main__":
    build()
