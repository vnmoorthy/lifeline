"""Render dashboard_lifeline/real.html from real_results.json (the measured run)."""
from __future__ import annotations
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    p = os.path.join(BASE, "dashboard_lifeline", "real_results.json")
    d = json.load(open(p))
    html = TEMPLATE.replace("/*__DATA__*/", json.dumps(d))
    out = os.path.join(BASE, "dashboard_lifeline", "real.html")
    open(out, "w").write(html)
    print(f"wrote {out}")


TEMPLATE = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lifeline — measured</title><style>
:root{--bg:#0b0f14;--panel:#13181f;--line:#222b36;--text:#e6edf3;--dim:#8b97a6;--green:#3fb950;--red:#f85149;--amber:#e3b341;--blue:#58a6ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.55 -apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:26px 20px 60px}h1{margin:0;font-size:26px}
.tag{color:var(--dim);margin-top:4px}.banner{margin:12px 0;padding:8px 12px;border-radius:8px;font-size:13px;font-weight:600;background:rgba(63,185,80,.13);color:var(--green);border:1px solid rgba(63,185,80,.4)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin-top:16px}
.card h2{font-size:12px;text-transform:uppercase;letter-spacing:.6px;color:var(--dim);margin:0 0 12px}
.kpis{display:flex;gap:22px;flex-wrap:wrap}.kpi{flex:1;min-width:130px}.kpi .v{font-size:30px;font-weight:800}
.kpi .l{color:var(--dim);font-size:12px}.green{color:var(--green)}.amber{color:var(--amber)}.dimv{color:var(--dim)}
.grid{display:grid;grid-template-columns:1.1fr 1fr;gap:16px}@media(max-width:820px){.grid{grid-template-columns:1fr}}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
th{color:var(--dim);font-size:11px;text-transform:uppercase}.pill{font-size:11px;padding:1px 7px;border-radius:6px}
.routine{color:var(--green)}.moderate{color:var(--amber)}.critical{color:var(--red)}
.legend{display:flex;gap:16px;font-size:12px;margin-top:8px}.dot{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:5px}
</style></head><body><div class="wrap">
<h1>Lifeline <span class="dimv" style="font-size:15px">— measured on a live model</span></h1>
<div class="tag">Emergency first aid: a weak single answer, made reliable by verified best-of-N — compute spent only where it's needed.</div>
<div class="banner" id="banner"></div>
<div class="card"><h2>Headline (real model output, grounded verifier)</h2><div class="kpis">
<div class="kpi"><div class="v green" id="k-best"></div><div class="l">best-of-<span id="k-bn"></span> accuracy</div></div>
<div class="kpi"><div class="v" id="k-single"></div><div class="l">single answer (N=1)</div></div>
<div class="kpi"><div class="v amber" id="k-ctrl"></div><div class="l">effort-manager accuracy</div></div>
<div class="kpi"><div class="v" id="k-save"></div><div class="l">of the samples it used</div></div>
</div></div>
<div class="grid">
<div class="card"><h2>Accuracy vs. samples (N)</h2><div id="chart"></div>
<div class="legend"><span><i class="dot" style="background:var(--blue)"></i>best-of-N</span>
<span><i class="dot" style="background:var(--amber)"></i>effort-manager (adaptive)</span>
<span><i class="dot" style="background:var(--dim)"></i>single answer</span></div></div>
<div class="card"><h2>Per-emergency: how many tries it spent</h2><table><thead><tr><th>emergency</th><th>1-shot</th><th>spent</th></tr></thead><tbody id="rows"></tbody></table></div>
</div></div>
<script>
const D=/*__DATA__*/;const $=i=>document.getElementById(i);
$('banner').textContent='● REAL — model '+D.model+' · knob: '+D.knob+' · verified against documented protocols (no LLM judge)';
const ks=D.grid,mx=Math.max(...ks);
$('k-best').textContent=(D.curve[D.curve.length-1]*100).toFixed(0)+'%';
$('k-bn').textContent=mx;$('k-single').textContent=(D.single_shot*100).toFixed(0)+'%';
$('k-ctrl').textContent=(D.controller.acc*100).toFixed(0)+'%';
$('k-save').textContent=Math.round(D.controller.avg_n/mx*100)+'%';
const W=460,H=280,P={l:42,r:16,t:14,b:34};
const x=v=>P.l+(W-P.l-P.r)*(Math.log2(v)/Math.log2(mx)),y=v=>P.t+(H-P.t-P.b)*(1-v);
let g='';for(let t=0;t<=1.001;t+=.25){g+=`<line x1="${P.l}" y1="${y(t)}" x2="${W-P.r}" y2="${y(t)}" stroke="#222b36"/><text x="${P.l-8}" y="${y(t)+4}" fill="#8b97a6" font-size="10" text-anchor="end">${t*100|0}%</text>`;}
ks.forEach(k=>{g+=`<text x="${x(k)}" y="${H-P.b+16}" fill="#8b97a6" font-size="10" text-anchor="middle">${k}</text>`;});
g+=`<text x="${(P.l+W-P.r)/2}" y="${H-2}" fill="#8b97a6" font-size="11" text-anchor="middle">N samples (best-of-N, log)</text>`;
g+=`<line x1="${P.l}" y1="${y(D.single_shot)}" x2="${W-P.r}" y2="${y(D.single_shot)}" stroke="#8b97a6" stroke-dasharray="4 3"/>`;
g+=`<polyline points="${ks.map((k,i)=>x(k)+','+y(D.curve[i])).join(' ')}" fill="none" stroke="#58a6ff" stroke-width="2.4"/>`;
ks.forEach((k,i)=>{g+=`<circle cx="${x(k)}" cy="${y(D.curve[i])}" r="2.6" fill="#58a6ff"/>`;});
const cx=x(Math.max(1,D.controller.avg_n)),cy=y(D.controller.acc);
g+=`<circle cx="${cx}" cy="${cy}" r="6" fill="#e3b341"/><text x="${cx+9}" y="${cy+4}" fill="#e3b341" font-size="11">effort-mgr: ${(D.controller.acc*100).toFixed(0)}% @ N=${D.controller.avg_n.toFixed(1)}</text>`;
$('chart').innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%">${g}</svg>`;
$('rows').innerHTML=D.scenarios.map(r=>`<tr><td>${r.q}<div class="dimv" style="font-size:11px">${r.proto}</div></td>`
 +`<td>${(r.single_p*100).toFixed(0)}%</td><td><span class="pill ${r.regime}">${r.regime}</span> N=${r.chosen_n} · ${(r.acc*100).toFixed(0)}%</td></tr>`).join('');
</script></body></html>
"""


if __name__ == "__main__":
    main()
