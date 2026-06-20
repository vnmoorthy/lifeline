"""
Lifeline harness -> the measured frontier (accuracy vs refinement compute) + the
effort-manager's win (high accuracy at a fraction of the compute, within the latency
budget) + a dashboard.

    python3 -m lifeline.run                     # frugal: local mock, $0 (SIMULATED)
    python3 -m lifeline.run --backend diffusion --resamples 5   # real model (spends GPU)

Build/debug for free on the mock; flip to --backend diffusion only to capture the real
number and run the demo. The verifier is REAL in both modes — only the generator is mocked.
"""
from __future__ import annotations
import argparse
import json
import os
import random
import statistics

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, BASE)

from lifeline.protocols import SCENARIOS, PROTOCOL_BY_SCENARIO          # noqa: E402
from lifeline.generate import generate                                  # noqa: E402
from lifeline.verifier import is_correct, check_guidance                # noqa: E402
from lifeline.controller import (                                       # noqa: E402
    decide_passes, latency_ms, PER_PASS_MS, LATENCY_BUDGET_MS, MAX_PASSES,
)

PASSES_GRID = [1, 2, 4, 8, 16, 24]


def fixed_curve(backend, resamples, seed=3):
    rng = random.Random(seed)
    acc = {}
    for k in PASSES_GRID:
        per = []
        for sc in SCENARIOS:
            proto = PROTOCOL_BY_SCENARIO[sc["id"]]
            hits = [1.0 if is_correct(generate(sc, proto, k, backend=backend, rng=rng), proto) else 0.0
                    for _ in range(resamples)]
            per.append(statistics.mean(hits))
        acc[k] = round(statistics.mean(per), 4)
    return acc


def controller_eval(backend, resamples, seed=7):
    rng = random.Random(seed)
    gen = lambda sc, pr, k, r: generate(sc, pr, k, backend=backend, rng=r)
    accs, passes_used, per_scenario = [], [], []
    for sc in SCENARIOS:
        proto = PROTOCOL_BY_SCENARIO[sc["id"]]
        hit, used, regimes = [], [], []
        for _ in range(resamples):
            p, regime, conf = decide_passes(sc, proto, is_correct, gen, rng)
            g = gen(sc, proto, p, rng)
            hit.append(1.0 if is_correct(g, proto) else 0.0)
            used.append(p)
            regimes.append(regime)
        accs.append(statistics.mean(hit))
        passes_used.append(statistics.mean(used))
        per_scenario.append({
            "id": sc["id"], "say": sc["say"], "protocol": proto["name"],
            "regime": max(set(regimes), key=regimes.count),
            "passes": round(statistics.mean(used), 1),
            "latency_ms": round(statistics.mean(used) * PER_PASS_MS),
            "acc": round(statistics.mean(hit), 3),
        })
    return round(statistics.mean(accs), 4), round(statistics.mean(passes_used), 2), per_scenario


def run(backend="mock", resamples=200):
    simulated = backend == "mock"
    acc = fixed_curve(backend, resamples)
    ctrl_acc, ctrl_passes, per_scenario = controller_eval(backend, max(resamples // 4, 20) if not simulated else resamples)

    fixed_hi = acc[PASSES_GRID[-1]]
    print(f"\n  Lifeline  [backend={backend}{'  *** SIMULATED ***' if simulated else ''}]  "
          f"{len(SCENARIOS)} emergencies, latency budget {LATENCY_BUDGET_MS}ms\n")
    print(f"  {'passes':>6} {'latency':>8} | {'fixed acc':>9}")
    for k in PASSES_GRID:
        print(f"  {k:>6} {latency_ms(k):>6}ms | {acc[k]:>9.3f}")
    print(f"\n  effort-manager: acc={ctrl_acc:.3f} at avg {ctrl_passes:.1f} passes "
          f"({round(ctrl_passes*PER_PASS_MS)}ms avg)")
    print(f"  fixed best ({PASSES_GRID[-1]} passes): acc={fixed_hi:.3f} at {latency_ms(PASSES_GRID[-1])}ms")
    if fixed_hi > 0:
        print(f"  -> {ctrl_acc/fixed_hi*100:.0f}% of best accuracy using "
              f"{ctrl_passes/PASSES_GRID[-1]*100:.0f}% of the compute, all under {LATENCY_BUDGET_MS}ms")

    data = {
        "project": "Lifeline",
        "tagline": "Hands-free emergency first-aid — instant on routine, thinks harder on hard cases, never speaks an unverified step.",
        "simulated": simulated,
        "backend": backend,
        "model": os.environ.get("LIFELINE_MODEL", backend),
        "latency_budget_ms": LATENCY_BUDGET_MS,
        "per_pass_ms": PER_PASS_MS,
        "passes_grid": PASSES_GRID,
        "fixed_acc": [acc[k] for k in PASSES_GRID],
        "controller": {"acc": ctrl_acc, "avg_passes": ctrl_passes, "avg_latency_ms": round(ctrl_passes * PER_PASS_MS)},
        "fixed_hi": {"passes": PASSES_GRID[-1], "acc": fixed_hi, "latency_ms": latency_ms(PASSES_GRID[-1])},
        "scenarios": per_scenario,
    }
    out = os.path.join(BASE, "dashboard_lifeline")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "results.json"), "w") as f:
        json.dump(data, f, indent=2)
    with open(os.path.join(out, "index.html"), "w") as f:
        f.write(build_html(data))
    print(f"\n  -> dashboard_lifeline/index.html"
          + ("   (SIMULATED — build/debug only; run --backend diffusion for the real number)" if simulated else "")
          + "\n")
    return data


def build_html(d):
    return _HTML.replace("/*__DATA__*/", json.dumps(d))


_HTML = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lifeline</title><style>
:root{--bg:#0b0f14;--panel:#13181f;--line:#222b36;--text:#e6edf3;--dim:#8b97a6;--green:#3fb950;--red:#f85149;--amber:#e3b341;--blue:#58a6ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:24px 20px 60px}h1{margin:0;font-size:26px}
.tag{color:var(--dim);margin-top:4px}.banner{margin:10px 0;padding:8px 12px;border-radius:8px;font-size:13px;font-weight:600}
.real{background:rgba(63,185,80,.13);color:var(--green);border:1px solid rgba(63,185,80,.4)}
.sim{background:rgba(248,81,73,.13);color:var(--red);border:1px solid rgba(248,81,73,.4)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin-top:16px}
.card h2{font-size:12px;text-transform:uppercase;letter-spacing:.6px;color:var(--dim);margin:0 0 12px}
.kpis{display:flex;gap:22px;flex-wrap:wrap}.kpi{flex:1;min-width:130px}.kpi .v{font-size:28px;font-weight:800}
.kpi .l{color:var(--dim);font-size:12px}.green{color:var(--green)}.amber{color:var(--amber)}.dimv{color:var(--dim)}
.grid{display:grid;grid-template-columns:1.1fr 1fr;gap:16px}@media(max-width:820px){.grid{grid-template-columns:1fr}}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
th{color:var(--dim);font-size:11px;text-transform:uppercase}
.pill{font-size:11px;padding:1px 7px;border-radius:6px}
.routine{background:rgba(63,185,80,.15);color:var(--green)}.moderate{background:rgba(227,179,65,.15);color:var(--amber)}.critical{background:rgba(248,81,73,.15);color:var(--red)}
.legend{display:flex;gap:16px;font-size:12px;margin-top:8px}.dot{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:5px}
</style></head><body><div class="wrap">
<h1>Lifeline <span class="dimv" style="font-size:15px">— emergency first-aid, fast & verified</span></h1>
<div class="tag" id="tag"></div>
<div id="banner"></div>
<div class="card"><h2>Headline</h2><div class="kpis">
<div class="kpi"><div class="v green" id="k-acc"></div><div class="l">effort-manager accuracy</div></div>
<div class="kpi"><div class="v" id="k-lat"></div><div class="l">avg response time (budget <span id="k-budget"></span>ms)</div></div>
<div class="kpi"><div class="v amber" id="k-save"></div><div class="l">of the compute vs always-think-hard</div></div>
<div class="kpi"><div class="v dimv" id="k-base"></div><div class="l">accuracy at 1 pass (fast & careless)</div></div>
</div></div>
<div class="grid">
<div class="card"><h2>Accuracy vs. refinement compute</h2><div id="chart"></div>
<div class="legend"><span><i class="dot" style="background:var(--blue)"></i>fixed passes</span>
<span><i class="dot" style="background:var(--amber)"></i>effort-manager (adaptive)</span></div></div>
<div class="card"><h2>Per-emergency: how hard it thought</h2><table><thead><tr><th>caller says</th><th>triage</th><th>time</th></tr></thead><tbody id="rows"></tbody></table></div>
</div></div>
<script>
const D=/*__DATA__*/;const $=i=>document.getElementById(i);
$('tag').textContent=D.tagline;
$('banner').className='banner '+(D.simulated?'sim':'real');
$('banner').textContent=D.simulated
 ?'⚠ SIMULATED generator (mock) — verifier is real, generator is not. Run --backend diffusion for the real number.'
 :'● REAL — backend='+D.backend+' · model='+D.model+' · verified against documented protocols';
$('k-acc').textContent=(D.controller.acc*100).toFixed(0)+'%';
$('k-lat').textContent=D.controller.avg_latency_ms+'ms';
$('k-budget').textContent=D.latency_budget_ms;
$('k-save').textContent=Math.round(D.controller.avg_passes/D.fixed_hi.passes*100)+'%';
$('k-base').textContent=(D.fixed_acc[0]*100).toFixed(0)+'%';
const W=460,H=280,P={l:42,r:16,t:14,b:34},ks=D.passes_grid,mx=Math.max(...ks);
const x=v=>P.l+(W-P.l-P.r)*(Math.log2(v)/Math.log2(mx)),y=v=>P.t+(H-P.t-P.b)*(1-v);
let g='';for(let t=0;t<=1.001;t+=.25){g+=`<line x1="${P.l}" y1="${y(t)}" x2="${W-P.r}" y2="${y(t)}" stroke="#222b36"/><text x="${P.l-8}" y="${y(t)+4}" fill="#8b97a6" font-size="10" text-anchor="end">${t*100|0}%</text>`;}
ks.forEach(k=>{g+=`<text x="${x(k)}" y="${H-P.b+16}" fill="#8b97a6" font-size="10" text-anchor="middle">${k}</text>`;});
g+=`<text x="${(P.l+W-P.r)/2}" y="${H-2}" fill="#8b97a6" font-size="11" text-anchor="middle">refinement passes (log)</text>`;
g+=`<polyline points="${ks.map((k,i)=>x(k)+','+y(D.fixed_acc[i])).join(' ')}" fill="none" stroke="#58a6ff" stroke-width="2.4"/>`;
ks.forEach((k,i)=>{g+=`<circle cx="${x(k)}" cy="${y(D.fixed_acc[i])}" r="2.6" fill="#58a6ff"/>`;});
const cx=x(Math.max(1,D.controller.avg_passes)),cy=y(D.controller.acc);
g+=`<circle cx="${cx}" cy="${cy}" r="6" fill="#e3b341"/><text x="${cx+9}" y="${cy+4}" fill="#e3b341" font-size="11">effort-mgr: ${(D.controller.acc*100).toFixed(0)}% @ ${D.controller.avg_passes.toFixed(1)} passes</text>`;
$('chart').innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%">${g}</svg>`;
$('rows').innerHTML=D.scenarios.map(r=>`<tr><td>"${r.say}"<div class="dimv" style="font-size:11px">${r.protocol}</div></td>`
 +`<td><span class="pill ${r.regime}">${r.regime}</span> ${r.passes}p</td><td>${r.latency_ms}ms · ${(r.acc*100).toFixed(0)}%</td></tr>`).join('');
</script></body></html>
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="mock", choices=["mock", "diffusion"])
    ap.add_argument("--resamples", type=int, default=200)
    a = ap.parse_args()
    run(backend=a.backend, resamples=a.resamples)
