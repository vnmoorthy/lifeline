"""The polished Lifeline UI (single source of truth, no deps). Used by the real product
(diffusion_server) and the local preview (mock_ui). Talks to POST /ask.

Designed for a real emergency: large text, high contrast, screen-reader live regions,
reduced-motion support, a one-tap Call-911 link, and Repeat/Start-over controls."""

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0a0e13">
<title>Lifeline — verified first aid</title><style>
:root{
 --bg:#0a0e13;--bg2:#0e141c;--panel:#141b24;--line:#222d3a;--text:#eef3f8;--dim:#93a1b2;
 --red:#ff4d4d;--red2:#c81e1e;--green:#39d353;--amber:#e3b341;--accent:#5cabff;
 --shadow:0 8px 30px rgba(0,0,0,.45);--r:16px;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;background:radial-gradient(1200px 600px at 50% -10%,#11202f 0,var(--bg) 60%);color:var(--text);
 font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;min-height:100%}
.wrap{max-width:560px;margin:0 auto;padding:max(22px,env(safe-area-inset-top)) 18px 56px}
.top{display:flex;align-items:center;gap:10px;justify-content:center;margin-bottom:2px}
.logo{font-size:22px;font-weight:800;letter-spacing:-.3px}
.logo b{color:var(--red)}
.sub{text-align:center;color:var(--dim);font-size:13.5px;margin-bottom:20px}
.call911{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;max-width:420px;margin:0 auto 16px;
 text-decoration:none;background:linear-gradient(180deg,#ff5b5b,#d11f1f);color:#fff;font-weight:800;font-size:16px;
 padding:13px;border-radius:12px;box-shadow:0 6px 18px rgba(255,77,77,.3)}
.call911:active{transform:scale(.99)}
.mic-wrap{display:flex;flex-direction:column;align-items:center;gap:14px}
.mic{width:132px;height:132px;border-radius:50%;border:0;cursor:pointer;color:#fff;font-size:15px;font-weight:700;
 background:radial-gradient(circle at 50% 35%,var(--red),var(--red2));box-shadow:var(--shadow),0 0 0 0 rgba(255,77,77,.5);
 display:flex;align-items:center;justify-content:center;flex-direction:column;gap:6px;transition:transform .1s}
.mic:active{transform:scale(.96)}
.mic:focus-visible{outline:3px solid var(--accent);outline-offset:4px}
.mic .ico{font-size:36px}
.mic.listening{animation:pulse 1.3s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(255,77,77,.55)}70%{box-shadow:0 0 0 26px rgba(255,77,77,0)}100%{box-shadow:0 0 0 0 rgba(255,77,77,0)}}
.or{color:var(--dim);font-size:12px;letter-spacing:.5px}
.row{display:flex;gap:8px;width:100%;max-width:420px}
input{flex:1;padding:14px;border-radius:12px;border:1px solid var(--line);background:#0b1118;color:var(--text);font-size:16px}
input:focus{outline:none;border-color:var(--accent)}
.send{border:0;border-radius:12px;padding:0 20px;font-weight:700;background:#1c2734;color:var(--text);cursor:pointer;font-size:15px}
.send:focus-visible,.act:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.chips{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-top:14px}
.chip{font-size:12.5px;color:var(--dim);background:#10171f;border:1px solid var(--line);border-radius:999px;padding:7px 13px;cursor:pointer}
.chip:hover,.chip:focus-visible{border-color:var(--accent);color:var(--text);outline:none}
.you{margin:22px 0 6px;font-size:18px;text-align:center}.you b{color:#fff}
.stage{display:none}
.statusbar{display:flex;gap:8px;align-items:center;justify-content:center;flex-wrap:wrap;margin:10px 0}
.pill{font-size:12.5px;padding:5px 12px;border-radius:999px;border:1px solid var(--line);background:#10171f;color:var(--dim)}
.pill.proto{color:#fff;border-color:#2b3a4b}
.pill.routine{color:var(--green);border-color:rgba(57,211,83,.35)}
.pill.moderate{color:var(--amber);border-color:rgba(227,179,65,.35)}
.pill.critical{color:var(--red);border-color:rgba(255,77,77,.4)}
.pill.verified{background:rgba(57,211,83,.12);color:var(--green);border-color:rgba(57,211,83,.4)}
.pill.fallback{background:rgba(227,179,65,.12);color:var(--amber);border-color:rgba(227,179,65,.4)}
.engine{background:linear-gradient(180deg,#101822,#0d141c);border:1px solid var(--line);border-radius:var(--r);padding:14px 16px;margin-top:6px}
.engine .lbl{font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:.6px;display:flex;justify-content:space-between;gap:8px}
.dots{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0 2px}
.dot{width:16px;height:16px;border-radius:5px;background:#1d2a38;opacity:.25;transform:scale(.6);transition:.25s}
.dot.in{opacity:1;transform:scale(1)}
.dot.ok{background:var(--green)}.dot.bad{background:var(--red2)}
.shim{height:3px;border-radius:2px;margin-top:8px;background:linear-gradient(90deg,#1d2a38,#2b6cb0,#1d2a38);background-size:200% 100%;animation:sh 1.1s linear infinite;opacity:0}
.shim.on{opacity:1}@keyframes sh{0%{background-position:200% 0}100%{background-position:-200% 0}}
.steps{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:6px 8px 10px;margin-top:12px;box-shadow:var(--shadow)}
.steps .h{display:flex;align-items:center;gap:8px;padding:12px 12px 6px;color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.6px}
.step{display:flex;gap:12px;align-items:flex-start;padding:12px;border-top:1px solid var(--line);opacity:0;transform:translateY(8px);transition:.35s}
.step.in{opacity:1;transform:none}
.step:first-of-type{border-top:0}
.num{flex:0 0 28px;height:28px;border-radius:50%;background:#192633;color:var(--accent);font-weight:800;display:flex;align-items:center;justify-content:center;font-size:15px}
.step .txt{font-size:18.5px;line-height:1.45;padding-top:2px}
.actions{display:flex;gap:8px;margin-top:12px}
.act{flex:1;border:1px solid var(--line);background:#141d28;color:var(--text);border-radius:12px;padding:12px;font-weight:700;font-size:14px;cursor:pointer}
.act:active{transform:scale(.99)}
.act.primary{background:#16324a;border-color:#27506f;color:#cfe6ff}
.note{margin-top:12px;text-align:center;color:var(--dim);font-size:12.5px;line-height:1.5}
.foot{margin-top:22px;text-align:center;color:var(--dim);font-size:12px;line-height:1.6}
.foot b{color:#aeb9c6;font-weight:600}
.sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0}
@media (prefers-reduced-motion:reduce){
 *{animation:none!important}
 .mic.listening{box-shadow:var(--shadow),0 0 0 6px rgba(255,77,77,.35)}
 .dot{transition:none;opacity:1;transform:none}.step{transition:none;opacity:1;transform:none}.shim{display:none}
}
</style></head><body>
<a class="sr" href="#main">Skip to content</a>
<div class="wrap">
<header class="top"><div class="logo"><b>✚</b> Lifeline</div></header>
<p class="sub">Hands-free first aid — verified against official protocols, on-device DiffusionGemma.</p>
<a class="call911" href="tel:911" aria-label="Call 911 emergency services now">📞 Call 911</a>

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
   <div class="shim" id="shim"></div>
 </div>
 <div class="steps" id="stepsCard" style="display:none">
   <div class="h" id="stepsH">First-aid steps</div>
   <ol id="steps" style="margin:0;padding:0;list-style:none" aria-live="polite"></ol>
 </div>
 <div class="actions" id="actions" style="display:none">
   <button class="act primary" id="repeat">🔊 Repeat steps</button>
   <button class="act" id="reset">↺ Start over</button>
 </div>
 <p class="note">This is decision support, not a replacement for emergency services. Call 911 for any serious emergency.</p>
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
    $('you').innerHTML='“ <b>'+text+'</b> ”';
    $('stage').style.display='block';
    $('actions').style.display='none';
    $('status').innerHTML='<span class="pill">recognizing…</span>';
    $('elbl').textContent='Generating verified guidance…';$('ecount').textContent='';
    $('dots').innerHTML='';$('shim').classList.add('on');
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
      $('actions').style.display='flex';announce('Network unavailable. Call 911 now.');return;
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
      $('ecount').textContent=cands.length+(cands.length>1?' tries':' try');
    }else{
      for(let i=0;i<cands.length;i++){
        const d=document.createElement('div');d.className='dot';$('dots').appendChild(d);
        requestAnimationFrame(()=>d.classList.add('in'));
        await sleep(90);
        d.classList.add(cands[i].ok?'ok':'bad');
        $('ecount').textContent=(i+1)+(i+1>1?' tries':' try');
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
  const box=$('steps');box.innerHTML='';
  arr.forEach((s,i)=>{
    const row=document.createElement('li');row.className='step';
    row.innerHTML=`<div class="num" aria-hidden="true">${i+1}</div><div class="txt">${s}</div>`;
    box.appendChild(row);
    if(REDUCED)row.classList.add('in');else setTimeout(()=>row.classList.add('in'),150*i);
  });
}
function resetAll(){
  try{speechSynthesis.cancel();}catch(e){}
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
