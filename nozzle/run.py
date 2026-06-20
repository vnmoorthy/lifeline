"""
Nozzle end-to-end run -> REAL measured accuracy-vs-compute curve + controller savings.

    python3 -m nozzle.run --backend vllm        # the real demo (point VLLM_BASE_URL at Lambda)
    python3 -m nozzle.run --backend anthropic    # Claude generator (low volume)
    python3 -m nozzle.run --backend smoke        # OFFLINE plumbing test only -> SIMULATED, do NOT demo

Generates N candidates per question with a real model, EXECUTES each against the database
(the oracle), scores correctness vs gold, and computes:
  * accuracy vs N for execution-consensus selection (the hero curve)
  * single-shot baseline (flat)
  * the controller: per-question adaptive N -> near-max accuracy at a fraction of the samples
Every number comes from real model output unless backend=smoke (stamped SIMULATED).
"""
from __future__ import annotations
import argparse
import json
import os
import random
import statistics

from nozzle.db import build_db, load_questions, DB_PATH
from nozzle.generate import generate
from nozzle.verifier import execute_candidate, is_correct, consensus_select, agreement
from nozzle.controller import decide_n, PROBE_K, N_HARD

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KS = [1, 2, 4, 8, 16, 32]
DISPLAY_N = {"easy": 6, "medium": 12, "hard": 24}


def preview(rows, error) -> str:
    if error:
        return "error"
    if not rows:
        return "(empty)"
    if len(rows) == 1 and len(rows[0]) == 1:
        v = rows[0][0]
        return f"{v:.2f}" if isinstance(v, float) else str(v)
    if len(rows) == 1:
        return ", ".join(str(c) for c in rows[0])
    return f"{len(rows)} rows"


def build_pool(questions, backend, nmax, temperature):
    """Generate + execute nmax candidates per question. Returns {qid: [executed,...]}."""
    pool = {}
    for q in questions:
        sqls = generate(q, nmax, backend=backend, temperature=temperature)
        ex = []
        for sql in sqls:
            e = execute_candidate(DB_PATH, sql)
            e["correct"] = is_correct(e["sig"], q["gold_rows"])
            ex.append(e)
        pool[q["id"]] = ex
        ok = sum(e["correct"] for e in ex)
        print(f"  {q['id']:4} [{q['difficulty']:6}] {ok:2}/{len(ex)} candidates correct  | {q['q']}")
    return pool


def curve(pool, questions, resamples, seed=5):
    rng = random.Random(seed)
    consensus = {}
    for k in KS:
        per_q = []
        for q in questions:
            cands = pool[q["id"]]
            if not cands:
                continue
            hits = []
            for _ in range(resamples):
                sub = rng.sample(cands, min(k, len(cands)))
                sel = consensus_select(sub)
                hits.append(1.0 if (sel and sel["correct"]) else 0.0)
            per_q.append(statistics.mean(hits))
        consensus[k] = round(statistics.mean(per_q), 4)
    single = round(statistics.mean(
        statistics.mean([1.0 if e["correct"] else 0.0 for e in pool[q["id"]]])
        for q in questions if pool[q["id"]]), 4)
    return consensus, single


def run_controller(pool, questions, resamples, seed=9):
    rng = random.Random(seed)
    accs, samples, per_q = [], [], []
    for q in questions:
        cands = pool[q["id"]]
        if not cands:
            continue
        hit, used, regimes = [], [], []
        for _ in range(resamples):
            probe = rng.sample(cands, min(PROBE_K, len(cands)))
            ag = agreement(probe)
            n, regime = decide_n(ag)
            sub = rng.sample(cands, min(n, len(cands)))
            sel = consensus_select(sub)
            hit.append(1.0 if (sel and sel["correct"]) else 0.0)
            used.append(min(n, len(cands)))
            regimes.append(regime)
        accs.append(statistics.mean(hit))
        samples.append(statistics.mean(used))
        per_q.append({"id": q["id"], "q": q["q"], "difficulty": q["difficulty"],
                      "regime": max(set(regimes), key=regimes.count),
                      "avg_n": round(statistics.mean(used), 1),
                      "acc": round(statistics.mean(hit), 3)})
    return round(statistics.mean(accs), 4), round(statistics.mean(samples), 2), per_q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="vllm", choices=["vllm", "anthropic", "smoke"])
    ap.add_argument("--nmax", type=int, default=32)
    ap.add_argument("--resamples", type=int, default=200)
    ap.add_argument("--temperature", type=float, default=0.7)
    a = ap.parse_args()

    simulated = a.backend == "smoke"
    build_db()
    questions = load_questions()
    print(f"\nNozzle run  [backend={a.backend}{'  *** SIMULATED ***' if simulated else ''}]  "
          f"{len(questions)} questions, nmax={a.nmax}\n")
    pool = build_pool(questions, a.backend, a.nmax, a.temperature)

    consensus, single = curve(pool, questions, a.resamples)
    ctrl_acc, ctrl_samples, per_q = run_controller(pool, questions, a.resamples)
    total_samples = sum(len(pool[q["id"]]) for q in questions)

    stage = []
    for q in questions:
        cands = pool[q["id"]]
        shown = cands[:DISPLAY_N.get(q["difficulty"], 12)]
        base = cands[0]
        con = consensus_select(cands)
        stage.append({
            "id": q["id"], "q": q["q"], "difficulty": q["difficulty"],
            "gold": preview(q["gold_rows"], None),
            "n_total": len(cands),
            "baseline": {"preview": preview(base["rows"], base["error"]), "correct": base["correct"]},
            "consensus": {"preview": preview(con["rows"], None) if con else "(no valid answer)",
                          "correct": bool(con and con["correct"])},
            "candidates": [{"ok": e["error"] is None, "correct": e["correct"],
                            "preview": preview(e["rows"], e["error"])} for e in shown],
        })

    fixed_hard_acc = consensus[max(k for k in KS if k <= N_HARD)]
    print(f"\n  {'N':>4} | consensus  single-shot")
    for k in KS:
        print(f"  {k:>4} | {consensus[k]:>9.3f}  {single:>10.3f}")
    print(f"\n  controller: acc={ctrl_acc:.3f} at avg {ctrl_samples:.1f} samples/question")
    print(f"  fixed best-of-{N_HARD}: acc={fixed_hard_acc:.3f} at {float(N_HARD):.1f} samples/question")
    if ctrl_samples > 0:
        print(f"  -> controller reaches {ctrl_acc/max(fixed_hard_acc,1e-9)*100:.0f}% of max accuracy "
              f"using {ctrl_samples/N_HARD*100:.0f}% of the compute")

    data = {
        "project": "Nozzle",
        "simulated": simulated,
        "backend": a.backend,
        "model": os.environ.get("VLLM_MODEL" if a.backend == "vllm" else "ANTHROPIC_MODEL", a.backend),
        "n_questions": len(questions),
        "total_samples": total_samples,
        "ks": KS,
        "consensus": [consensus[k] for k in KS],
        "single_shot": single,
        "controller": {"acc": ctrl_acc, "avg_samples": ctrl_samples},
        "fixed_hard": {"n": N_HARD, "acc": fixed_hard_acc},
        "per_question": per_q,
        "stage": stage,
    }
    out = os.path.join(BASE, "dashboard_nozzle")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "results.json"), "w") as f:
        json.dump(data, f, indent=2)
    with open(os.path.join(out, "index.html"), "w") as f:
        f.write(build_html(data))
    with open(os.path.join(out, "stage.html"), "w") as f:
        f.write(build_stage(data))
    tail = "   (SIMULATED — plumbing only, do NOT demo these numbers)" if simulated else ""
    print(f"\n  -> dashboard_nozzle/stage.html  (the live demo){tail}")
    print(f"  -> dashboard_nozzle/index.html  (the analysis){tail}\n")


def build_html(d):
    return _HTML.replace("/*__DATA__*/", json.dumps(d))


_HTML = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nozzle</title><style>
:root{--bg:#0d1117;--panel:#161b22;--line:#21262d;--text:#c9d1d9;--dim:#8b949e;--green:#3fb950;--blue:#58a6ff;--amber:#d29922;--red:#f85149;--purple:#bc8cff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:26px 20px 60px}h1{margin:0;font-size:26px}
.tag{color:var(--dim)}.banner{margin:10px 0;padding:8px 12px;border-radius:8px;font-size:13px;font-weight:600}
.real{background:rgba(63,185,80,.15);color:var(--green);border:1px solid rgba(63,185,80,.4)}
.sim{background:rgba(248,81,73,.15);color:var(--red);border:1px solid rgba(248,81,73,.4)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin-top:16px}
.card h2{font-size:12px;text-transform:uppercase;letter-spacing:.6px;color:var(--dim);margin:0 0 12px}
.kpis{display:flex;gap:22px;flex-wrap:wrap}.kpi{flex:1;min-width:130px}.kpi .v{font-size:28px;font-weight:700}
.kpi .l{color:var(--dim);font-size:12px}.green{color:var(--green)}.amber{color:var(--amber)}.dimv{color:var(--dim)}
.grid{display:grid;grid-template-columns:1.2fr 1fr;gap:16px}@media(max-width:820px){.grid{grid-template-columns:1fr}}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
th{color:var(--dim);font-size:11px;text-transform:uppercase}.pill{font-size:11px;padding:1px 7px;border-radius:6px}
.easy{background:rgba(63,185,80,.15);color:var(--green)}.medium{background:rgba(210,153,34,.15);color:var(--amber)}.hard{background:rgba(248,81,73,.15);color:var(--red)}
.legend{display:flex;gap:16px;font-size:12px;margin-top:8px}.dot{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:5px}
</style></head><body><div class="wrap">
<h1>Nozzle</h1><div class="tag">Provably-right answers — compute aimed by the controller, verified by the database.</div>
<div id="banner"></div>
<div class="card"><h2>Headline</h2><div class="kpis">
<div class="kpi"><div class="v green" id="k-con"></div><div class="l">consensus accuracy @ N=<span id="k-max"></span></div></div>
<div class="kpi"><div class="v dimv" id="k-single"></div><div class="l">single-shot baseline</div></div>
<div class="kpi"><div class="v amber" id="k-ctrl"></div><div class="l">controller accuracy</div></div>
<div class="kpi"><div class="v" id="k-save"></div><div class="l">of the compute (controller vs fixed best-of-N)</div></div>
</div></div>
<div class="grid">
<div class="card"><h2>Accuracy vs. compute (measured)</h2><div id="chart"></div>
<div class="legend"><span><i class="dot" style="background:var(--green)"></i>execution-consensus</span>
<span><i class="dot" style="background:var(--dim)"></i>single-shot</span>
<span><i class="dot" style="background:var(--amber)"></i>controller (adaptive)</span></div></div>
<div class="card"><h2>Per-question allocation</h2><table><thead><tr><th>question</th><th>true</th><th>controller</th></tr></thead><tbody id="rows"></tbody></table></div>
</div></div>
<script>
const D=/*__DATA__*/;const $=i=>document.getElementById(i);
$('banner').className='banner '+(D.simulated?'sim':'real');
$('banner').textContent=D.simulated
 ?'⚠ SIMULATED (backend=smoke) — plumbing only. Do NOT present these numbers. Run with --backend vllm for real results.'
 :'● REAL RUN — backend='+D.backend+' · model='+D.model+' · '+D.n_questions+' questions · '+D.total_samples+' executed candidates';
const mx=Math.max(...D.ks);
$('k-con').textContent=(D.consensus[D.ks.length-1]*100).toFixed(0)+'%';
$('k-max').textContent=mx;$('k-single').textContent=(D.single_shot*100).toFixed(0)+'%';
$('k-ctrl').textContent=(D.controller.acc*100).toFixed(0)+'%';
$('k-save').textContent=Math.round(D.controller.avg_samples/D.fixed_hard.n*100)+'%';
const W=460,H=280,P={l:42,r:16,t:14,b:34};const ks=D.ks,n=ks.length;
const x=v=>P.l+(W-P.l-P.r)*(Math.log2(v)/Math.log2(mx));
const y=v=>P.t+(H-P.t-P.b)*(1-v);
let g='';for(let t=0;t<=1.001;t+=.25){g+=`<line x1="${P.l}" y1="${y(t)}" x2="${W-P.r}" y2="${y(t)}" stroke="#21262d"/><text x="${P.l-8}" y="${y(t)+4}" fill="#8b949e" font-size="10" text-anchor="end">${t*100|0}%</text>`;}
ks.forEach(k=>{g+=`<text x="${x(k)}" y="${H-P.b+16}" fill="#8b949e" font-size="10" text-anchor="middle">${k}</text>`;});
g+=`<text x="${(P.l+W-P.r)/2}" y="${H-2}" fill="#8b949e" font-size="11" text-anchor="middle">N candidates (log scale)</text>`;
g+=`<polyline points="${ks.map(k=>x(k)+','+y(D.single_shot)).join(' ')}" fill="none" stroke="#8b949e" stroke-width="2" stroke-dasharray="4 3"/>`;
g+=`<polyline points="${ks.map((k,i)=>x(k)+','+y(D.consensus[i])).join(' ')}" fill="none" stroke="#3fb950" stroke-width="2.4"/>`;
ks.forEach((k,i)=>{g+=`<circle cx="${x(k)}" cy="${y(D.consensus[i])}" r="2.6" fill="#3fb950"/>`;});
const cx=x(Math.max(1,D.controller.avg_samples)),cy=y(D.controller.acc);
g+=`<circle cx="${cx}" cy="${cy}" r="6" fill="#d29922"/><text x="${cx+9}" y="${cy+4}" fill="#d29922" font-size="11">controller: ${(D.controller.acc*100).toFixed(0)}% @ ${D.controller.avg_samples.toFixed(1)} avg</text>`;
$('chart').innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%">${g}</svg>`;
$('rows').innerHTML=D.per_question.map(r=>`<tr><td>${r.q}</td><td><span class="pill ${r.difficulty}">${r.difficulty}</span></td><td>N=${r.avg_n} · ${(r.acc*100).toFixed(0)}%</td></tr>`).join('');
</script></body></html>
"""


def build_stage(d):
    return _STAGE_HTML.replace("/*__DATA__*/", json.dumps(d))


_STAGE_HTML = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nozzle — live</title><style>
:root{--bg:#0b0f14;--panel:#161b22;--line:#21262d;--text:#e6edf3;--dim:#8b949e;--green:#3fb950;--red:#f85149;--amber:#d29922;--blue:#58a6ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:22px 20px 60px}h1{margin:0;font-size:24px}
.tag{color:var(--dim);margin-bottom:8px}.banner{margin:8px 0;padding:7px 12px;border-radius:8px;font-size:13px;font-weight:600}
.real{background:rgba(63,185,80,.13);color:var(--green);border:1px solid rgba(63,185,80,.4)}
.sim{background:rgba(248,81,73,.13);color:var(--red);border:1px solid rgba(248,81,73,.4)}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
.chip{cursor:pointer;border:1px solid var(--line);background:var(--panel);border-radius:999px;padding:6px 13px;font-size:13px;color:var(--text)}
.chip:hover{border-color:var(--blue)}.chip .d{font-size:11px;color:var(--dim);margin-left:6px}
.ask{font-size:20px;margin:6px 0 16px}.ask b{color:var(--blue)}
.cols{display:grid;grid-template-columns:1fr 1.4fr;gap:16px}@media(max-width:760px){.cols{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;min-height:240px}
.card h2{font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--dim);margin:0 0 12px}
.one{width:30px;height:30px;border-radius:6px;background:#30363d;display:inline-block}
.ans{font-size:30px;font-weight:800;margin-top:14px;min-height:38px}
.ans.good{color:var(--green)}.ans.bad{color:var(--red)}
.sub{color:var(--dim);font-size:13px;margin-top:4px;min-height:18px}
.grid{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:6px}
.cell{width:16px;height:16px;border-radius:4px;background:#30363d;transform:scale(.2);opacity:0;transition:all .25s}
.cell.in{transform:scale(1);opacity:1}
.cell.correct{background:var(--green)}.cell.wrong{background:var(--amber)}.cell.err{background:var(--red)}
.cnt{font-size:13px;color:var(--dim);min-height:18px}
.bar{margin-top:16px;padding:12px 14px;border-radius:10px;border:1px solid var(--line);background:#0b0f14;font-size:14px;min-height:20px}
.btn{cursor:pointer;border:0;border-radius:8px;padding:9px 16px;font-weight:700;background:var(--green);color:#04210e;margin-top:8px}
.muted{color:var(--dim)}
</style></head><body><div class="wrap">
<h1>Nozzle <span class="muted" style="font-size:15px">— ask your data, trust the answer</span></h1>
<div class="tag">Easy question → 1 try. Hard question → many tries, verified against the database. More compute, aimed where it matters.</div>
<div id="banner"></div>
<div class="chips" id="chips"></div>
<div class="ask" id="ask"></div>
<div class="cols">
  <div class="card"><h2>Plain AI · 1 answer</h2>
    <div id="one"><span class="one"></span></div>
    <div class="ans" id="oneAns"></div><div class="sub" id="oneSub"></div>
  </div>
  <div class="card"><h2>Nozzle · verified swarm</h2>
    <div class="grid" id="grid"></div><div class="cnt" id="cnt"></div>
    <div class="ans" id="swAns"></div><div class="sub" id="swSub"></div>
  </div>
</div>
<div class="bar" id="bar"></div>
<button class="btn" id="run">▶ Run again</button>
</div>
<script>
const D=/*__DATA__*/;const $=i=>document.getElementById(i);
$('banner').className='banner '+(D.simulated?'sim':'real');
$('banner').textContent=D.simulated
 ?'⚠ SIMULATED candidates (backend=smoke) — pipeline demo only. Run with --backend vllm for real model output.'
 :'● REAL — backend='+D.backend+' · model='+D.model+' · candidates executed against a live database';
let cur=D.stage.find(s=>s.difficulty==='hard')||D.stage[0];
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
$('chips').innerHTML=D.stage.map((s,i)=>`<span class="chip" data-i="${i}">${s.q}<span class="d">${s.difficulty}</span></span>`).join('');
document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{cur=D.stage[+c.dataset.i];play();});
$('run').onclick=play;

async function play(){
  $('ask').innerHTML='“ <b>'+cur.q+'</b> ”';
  // reset
  $('oneAns').textContent='';$('oneAns').className='ans';$('oneSub').textContent='';
  $('grid').innerHTML='';$('cnt').textContent='';$('swAns').textContent='';$('swAns').className='ans';$('swSub').textContent='';
  $('bar').textContent='';
  // plain AI: one shot
  await sleep(500);
  const b=cur.baseline;
  $('oneAns').textContent=b.preview;$('oneAns').className='ans '+(b.correct?'good':'bad');
  $('oneSub').textContent=b.correct?'happened to be right':'confident… and wrong';
  // nozzle: swarm
  const cs=cur.candidates;
  for(let i=0;i<cs.length;i++){
    const el=document.createElement('div');el.className='cell';$('grid').appendChild(el);
    requestAnimationFrame(()=>el.classList.add('in'));
    await sleep(35);
  }
  $('cnt').textContent=cs.length+' attempts generated (controller chose this many for a '+cur.difficulty+' question)';
  await sleep(300);
  const cells=[...document.querySelectorAll('#grid .cell')];
  for(let i=0;i<cs.length;i++){
    const c=cs[i];cells[i].classList.add(c.correct?'correct':(c.ok?'wrong':'err'));
    await sleep(45);
  }
  const ok=cs.filter(c=>c.ok).length,agree=cs.filter(c=>c.correct).length;
  await sleep(250);
  $('swAns').textContent=cur.consensus.preview;$('swAns').className='ans '+(cur.consensus.correct?'good':'bad');
  $('swSub').textContent=agree+' of '+ok+' valid answers agree → verified by execution on the database';
  await sleep(300);
  $('bar').innerHTML='✅ Truth (gold): <b>'+cur.gold+'</b> &nbsp;—&nbsp; '
    +(b.correct?'plain AI right':'<span style="color:var(--red)">plain AI was WRONG</span>')
    +', <span style="color:var(--green)">Nozzle verified correct</span>.';
}
play();
</script></body></html>
"""


if __name__ == "__main__":
    main()
