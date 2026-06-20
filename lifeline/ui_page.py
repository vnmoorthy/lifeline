"""The polished Lifeline UI (single source of truth, no deps). Used by the real product
(diffusion_server) and the local preview (mock_ui). Talks to POST /ask.

Designed for a real emergency: large legible type, calm-clinical dark theme with urgent accents,
screen-reader live regions, reduced-motion support, one-tap Call-911, Repeat + Start-over, and a
visible inference-time-compute panel (candidate cells + progress track)."""

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0a0f15">
<title>Lifeline — verified first aid</title><style>
:root{
 --bg:#0a0f15;--panel:#111a24;--card:#0f1722;--line:#1e2a37;--line2:#2a3a4c;
 --text:#eaf1f8;--dim:#8fa0b2;--red:#e5484d;--red2:#c52f33;--green:#34d399;--amber:#f5b942;--accent:#5cc8ff;
 --r:14px;--rl:18px;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;background:var(--bg);color:var(--text);min-height:100%;
 font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:540px;margin:0 auto;padding:max(20px,env(safe-area-inset-top)) 18px 56px}
.brand{display:flex;align-items:center;gap:9px;justify-content:center;margin-bottom:6px}
.mark{width:26px;height:26px;border-radius:8px;background:var(--red);color:#fff;font-size:17px;
 display:flex;align-items:center;justify-content:center;font-weight:700}
.name{font-size:20px;font-weight:700;letter-spacing:-.3px}
.sub{text-align:center;color:var(--dim);font-size:13px;line-height:1.5;margin:0 6px 16px}
.call911{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;max-width:430px;margin:0 auto 18px;
 text-decoration:none;background:var(--red);color:#fff;font-weight:700;font-size:16px;padding:13px;border-radius:var(--r)}
.call911:active{transform:scale(.99)}
.mic-wrap{display:flex;flex-direction:column;align-items:center;gap:13px}
.mic{position:relative;width:122px;height:122px;border-radius:50%;border:0;cursor:pointer;color:#fff;
 font-size:14px;font-weight:700;background:var(--red);display:flex;flex-direction:column;align-items:center;
 justify-content:center;gap:6px;transition:transform .1s}
.mic:active{transform:scale(.96)}
.mic:focus-visible{outline:3px solid var(--accent);outline-offset:5px}
.mic .ico{font-size:32px}
.mic::after{content:"";position:absolute;inset:-10px;border-radius:50%;border:2px solid var(--red);opacity:0}
.mic.listening::after{animation:ring 1.7s ease-out infinite}
@keyframes ring{0%{transform:scale(.9);opacity:.6}100%{transform:scale(1.28);opacity:0}}
.or{color:var(--dim);font-size:11.5px;letter-spacing:.5px}
.row{display:flex;gap:8px;width:100%;max-width:430px}
input{flex:1;padding:13px 14px;border-radius:12px;border:1px solid var(--line);background:#0c131b;color:var(--text);font-size:16px}
input:focus{outline:none;border-color:var(--accent)}
.send{border:0;border-radius:12px;padding:0 18px;font-weight:700;background:#1b2735;color:var(--text);cursor:pointer;font-size:15px}
.send:focus-visible,.act:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.send:disabled,.mic:disabled{opacity:.5}
.chips{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-top:15px}
.chip{font-size:12.5px;color:var(--dim);background:#0c131b;border:1px solid var(--line);border-radius:999px;padding:7px 13px;cursor:pointer}
.chip:hover,.chip:focus-visible{border-color:var(--accent);color:var(--text);outline:none}
.you{margin:22px 0 12px;font-size:18px;font-weight:600;text-align:center;line-height:1.4}
.stage{display:none}
.statusbar{display:flex;gap:7px;align-items:center;justify-content:center;flex-wrap:wrap;margin-bottom:12px}
.pill{font-size:12.5px;padding:5px 12px;border-radius:999px;border:1px solid var(--line);background:#0c131b;color:var(--dim);
 display:inline-flex;align-items:center;gap:6px}
.pill.proto{color:#fff;border-color:var(--line2)}
.pill.routine::before,.pill.moderate::before,.pill.critical::before{content:"";width:7px;height:7px;border-radius:50%}
.pill.routine{color:var(--green)}.pill.routine::before{background:var(--green)}
.pill.moderate{color:var(--amber)}.pill.moderate::before{background:var(--amber)}
.pill.critical{color:var(--red)}.pill.critical::before{background:var(--red)}
.pill.verified{background:rgba(52,211,153,.12);color:var(--green);border-color:rgba(52,211,153,.4)}
.pill.fallback{background:rgba(245,185,66,.12);color:var(--amber);border-color:rgba(245,185,66,.4)}
.engine{background:var(--panel);border:1px solid var(--line);border-radius:var(--rl);padding:14px 16px;margin-bottom:12px}
.engine .lbl{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.5px;display:flex;justify-content:space-between;gap:8px}
.dots{display:flex;gap:6px;flex-wrap:wrap;margin:11px 0 0}
.dot{width:18px;height:18px;border-radius:5px;background:#1a2530;opacity:.4;transform:scale(.7);transition:.22s}
.dot.in{opacity:1;transform:scale(1)}
.dot.ok{background:var(--green)}.dot.bad{background:var(--red2)}
.track{position:relative;height:4px;border-radius:3px;background:#1a2530;margin-top:12px;overflow:hidden}
.track.on::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(92,200,255,.5),transparent);
 background-size:50% 100%;animation:sh 1.1s linear infinite}
@keyframes sh{0%{background-position:-100% 0}100%{background-position:200% 0}}
.fill{height:100%;width:0;background:var(--accent);border-radius:3px;transition:width .25s}
.steps{display:flex;flex-direction:column;gap:9px;list-style:none;margin:0;padding:0}
.stepsh{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.5px;margin:2px 2px 10px}
.step{display:flex;gap:12px;align-items:flex-start;background:var(--card);border:1px solid var(--line);
 border-radius:var(--r);padding:13px 14px;opacity:0;transform:translateY(7px);transition:.32s}
.step.in{opacity:1;transform:none}
.num{flex:0 0 26px;height:26px;border-radius:50%;background:#10202e;color:var(--accent);font-weight:700;
 display:flex;align-items:center;justify-content:center;font-size:14px}
.step .txt{font-size:17.5px;line-height:1.45;padding-top:2px}
.actions{display:flex;gap:8px;margin-top:14px}
.act{flex:1;border:1px solid var(--line2);background:#13202d;color:#cfe3f5;border-radius:12px;padding:12px;
 font-weight:700;font-size:14px;cursor:pointer}
.act:active{transform:scale(.99)}
.note{margin-top:13px;text-align:center;color:var(--dim);font-size:12.5px;line-height:1.5}
.foot{margin-top:22px;text-align:center;color:var(--dim);font-size:11.5px;line-height:1.6}
.foot b{color:#aeb9c6;font-weight:600}
.sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0}
@media (prefers-reduced-motion:reduce){
 *{animation:none!important}
 .dot{transition:none;opacity:1;transform:none}.step{transition:none;opacity:1;transform:none}
 .track.on::after{display:none}.fill{transition:none}
}
</style></head><body>
<a class="sr" href="#main">Skip to content</a>
<div class="wrap">
<header class="brand"><span class="mark" aria-hidden="true">✚</span><span class="name">Lifeline</span></header>
<p class="sub">Hands-free first aid — every step verified against official protocols before it's spoken.</p>
<a class="call911" href="tel:911" aria-label="Call 911 emergency services now"><span aria-hidden="true">📞</span> Call 911</a>

<main id="main" class="mic-wrap">
 <button class="mic" id="mic" aria-label="Tap and describe the emergency by voice"><span class="ico" aria-hidden="true">🎙️</span><span id="miclbl">Tap &amp; speak</span></button>
 <div class="or">— or type —</div>
 <div class="row"><input id="txt" placeholder="e.g. he collapsed and isn't breathing" autocomplete="off" aria-label="Describe the emergency"><button class="send" id="go">Ask</button></div>
 <div class="chips" id="chips" role="list" aria-label="Example emergencies"></div>
</main>

<div class="you" id="you"></div>
<section class="stage" id="stage" aria-label="Guidance">
 <div class="statusbar" id="status"></div>
 <div class="engine" role="status" aria-live="polite">
   <div class="lbl"><span id="elbl">Generating verified guidance…</span><span id="ecount"></span></div>
   <div class="dots" id="dots" aria-hidden="true"></div>
   <div class="track" id="shim"><div class="fill" id="fill"></div></div>
 </div>
 <div id="stepsCard" style="display:none">
   <div class="stepsh" id="stepsH">First-aid steps</div>
   <ol id="steps" class="steps" aria-live="polite"></ol>
 </div>
 <div class="actions" id="actions" style="display:none">
   <button class="act" id="repeat">🔊 Repeat steps</button>
   <button class="act" id="reset">↺ Start over</button>
 </div>
 <p class="note">Decision support, not a replacement for emergency services. Call 911 for any serious emergency.</p>
</section>

<p class="foot">Powered by <b>Google DiffusionGemma</b> · every step <b>checked against official protocols</b> before it's spoken · never an unverified instruction.</p>
<div class="sr" id="live" aria-live="assertive"></div>
</div>
<script>
const $=i=>document.getElementById(i);
const REDUCED=window.matchMedia&&matchMedia('(prefers-reduced-motion:reduce)').matches;
const EXAMPLES=["he collapsed and isn't breathing","my dad is choking on food","her arm is bleeding heavily","someone overdosed, lips are blue","kid spilled boiling water on her arm","i think he's having a stroke"];
$('chips').innerHTML=EXAMPLES.map(e=>`<button class="chip" role="listitem">${e}</button>`).join('');
document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{$('txt').value=c.textContent;ask(c.textContent);});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let lastSpeak='';let busy=false;
function speak(t){lastSpeak=t;try{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(t);u.rate=1.04;speechSynthesis.speak(u);}catch(e){}}
function announce(t){$('live').textContent=t;}

async function ask(text){
  text=(text||'').trim();
  if(!text){announce('Please describe the emergency first.');return;}
  if(busy)return; busy=true;
  $('txt').blur();$('go').disabled=true;$('mic').disabled=true;
  try{
    try{speechSynthesis.cancel();}catch(e){}
    $('you').innerHTML='“ '+text+' ”';
    $('stage').style.display='block';
    $('actions').style.display='none';
    $('status').innerHTML='<span class="pill">recognizing…</span>';
    $('elbl').textContent='Generating verified guidance…';$('ecount').textContent='';
    $('dots').innerHTML='';$('fill').style.width='0';$('shim').classList.add('on');
    $('stepsCard').style.display='none';$('steps').innerHTML='';
    announce('Working on it.');
    let r;
    const ctrl=new AbortController();const to=setTimeout(()=>ctrl.abort(),30000);
    try{
      r=await(await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text}),signal:ctrl.signal})).json();
    }catch(e){
      $('shim').classList.remove('on');
      $('status').innerHTML='<span class="pill critical">Network unavailable — call 911</span>';
      $('stepsCard').style.display='block';$('stepsH').textContent='What to do';
      renderSteps(['Call 911 now and describe what you see.']);
      $('actions').style.display='flex';speak('Network unavailable. Call 911 now.');announce('Network unavailable. Call 911 now.');return;
    }finally{clearTimeout(to);}

    if(!r.recognized){
      $('shim').classList.remove('on');
      $('status').innerHTML='<span class="pill critical">Unrecognized emergency — call 911</span>';
      $('stepsCard').style.display='block';$('stepsH').textContent='What to do';
      const msg=r.spoken||'Call 911 now and describe what you see.';
      renderSteps([msg]);speak(msg);$('actions').style.display='flex';announce(msg);return;
    }
    $('status').innerHTML=
      `<span class="pill proto">${r.protocol}</span>`+
      `<span class="pill ${r.regime}">${r.regime}</span>`+
      `<span class="pill ${r.fallback?'fallback':'verified'}">${r.fallback?'⚠ Fallback: official protocol':'✓ model-verified'}</span>`;
    const cands=r.candidates&&r.candidates.length?r.candidates:[{ok:true}];
    if(REDUCED){
      cands.forEach(c=>{const d=document.createElement('div');d.className='dot in '+(c.ok?'ok':'bad');$('dots').appendChild(d);});
      $('ecount').textContent=cands.length+(cands.length>1?' tries':' try');$('fill').style.width='100%';
    }else{
      for(let i=0;i<cands.length;i++){
        const d=document.createElement('div');d.className='dot';$('dots').appendChild(d);
        requestAnimationFrame(()=>d.classList.add('in'));
        await sleep(90);
        d.classList.add(cands[i].ok?'ok':'bad');
        $('ecount').textContent=(i+1)+(i+1>1?' tries':' try');
        $('fill').style.width=Math.round((i+1)/cands.length*100)+'%';
      }
    }
    $('shim').classList.remove('on');
    $('elbl').textContent=r.fallback
      ? 'Model could not verify — showing official protocol steps'
      : `verified after ${cands.length} ${cands.length>1?'tries':'try'} · ${r.denoising_steps} denoising steps · ${r.latency_ms}ms`;
    if(!REDUCED)await sleep(150);
    $('stepsCard').style.display='block';$('stepsH').textContent=r.protocol+' — what to do now';
    renderSteps(r.answer);
    $('actions').style.display='flex';
    speak(r.protocol+'. '+r.answer.join('. '));
    announce(r.protocol+'. '+r.answer.join('. '));
  }finally{
    busy=false;$('go').disabled=false;$('mic').disabled=false;
  }
}
function renderSteps(arr){
  if(!Array.isArray(arr))arr=[String(arr||'Call 911 now.')];
  const box=$('steps');box.innerHTML='';
  arr.forEach((s,i)=>{
    const row=document.createElement('li');row.className='step';
    row.innerHTML=`<div class="num" aria-hidden="true">${i+1}</div><div class="txt">${s}</div>`;
    box.appendChild(row);
    if(REDUCED)row.classList.add('in');else setTimeout(()=>row.classList.add('in'),140*i);
  });
}
function resetAll(){
  try{speechSynthesis.cancel();}catch(e){}
  lastSpeak='';
  $('stage').style.display='none';$('you').innerHTML='';$('txt').value='';
  $('txt').focus();announce('Ready.');
}
$('go').onclick=()=>ask($('txt').value);
$('txt').addEventListener('keydown',e=>{if(e.key==='Enter')ask($('txt').value);});
$('repeat').onclick=()=>{if(lastSpeak)speak(lastSpeak);};
$('reset').onclick=resetAll;
document.addEventListener('keydown',e=>{if(e.key==='Escape'){try{speechSynthesis.cancel();}catch(e){}}});
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
if(SR){const rec=new SR();rec.lang='en-US';rec.interimResults=false;const m=$('mic');
 m.onclick=()=>{try{rec.start();m.classList.add('listening');$('miclbl').textContent='listening…';announce('Listening.');}catch(e){}};
 rec.onresult=e=>ask(e.results[0][0].transcript);
 rec.onerror=()=>{m.classList.remove('listening');$('miclbl').textContent='Tap & speak';announce('Speech recognition failed. Please type instead.');};
 rec.onend=()=>{m.classList.remove('listening');$('miclbl').textContent='Tap & speak';};
}else{$('miclbl').textContent='type below';$('mic').setAttribute('aria-hidden','true');$('mic').style.opacity=.5;}
</script></body></html>
"""
