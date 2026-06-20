"""
GreenWall end-to-end pipeline.

    python3 pipeline.py [--mode synthetic|replay] [--n 12]

Runs the swarm -> Diff Oracle -> selection -> bootstrap scaling curves, writes
dashboard/results.json and a self-contained dashboard/index.html you can open in a
browser (double-click; no server needed) and demo immediately.
"""
from __future__ import annotations
import argparse
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from tasks.orders_task import load_task, write_source_csv          # noqa: E402
from agents.orchestrator import DevinOrchestrator                  # noqa: E402
from agents.synthetic import ERROR_MODES                           # noqa: E402
from oracle.diff_oracle import check_invariants, oracle_pass, oracle_score, HARD_INVARIANTS  # noqa: E402
from oracle.metrics import true_accuracy, is_correct               # noqa: E402
from oracle.selection import SELECTORS, bootstrap_curve, find_knee  # noqa: E402

KS = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32]
ONE_PER_MODE_SEED = 7


def precompute(pool, task):
    for c in pool:
        c["_true_acc"] = round(true_accuracy(c, task), 4)
        c["_correct"] = is_correct(c, task)
        c["_oracle_pass"] = oracle_pass(c, task)
        c["_oracle_score"] = oracle_score(c, task)
    return pool


def archetypes(task):
    """One illustrative candidate per error mode, with full invariant breakdown."""
    from agents.synthetic import _apply
    out = []
    for mode, _, judge in ERROR_MODES:
        cand = _apply(mode, task)
        inv = check_invariants(cand, task)
        out.append({
            "error_mode": mode,
            "true_acc": round(true_accuracy(cand, task), 3),
            "judge_score": judge,
            "oracle_pass": oracle_pass(cand, task),
            "invariants": {k: {"pass": v["pass"], "detail": v["detail"]} for k, v in inv.items()},
        })
    return out


def run(mode="synthetic", n=12, replay_path=None):
    task = load_task()
    write_source_csv()

    orch = DevinOrchestrator(mode=mode, replay_path=replay_path)
    pool = precompute(orch.bank(task), task)

    curves = {name: bootstrap_curve(pool, sel, KS) for name, sel in SELECTORS.items()}
    knee = find_knee(curves["oracle"], KS)

    max_idx = KS.index(max(KS))
    headline = {
        "max_n": KS[-1],
        "oracle_max": curves["oracle"][max_idx],
        "judge_max": max(curves["llm_judge"]),
        "judge_end": curves["llm_judge"][max_idx],
        "single_shot": curves["single_shot"][0],
        "knee": knee,
    }

    data = {
        "project": "GreenWall",
        "tagline": "Verifier-gated Devin swarm — inference compute selected by math, not vibes.",
        "track": "Agents (Devin Teams)",
        "mode": mode,
        "task": {
            "name": task["name"],
            "n_source_rows": task["n_source_rows"],
            "n_source_orders": task["n_source_orders"],
            "n_distinct_customers": task["n_distinct_customers"],
            "source_revenue": task["source_revenue"],
        },
        "hard_invariants": HARD_INVARIANTS,
        "ks": KS,
        "curves": curves,
        "knee": knee,
        "headline": headline,
        "archetypes": archetypes(task),
    }

    out_dir = os.path.join(BASE, "dashboard")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "results.json"), "w") as f:
        json.dump(data, f, indent=2)
    with open(os.path.join(out_dir, "index.html"), "w") as f:
        f.write(build_html(data))

    _print_summary(data)
    return data


def _print_summary(d):
    print(f"\n  GreenWall pipeline  [mode={d['mode']}]")
    print(f"  task: {d['task']['n_source_rows']} messy rows -> "
          f"{d['task']['n_source_orders']} orders / {d['task']['n_distinct_customers']} customers / "
          f"${d['task']['source_revenue']:.2f}\n")
    print(f"  {'N':>4} | {'oracle':>7} {'judge':>7} {'major':>7} {'1-shot':>7}")
    for i, k in enumerate(d["ks"]):
        print(f"  {k:>4} | {d['curves']['oracle'][i]:>7.3f} {d['curves']['llm_judge'][i]:>7.3f} "
              f"{d['curves']['majority'][i]:>7.3f} {d['curves']['single_shot'][i]:>7.3f}")
    h = d["headline"]
    print(f"\n  oracle @N={h['max_n']}: {h['oracle_max']:.3f}   "
          f"single-shot: {h['single_shot']:.3f}   "
          f"llm-judge peak->end: {h['judge_max']:.3f}->{h['judge_end']:.3f}")
    print(f"  knee (diminishing returns) at N={h['knee']}")
    print(f"\n  -> open dashboard/index.html\n")


# --------------------------------------------------------------------------------------
# Self-contained dashboard (data inlined; no server, no CDN).
# --------------------------------------------------------------------------------------
def build_html(data: dict) -> str:
    payload = json.dumps(data)
    return _HTML.replace("/*__DATA__*/", payload)


_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GreenWall</title>
<style>
:root{--bg:#0d1117;--panel:#161b22;--line:#21262d;--text:#c9d1d9;--dim:#8b949e;
--green:#3fb950;--red:#f85149;--orange:#d29922;--blue:#58a6ff;--purple:#bc8cff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:14px/1.5 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:28px 22px 60px}
h1{font-size:26px;margin:0;letter-spacing:-.4px}
.tag{color:var(--dim);margin:4px 0 2px}.pill{display:inline-block;background:var(--panel);
border:1px solid var(--line);border-radius:999px;padding:3px 11px;font-size:12px;color:var(--blue)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:22px}
@media(max-width:820px){.grid{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}
.card h2{font-size:13px;text-transform:uppercase;letter-spacing:.6px;color:var(--dim);margin:0 0 12px}
.kpis{display:flex;gap:20px;flex-wrap:wrap}
.kpi{flex:1;min-width:120px}.kpi .v{font-size:30px;font-weight:700;letter-spacing:-1px}
.kpi .l{color:var(--dim);font-size:12px}
.v.green{color:var(--green)}.v.red{color:var(--red)}.v.orange{color:var(--orange)}
.slider{width:100%;margin:8px 0 4px;accent-color:var(--green)}
.readout{font-size:13px;color:var(--dim);margin-top:6px}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:12px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.dot{width:10px;height:10px;border-radius:3px;display:inline-block}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line)}
th{color:var(--dim);font-weight:600;font-size:11px;text-transform:uppercase}
.badge{font-size:11px;padding:1px 7px;border-radius:6px;font-weight:600}
.ok{background:rgba(63,185,80,.15);color:var(--green)}
.bad{background:rgba(248,81,73,.15);color:var(--red)}
.mode{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--purple)}
.call{margin-top:14px;padding:12px 14px;border-radius:10px;border:1px solid var(--line);
background:#0b0f14;font-size:13px}.call b{color:var(--text)}
.win{color:var(--green)}.lose{color:var(--red)}
footer{color:var(--dim);font-size:12px;margin-top:26px;text-align:center}
</style></head><body><div class="wrap">

<div class="pill" id="track"></div>
<h1 id="title"></h1>
<div class="tag" id="tagline"></div>

<div class="card" style="margin-top:18px">
  <h2>Headline</h2>
  <div class="kpis">
    <div class="kpi"><div class="v green" id="k-oracle"></div><div class="l">oracle accuracy @ N=<span id="k-maxn"></span></div></div>
    <div class="kpi"><div class="v" id="k-single"></div><div class="l">single-shot baseline</div></div>
    <div class="kpi"><div class="v red" id="k-judge"></div><div class="l">LLM-judge @ N=<span id="k-maxn2"></span> (peaked then fell)</div></div>
    <div class="kpi"><div class="v orange" id="k-knee"></div><div class="l">knee: more compute stops paying</div></div>
  </div>
</div>

<div class="grid">
  <div class="card">
    <h2>Accuracy vs. inference compute (N trajectories)</h2>
    <div id="chart"></div>
    <div class="legend">
      <span><i class="dot" style="background:var(--green)"></i>oracle (grounded)</span>
      <span><i class="dot" style="background:var(--red)"></i>llm-judge</span>
      <span><i class="dot" style="background:var(--blue)"></i>majority</span>
      <span><i class="dot" style="background:var(--dim)"></i>single-shot</span>
    </div>
    <input type="range" min="0" class="slider" id="slider">
    <div class="readout" id="readout"></div>
    <div class="call" id="callout"></div>
  </div>

  <div class="card">
    <h2>What the swarm produces &mdash; and what the oracle catches</h2>
    <table><thead><tr><th>agent output</th><th>oracle</th><th>true</th><th>judge</th></tr></thead>
    <tbody id="rows"></tbody></table>
    <div class="call" id="invdetail"></div>
  </div>
</div>

<footer id="foot"></footer>
</div>
<script>
const DATA = /*__DATA__*/;
const C = {oracle:'#3fb950',llm_judge:'#f85149',majority:'#58a6ff',single_shot:'#8b949e'};
const $ = id => document.getElementById(id);

$('track').textContent = DATA.track + '  ·  ' + DATA.mode + ' mode';
$('title').textContent = DATA.project;
$('tagline').textContent = DATA.tagline;
$('k-oracle').textContent = (DATA.headline.oracle_max*100).toFixed(0)+'%';
$('k-single').textContent = (DATA.headline.single_shot*100).toFixed(0)+'%';
$('k-judge').textContent = (DATA.headline.judge_end*100).toFixed(0)+'%';
$('k-knee').textContent = 'N='+DATA.knee;
$('k-maxn').textContent = DATA.headline.max_n;
$('k-maxn2').textContent = DATA.headline.max_n;
$('foot').textContent = DATA.task.n_source_rows+' messy rows → '+DATA.task.n_source_orders
  +' orders / '+DATA.task.n_distinct_customers+' customers / $'+DATA.task.source_revenue.toFixed(2)
  +'  ·  one frozen model, all gains are inference compute.';

// ---- chart ----
const W=480,H=300,P={l:42,r:14,t:14,b:30};
const ks=DATA.ks, n=ks.length;
const x=i=>P.l+(W-P.l-P.r)*(i/(n-1));
const y=v=>P.t+(H-P.t-P.b)*(1-v);
function poly(key){return ks.map((k,i)=>x(i)+','+y(DATA.curves[key][i])).join(' ');}
function dots(key){return ks.map((k,i)=>`<circle cx="${x(i)}" cy="${y(DATA.curves[key][i])}" r="2.5" fill="${C[key]}"/>`).join('');}
let marker=DATA.ks.indexOf(DATA.knee); if(marker<0)marker=n-1;
function grid(){let g='';for(let t=0;t<=1.0001;t+=0.25){g+=`<line x1="${P.l}" y1="${y(t)}" x2="${W-P.r}" y2="${y(t)}" stroke="#21262d"/>`
  +`<text x="${P.l-8}" y="${y(t)+4}" fill="#8b949e" font-size="10" text-anchor="end">${(t*100)|0}%</text>`;}
  ks.forEach((k,i)=>{g+=`<text x="${x(i)}" y="${H-P.b+16}" fill="#8b949e" font-size="10" text-anchor="middle">${k}</text>`;});
  g+=`<text x="${(P.l+W-P.r)/2}" y="${H-2}" fill="#8b949e" font-size="11" text-anchor="middle">N = parallel trajectories (Devin agents)</text>`;
  return g;}
function draw(){
  const mx=x(marker);
  $('chart').innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%">${grid()}
    <line x1="${mx}" y1="${P.t}" x2="${mx}" y2="${H-P.b}" stroke="#30363d" stroke-dasharray="4 3"/>
    ${['single_shot','majority','llm_judge','oracle'].map(key=>
      `<polyline points="${poly(key)}" fill="none" stroke="${C[key]}" stroke-width="2.2"/>${dots(key)}`).join('')}
  </svg>`;
  const k=ks[marker];
  const o=DATA.curves.oracle[marker], j=DATA.curves.llm_judge[marker], s=DATA.curves.single_shot[marker];
  $('readout').innerHTML=`At <b>N=${k}</b>: oracle <b class="win">${(o*100).toFixed(0)}%</b> &nbsp;·&nbsp; `
    +`llm-judge <b class="lose">${(j*100).toFixed(0)}%</b> &nbsp;·&nbsp; single-shot ${(s*100).toFixed(0)}%`;
  const lead=((o-j)*100).toFixed(0);
  $('callout').innerHTML = j<o
    ? `<b>The contrast:</b> with ${k} trajectories the grounded oracle is <b class="win">${lead} pts</b> ahead of the LLM-judge. `
      +`More compute makes the judge <b class="lose">worse</b> (it keeps picking the clean-but-revenue-wrong migration); `
      +`the oracle keeps climbing because correctness is conservation math, not opinion.`
    : `<b>Early N:</b> too few samples to separate selectors — drag right to watch them diverge.`;
}
const sl=$('slider'); sl.max=n-1; sl.value=marker;
sl.addEventListener('input',e=>{marker=+e.target.value;draw();});
draw();

// ---- archetype rows ----
const LABEL={correct:'clean migration',clean_wrong:'clean but revenue $298 (cents truncated)',
row_drop:'dropped an order',fk_violation:'null customer_id',bad_dedup:'duplicate customer',
subtle_wrong:'product labels swapped'};
$('rows').innerHTML = DATA.archetypes.map((a,i)=>`<tr data-i="${i}">
  <td>${LABEL[a.error_mode]||a.error_mode}<div class="mode">${a.error_mode}</div></td>
  <td><span class="badge ${a.oracle_pass?'ok':'bad'}">${a.oracle_pass?'PASS':'FAIL'}</span></td>
  <td>${(a.true_acc*100).toFixed(0)}%</td>
  <td>${(a.judge_score*100).toFixed(0)}%</td></tr>`).join('');

function showInv(i){
  const a=DATA.archetypes[i];
  const inv=Object.entries(a.invariants).map(([k,v])=>
    `<span class="badge ${v.pass?'ok':'bad'}">${v.pass?'✓':'✗'} ${k}</span>`).join(' ');
  const note = (!a.oracle_pass && a.judge_score>0.9)
    ? `<br><br><b class="lose">This is the trap:</b> the LLM-judge scores it ${(a.judge_score*100).toFixed(0)}% (looks immaculate) `
      +`but the revenue invariant fails — a wrong number that would silently corrupt a decision.`
    : (a.oracle_pass && a.true_acc<1
       ? `<br><br><b class="orange">Honest ceiling:</b> passes every invariant yet isn't perfect — the oracle needs a stronger invariant to catch this. Worth saying on stage.`
       : '');
  $('invdetail').innerHTML=`<b>${LABEL[a.error_mode]||a.error_mode}</b> &mdash; invariants:<br>${inv}${note}`;
}
document.querySelectorAll('#rows tr').forEach(tr=>{
  tr.style.cursor='pointer';
  tr.onclick=()=>showInv(+tr.dataset.i);
});
// default: show the judge-bait row
showInv(DATA.archetypes.findIndex(a=>a.error_mode==='clean_wrong'));
</script></body></html>
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="synthetic", choices=["synthetic", "replay", "live"])
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--replay-path", default=None)
    a = ap.parse_args()
    run(mode=a.mode, n=a.n, replay_path=a.replay_path)
