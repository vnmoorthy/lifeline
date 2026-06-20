"""The polished Lifeline UI (single source of truth, no deps). Used by the real product
(diffusion_server) and the local preview (mock_ui). Talks to POST /ask."""

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Lifeline — verified first aid</title><style>
:root{
 --bg:#0a0e13;--bg2:#0e141c;--panel:#141b24;--line:#222d3a;--text:#eef3f8;--dim:#8a98a8;
 --red:#ff4d4d;--red2:#c81e1e;--green:#39d353;--amber:#e3b341;--accent:#4da3ff;
 --shadow:0 8px 30px rgba(0,0,0,.45);
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;background:radial-gradient(1200px 600px at 50% -10%,#11202f 0,var(--bg) 60%);color:var(--text);
 font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;min-height:100%}
.wrap{max-width:560px;margin:0 auto;padding:22px 18px 48px}
.top{display:flex;align-items:center;gap:10px;justify-content:center;margin-bottom:2px}
.logo{font-size:22px;font-weight:800;letter-spacing:-.3px}
.logo b{color:var(--red)}
.sub{text-align:center;color:var(--dim);font-size:13.5px;margin-bottom:22px}
.mic-wrap{display:flex;flex-direction:column;align-items:center;gap:14px}
.mic{width:128px;height:128px;border-radius:50%;border:0;cursor:pointer;color:#fff;font-size:15px;font-weight:700;
 background:radial-gradient(circle at 50% 35%,var(--red),var(--red2));box-shadow:var(--shadow),0 0 0 0 rgba(255,77,77,.5);
 display:flex;align-items:center;justify-content:center;flex-direction:column;gap:6px;transition:transform .1s}
.mic:active{transform:scale(.96)}
.mic .ico{font-size:34px}
.mic.listening{animation:pulse 1.3s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(255,77,77,.55)}70%{box-shadow:0 0 0 26px rgba(255,77,77,0)}100%{box-shadow:0 0 0 0 rgba(255,77,77,0)}}
.or{color:var(--dim);font-size:12px;letter-spacing:.5px}
.row{display:flex;gap:8px;width:100%;max-width:420px}
input{flex:1;padding:13px 14px;border-radius:12px;border:1px solid var(--line);background:#0b1118;color:var(--text);font-size:15px}
input:focus{outline:none;border-color:var(--accent)}
.send{border:0;border-radius:12px;padding:0 18px;font-weight:700;background:#1c2734;color:var(--text);cursor:pointer}
.chips{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-top:14px}
.chip{font-size:12.5px;color:var(--dim);background:#10171f;border:1px solid var(--line);border-radius:999px;padding:6px 12px;cursor:pointer}
.chip:hover{border-color:var(--accent);color:var(--text)}
.you{margin:22px 0 6px;font-size:18px;text-align:center}.you b{color:#fff}
.stage{display:none}
.statusbar{display:flex;gap:8px;align-items:center;justify-content:center;flex-wrap:wrap;margin:10px 0}
.pill{font-size:12.5px;padding:4px 11px;border-radius:999px;border:1px solid var(--line);background:#10171f;color:var(--dim)}
.pill.proto{color:#fff;border-color:#2b3a4b}
.pill.routine{color:var(--green);border-color:rgba(57,211,83,.35)}
.pill.moderate{color:var(--amber);border-color:rgba(227,179,65,.35)}
.pill.critical{color:var(--red);border-color:rgba(255,77,77,.4)}
.pill.verified{background:rgba(57,211,83,.12);color:var(--green);border-color:rgba(57,211,83,.4)}
.pill.fallback{background:rgba(227,179,65,.12);color:var(--amber);border-color:rgba(227,179,65,.4)}
.engine{background:linear-gradient(180deg,#101822,#0d141c);border:1px solid var(--line);border-radius:16px;padding:14px 16px;margin-top:6px}
.engine .lbl{font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:.6px;display:flex;justify-content:space-between}
.dots{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0 2px}
.dot{width:16px;height:16px;border-radius:5px;background:#1d2a38;opacity:.25;transform:scale(.6);transition:.25s}
.dot.in{opacity:1;transform:scale(1)}
.dot.ok{background:var(--green)}.dot.bad{background:var(--red2)}
.shim{height:3px;border-radius:2px;margin-top:8px;background:linear-gradient(90deg,#1d2a38,#2b6cb0,#1d2a38);background-size:200% 100%;animation:sh 1.1s linear infinite;opacity:0}
.shim.on{opacity:1}@keyframes sh{0%{background-position:200% 0}100%{background-position:-200% 0}}
.steps{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:6px 8px 10px;margin-top:12px;box-shadow:var(--shadow)}
.steps .h{display:flex;align-items:center;gap:8px;padding:12px 12px 6px;color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.6px}
.step{display:flex;gap:12px;align-items:flex-start;padding:11px 12px;border-top:1px solid var(--line);opacity:0;transform:translateY(8px);transition:.35s}
.step.in{opacity:1;transform:none}
.step:first-of-type{border-top:0}
.num{flex:0 0 26px;height:26px;border-radius:50%;background:#192633;color:var(--accent);font-weight:800;display:flex;align-items:center;justify-content:center;font-size:14px}
.step .txt{font-size:17px;line-height:1.45;padding-top:1px}
.call{margin-top:14px;text-align:center;background:rgba(255,77,77,.1);border:1px solid rgba(255,77,77,.35);color:#ffb3b3;
 border-radius:12px;padding:10px;font-weight:700;font-size:14px}
.foot{margin-top:22px;text-align:center;color:var(--dim);font-size:12px;line-height:1.6}
.foot b{color:#aeb9c6;font-weight:600}
</style></head><body><div class="wrap">
<div class="top"><div class="logo"><b>✚</b> Lifeline</div></div>
<div class="sub">Hands-free first aid — verified against official protocols, on-device DiffusionGemma.</div>

<div class="mic-wrap">
 <button class="mic" id="mic"><span class="ico">🎙️</span><span id="miclbl">Tap &amp; speak</span></button>
 <div class="or">— or type —</div>
 <div class="row"><input id="txt" placeholder="e.g. he collapsed and isn't breathing" autocomplete="off"><button class="send" id="go">Ask</button></div>
 <div class="chips" id="chips"></div>
</div>

<div class="you" id="you"></div>
<div class="stage" id="stage">
 <div class="statusbar" id="status"></div>
 <div class="engine">
   <div class="lbl"><span id="elbl">Generating verified guidance…</span><span id="ecount"></span></div>
   <div class="dots" id="dots"></div>
   <div class="shim" id="shim"></div>
 </div>
 <div class="steps" id="stepsCard" style="display:none"><div class="h" id="stepsH">First-aid steps</div><div id="steps"></div></div>
 <div class="call">📞 Call 911 now if you haven't — this is decision support, not a replacement for emergency services.</div>
</div>

<div class="foot">Powered by <b>Google DiffusionGemma</b> · every step <b>checked against official protocols</b> before it's spoken · never an unverified instruction.</div>
</div>
<script>
const $=i=>document.getElementById(i);
const EXAMPLES=["he collapsed and isn't breathing","my dad is choking on food","her arm is bleeding heavily","someone overdosed, lips are blue","kid spilled boiling water on her arm"];
$('chips').innerHTML=EXAMPLES.map(e=>`<span class="chip">${e}</span>`).join('');
document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{$('txt').value=c.textContent;ask(c.textContent);});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function speak(t){try{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(t);u.rate=1.05;speechSynthesis.speak(u);}catch(e){}}

async function ask(text){
  $('you').innerHTML='“ <b>'+text+'</b> ”';
  $('stage').style.display='block';
  $('status').innerHTML='<span class="pill">recognizing…</span>';
  $('elbl').textContent='Generating verified guidance…';$('ecount').textContent='';
  $('dots').innerHTML='';$('shim').classList.add('on');
  $('stepsCard').style.display='none';$('steps').innerHTML='';
  let r;
  try{ r=await(await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})})).json(); }
  catch(e){ $('status').innerHTML='<span class="pill critical">server unreachable</span>';$('shim').classList.remove('on');return; }

  if(!r.recognized){
    $('shim').classList.remove('on');
    $('status').innerHTML='<span class="pill critical">couldn\'t identify</span>';
    $('stepsCard').style.display='block';$('stepsH').textContent='What to do';
    renderSteps([r.spoken||'Call 911 now and describe what you see.']);speak(r.spoken||'Call 911 now.');return;
  }
  // status pills
  $('status').innerHTML=
    `<span class="pill proto">${r.protocol}</span>`+
    `<span class="pill ${r.regime}">${r.regime}</span>`+
    `<span class="pill ${r.fallback?'fallback':'verified'}">${r.fallback?'✓ verified · official protocol':'✓ model-verified'}</span>`;
  // animate the candidate dots (the "spending compute" visual)
  const cands=r.candidates&&r.candidates.length?r.candidates:[{ok:true}];
  for(let i=0;i<cands.length;i++){
    const d=document.createElement('div');d.className='dot';$('dots').appendChild(d);
    requestAnimationFrame(()=>d.classList.add('in'));
    await sleep(90);
    d.classList.add(cands[i].ok?'ok':'bad');
    $('ecount').textContent=(i+1)+(i+1>1?' tries':' try');
  }
  $('shim').classList.remove('on');
  const okN=cands.filter(c=>c.ok).length;
  $('elbl').textContent=r.fallback
    ? `${cands.length} tries didn't verify → using the official protocol`
    : `verified after ${cands.length} ${cands.length>1?'tries':'try'} · ${r.denoising_steps} denoising steps · ${r.latency_ms}ms`;
  await sleep(150);
  // reveal steps
  $('stepsCard').style.display='block';$('stepsH').textContent=r.protocol+' — what to do now';
  renderSteps(r.answer);
  speak(r.protocol+'. '+r.answer.join('. '));
}
function renderSteps(arr){
  const box=$('steps');box.innerHTML='';
  arr.forEach((s,i)=>{
    const row=document.createElement('div');row.className='step';
    row.innerHTML=`<div class="num">${i+1}</div><div class="txt">${s}</div>`;
    box.appendChild(row);setTimeout(()=>row.classList.add('in'),150*i);
  });
}
$('go').onclick=()=>{const v=$('txt').value.trim();if(v)ask(v);};
$('txt').addEventListener('keydown',e=>{if(e.key==='Enter'){const v=$('txt').value.trim();if(v)ask(v);}});
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
if(SR){const rec=new SR();rec.lang='en-US';rec.interimResults=false;const m=$('mic');
 m.onclick=()=>{try{rec.start();m.classList.add('listening');$('miclbl').textContent='listening…';}catch(e){}};
 rec.onresult=e=>ask(e.results[0][0].transcript);
 rec.onerror=()=>{m.classList.remove('listening');$('miclbl').textContent='Tap & speak';};
 rec.onend=()=>{m.classList.remove('listening');$('miclbl').textContent='Tap & speak';};
}else{$('miclbl').textContent='type below';$('mic').style.opacity=.5;}
</script></body></html>
"""
