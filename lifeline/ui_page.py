"""The Lifeline UI — a native-feeling, installable mobile web app (single source of truth, no deps).
Used by the real product (diffusion_server) and the local preview (mock_ui). Talks to POST /ask.

Native app shell (home/result screens + transitions + bottom dock), immersive listening overlay
with live waveform, crisp inline-SVG icons, spring motion + haptics, screen-reader live regions,
reduced-motion support, and PWA installability (manifest + service worker offline shell).

Exports: PAGE (html), MANIFEST (webmanifest json), ICON_SVG (app icon), SW_JS (service worker)."""

ICON_SVG = r"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" rx="112" fill="#e5484d"/><rect x="226" y="120" width="60" height="272" rx="14" fill="#fff"/><rect x="120" y="226" width="272" height="60" rx="14" fill="#fff"/></svg>"""

MANIFEST = (
    '{"name":"Lifeline — verified first aid","short_name":"Lifeline","start_url":"/",'
    '"display":"standalone","orientation":"portrait","background_color":"#0a0f15",'
    '"theme_color":"#0a0f15","description":"Hands-free first aid, every step verified against '
    'official protocols.","icons":[{"src":"/icon.svg","sizes":"any","type":"image/svg+xml",'
    '"purpose":"any maskable"}]}'
)

SW_JS = r"""const C='lifeline-v2';const SHELL=['/','/icon.svg','/manifest.webmanifest'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==C).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;const req=e.request;
 if(req.mode==='navigate'){e.respondWith(fetch(req).then(r=>{const cp=r.clone();caches.open(C).then(c=>c.put('/',cp));return r;}).catch(()=>caches.match('/')));return;}
 e.respondWith(caches.match(req).then(r=>r||fetch(req).then(rr=>{const cp=rr.clone();caches.open(C).then(c=>c.put(req,cp));return rr;})));});
"""

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0a0f15">
<link rel="manifest" href="/manifest.webmanifest">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Lifeline">
<link rel="apple-touch-icon" href="/icon.svg">
<title>Lifeline — verified first aid</title><style>
:root{
 --bg:#0b0e14;--bg2:#131a24;--panel:#141c27;--card:#161f2b;--line:#232f3f;--line2:#2c3a4d;
 --text:#eef3f9;--dim:#94a2b4;--red:#e5484d;--red2:#b23a3e;--green:#35d6a0;--amber:#f3b340;
 --accent:#5c9dff;--primary:#5c9dff;--primary-ink:#06101f;
 --r:14px;--rl:18px;--fstep:17.5px;--fbody:18px;--spring:cubic-bezier(.2,.8,.2,1);
 --sat:env(safe-area-inset-top);--sab:env(safe-area-inset-bottom);
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%;background:var(--bg);color:var(--text);overflow:hidden;
 font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
svg{display:block}
.app{position:relative;width:100%;max-width:520px;height:100vh;height:100dvh;margin:0 auto;overflow:hidden}
.screen{position:absolute;inset:0;display:flex;flex-direction:column;opacity:0;transform:translateX(22px) scale(.99);
 pointer-events:none;transition:opacity .26s ease,transform .34s var(--spring)}
.screen.active{opacity:1;transform:none;pointer-events:auto}
#homeScreen{transform:translateX(-22px) scale(.99)}#homeScreen.active{transform:none}
.appbar{display:flex;align-items:center;gap:10px;padding:calc(10px + var(--sat)) 14px 10px;min-height:52px}
.appbar .ttl{font-size:16px;font-weight:700;letter-spacing:-.2px;flex:1;display:flex;align-items:center;gap:8px;justify-content:center}
.mark{width:24px;height:24px;border-radius:7px;background:var(--red);display:flex;align-items:center;justify-content:center}
.mark svg{width:15px;height:15px}
.iconbtn{width:40px;height:40px;border-radius:11px;border:1px solid var(--line);background:var(--bg2);color:var(--dim);
 display:flex;align-items:center;justify-content:center;cursor:pointer;flex:0 0 auto;transition:transform .12s,border-color .2s}
.iconbtn svg{width:20px;height:20px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.iconbtn:active{transform:scale(.92)}.iconbtn:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.tt{font-size:14px;font-weight:700;color:var(--dim)}
.tt[aria-pressed="true"]{color:var(--text);border-color:var(--accent)}
.mid{flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch;padding:8px 18px 6px;display:flex;flex-direction:column}
.hero{text-align:center;margin:6vh 0 18px}
.hero h1{font-size:25px;font-weight:700;letter-spacing:-.4px;margin:0 0 8px}
.hero p{color:var(--dim);font-size:13.5px;line-height:1.5;margin:0 8px}
.chips{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-top:4px}
.chip{font-size:12.5px;color:var(--dim);background:var(--bg2);border:1px solid var(--line);border-radius:999px;
 padding:8px 13px;cursor:pointer;transition:transform .12s,border-color .2s,color .2s}
.chip:active{transform:scale(.96)}.chip:hover,.chip:focus-visible{border-color:var(--accent);color:var(--text);outline:none}
.dock{padding:10px 16px calc(12px + var(--sab));border-top:1px solid var(--line);background:linear-gradient(180deg,transparent,var(--bg2))}
.row{display:flex;gap:8px}
input{flex:1;padding:13px 14px;border-radius:12px;border:1px solid var(--line);background:var(--bg2);color:var(--text);font-size:16px}
input:focus{outline:none;border-color:var(--accent)}
.send{border:0;border-radius:12px;padding:0 18px;font-weight:700;background:#1b2735;color:var(--text);cursor:pointer;font-size:15px;transition:transform .12s}
.send:active{transform:scale(.97)}
.send:disabled,.mic:disabled{opacity:.5}
.micwrap{display:flex;justify-content:center;margin:12px 0 10px}
.mic{position:relative;display:flex;align-items:center;gap:10px;border:0;cursor:pointer;color:var(--primary-ink);font-size:16px;font-weight:700;
 background:var(--primary);border-radius:999px;padding:15px 26px;transition:transform .12s}
.mic svg{width:22px;height:22px;stroke:var(--primary-ink);fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.mic:active{transform:scale(.96)}.mic:focus-visible{outline:3px solid var(--accent);outline-offset:4px}
.mic::after{content:"";position:absolute;inset:-6px;border-radius:999px;border:2px solid var(--primary);opacity:0}
.mic.listening::after{animation:ring 1.7s ease-out infinite}
@keyframes ring{0%{transform:scale(.96);opacity:.55}100%{transform:scale(1.14);opacity:0}}
.call911{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;text-decoration:none;
 background:var(--red);color:#fff;font-weight:700;font-size:16px;padding:13px;border-radius:var(--r);transition:transform .12s}
.call911 svg{width:18px;height:18px;stroke:#fff;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.call911:active{transform:scale(.99)}
.rscroll{flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch;padding:4px 18px 8px}
.you{margin:4px 0 14px;font-size:var(--fbody);font-weight:600;text-align:center;line-height:1.4}
.statusbar{display:flex;gap:7px;align-items:center;justify-content:center;flex-wrap:wrap;margin-bottom:12px}
.pill{font-size:12.5px;padding:5px 12px;border-radius:999px;border:1px solid var(--line);background:var(--bg2);color:var(--dim);display:inline-flex;align-items:center;gap:6px}
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
.dot{width:18px;height:18px;border-radius:5px;background:#1a2530;opacity:.4;transform:scale(.7);transition:.22s var(--spring)}
.dot.in{opacity:1;transform:scale(1)}.dot.ok{background:var(--green)}.dot.bad{background:var(--red2)}
.legend{font-size:10.5px;color:var(--dim);margin-top:8px;display:none}
.legend .g{color:var(--green)}.legend .b{color:#c98}
.track{position:relative;height:4px;border-radius:3px;background:#1a2530;margin-top:10px;overflow:hidden}
.track.on::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(92,157,255,.55),transparent);background-size:50% 100%;animation:sh 1.1s linear infinite}
@keyframes sh{0%{background-position:-100% 0}100%{background-position:200% 0}}
.fill{height:100%;width:0;background:var(--accent);border-radius:3px;transition:width .25s}
.steps-head{display:flex;align-items:center;margin:2px 2px 4px}
.stepsh{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
.speakind{display:none;align-items:center;gap:6px;color:var(--accent);font-size:11px;margin-left:8px;text-transform:none}
.speakind.on{display:inline-flex}
.eq{display:inline-flex;gap:2px;align-items:flex-end;height:12px}
.eq i{width:3px;height:5px;background:var(--accent);border-radius:1px;animation:eq .9s ease-in-out infinite}
.eq i:nth-child(2){animation-delay:.15s}.eq i:nth-child(3){animation-delay:.3s}
@keyframes eq{0%,100%{height:4px}50%{height:12px}}
.taphint{color:var(--dim);font-size:11.5px;margin:0 2px 10px}
.steps{display:flex;flex-direction:column;gap:9px;list-style:none;margin:0;padding:0}
.step{display:flex;gap:12px;align-items:flex-start;background:var(--card);border:1px solid var(--line);border-radius:var(--r);
 padding:13px 14px;opacity:0;transform:translateY(8px);transition:opacity .3s,transform .34s var(--spring),border-color .2s;cursor:pointer}
.step.in{opacity:1;transform:none}.step:active{transform:scale(.99)}
.step:hover{border-color:var(--line2)}.step.flash{border-color:var(--accent)}
.step:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.num{flex:0 0 26px;height:26px;border-radius:50%;background:rgba(92,157,255,.15);color:var(--accent);font-weight:700;display:flex;align-items:center;justify-content:center;font-size:14px}
.step .txt{font-size:var(--fstep);line-height:1.45;padding-top:2px}
.note{margin:13px 2px 4px;text-align:center;color:var(--dim);font-size:12.5px;line-height:1.5}
.actions{display:flex;gap:8px;margin-bottom:10px}
.act{flex:1;border:1px solid var(--line2);background:#13202d;color:#cfe3f5;border-radius:12px;padding:12px;font-weight:700;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:7px;transition:transform .12s}
.act:active{transform:scale(.98)}.act svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.listen{position:absolute;inset:0;z-index:5;background:rgba(7,11,16,.94);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px;
 opacity:0;transform:scale(1.04);pointer-events:none;transition:opacity .22s,transform .3s var(--spring);padding:24px}
.listen.on{opacity:1;transform:none;pointer-events:auto}
.listenX{position:absolute;top:calc(14px + var(--sat));right:16px}
.wave{display:flex;align-items:center;gap:5px;height:64px}
.wave i{width:6px;height:14px;border-radius:3px;background:var(--accent);animation:wv 1s ease-in-out infinite}
.wave i:nth-child(2){animation-delay:.1s}.wave i:nth-child(3){animation-delay:.2s}.wave i:nth-child(4){animation-delay:.3s}
.wave i:nth-child(5){animation-delay:.4s}.wave i:nth-child(6){animation-delay:.25s}.wave i:nth-child(7){animation-delay:.15s}
@keyframes wv{0%,100%{height:12px}50%{height:56px}}
.listen .lt{color:var(--dim);font-size:13px;letter-spacing:.3px}
.listen .pt{font-size:20px;font-weight:600;text-align:center;min-height:28px;max-width:320px}
.foot{padding:4px 18px 8px;text-align:center;color:var(--dim);font-size:11px;line-height:1.5}
.foot b{color:#aeb9c6;font-weight:600}
.sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0}
body.large{--fstep:21px;--fbody:21px}
body.large .hero h1{font-size:28px}body.large .act{font-size:16px}body.large .num{font-size:16px}
@media (prefers-reduced-motion:reduce){
 *{animation:none!important}
 .screen{transition:opacity .01s}.screen,#homeScreen{transform:none}
 .dot,.step{transition:none;opacity:1;transform:none}.track.on::after{display:none}.fill{transition:none}
 .listen{transition:opacity .01s;transform:none}
}
.deskhint{display:none}
@media (min-width:760px){
 html,body{overflow:auto;height:auto}
 body{display:flex;align-items:center;justify-content:center;min-height:100dvh;
  background:radial-gradient(1100px 700px at 50% -5%,#0e1622,#070a0e 62%);padding:30px 16px 46px}
 .app{width:392px;height:min(86dvh,800px);border:1px solid #2a3a4d;border-radius:34px;box-shadow:0 26px 70px rgba(0,0,0,.55)}
 .deskhint{display:block;position:fixed;left:0;right:0;bottom:14px;text-align:center;color:var(--dim);font-size:12.5px}
}
</style></head><body>
<a class="sr" href="#main">Skip to content</a>
<div class="app">

<section class="screen home active" id="homeScreen">
 <div class="appbar">
   <span style="width:40px"></span>
   <span class="ttl"><span class="mark" aria-hidden="true"></span>Lifeline</span>
   <button class="iconbtn tt" id="bigtext" aria-pressed="false" aria-label="Toggle large text">Aa</button>
 </div>
 <main class="mid" id="main">
   <div class="hero"><h1>What's the emergency?</h1><p>Hands-free first aid — every step verified against official protocols before it's spoken.</p></div>
   <div class="chips" id="chips" role="list" aria-label="Example emergencies"></div>
 </main>
 <p class="foot">Powered by <b>Google DiffusionGemma</b> · every step <b>checked against official protocols</b>.</p>
 <div class="dock">
   <div class="row"><input id="txt" placeholder="Describe what's happening…" autocomplete="off" aria-label="Describe the emergency"><button class="send" id="go">Ask</button></div>
   <div class="micwrap"><button class="mic" id="mic" aria-label="Tap and describe the emergency by voice"><span class="mico" aria-hidden="true"></span><span id="miclbl">Tap &amp; speak</span></button></div>
   <a class="call911" href="tel:911" aria-label="Call 911 emergency services now"><span class="callico" aria-hidden="true"></span> Call 911</a>
 </div>
</section>

<section class="screen result" id="resultScreen">
 <div class="appbar">
   <button class="iconbtn" id="back" aria-label="Back to start"></button>
   <span class="ttl"><span class="mark" aria-hidden="true"></span>Lifeline</span>
   <button class="iconbtn tt" id="bigtext2" aria-pressed="false" aria-label="Toggle large text">Aa</button>
 </div>
 <div class="rscroll">
   <div class="you" id="you"></div>
   <div class="statusbar" id="status"></div>
   <div class="engine" role="status" aria-live="polite">
     <div class="lbl"><span id="elbl">Generating verified guidance…</span><span id="ecount"></span></div>
     <div class="dots" id="dots" aria-hidden="true"></div>
     <div class="track" id="shim"><div class="fill" id="fill"></div></div>
     <div class="legend" id="legend"><span class="g">■</span> passed the protocol check · <span class="b">■</span> rejected draft</div>
   </div>
   <div id="stepsCard" style="display:none">
     <div class="steps-head"><span class="stepsh" id="stepsH">First-aid steps</span><span class="speakind" id="speakind" aria-hidden="true"><span class="eq"><i></i><i></i><i></i></span>Speaking…</span></div>
     <div class="taphint" id="taphint" style="display:none">Tap any step to hear it again.</div>
     <ol id="steps" class="steps" aria-live="polite"></ol>
   </div>
   <p class="note">Decision support, not a replacement for emergency services. Call 911 for any serious emergency.</p>
 </div>
 <div class="dock">
   <div class="actions" id="actions">
     <button class="act" id="retry" style="display:none"></button>
     <button class="act" id="repeat"></button>
     <button class="act" id="reset"></button>
   </div>
   <a class="call911" href="tel:911" aria-label="Call 911 emergency services now"><span class="callico" aria-hidden="true"></span> Call 911</a>
 </div>
</section>

<div class="listen" id="listen" role="dialog" aria-label="Listening">
 <button class="iconbtn listenX" id="listenX" aria-label="Cancel listening"></button>
 <div class="wave" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
 <div class="lt">Listening…</div>
 <div class="pt" id="partial"></div>
</div>

<p class="deskhint">Mobile-first demo — tap a chip or the mic. Best experienced on a phone.</p>
<div class="sr" id="live" aria-live="assertive"></div>
</div>
<script>
const $=i=>document.getElementById(i);
const REDUCED=window.matchMedia&&matchMedia('(prefers-reduced-motion:reduce)').matches;
const ICO={
 mic:'<svg viewBox="0 0 24 24"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>',
 phone:'<svg viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.12 4.18 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.72 12.8 12.8 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.8 12.8 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
 vol:'<svg viewBox="0 0 24 24"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>',
 stop:'<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>',
 restart:'<svg viewBox="0 0 24 24"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-9.36L1 10"/></svg>',
 back:'<svg viewBox="0 0 24 24"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>',
 x:'<svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
};
const MARK='<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="10.5" y="4" width="3" height="16" rx="1" fill="#fff"/><rect x="4" y="10.5" width="16" height="3" rx="1" fill="#fff"/></svg>';
document.querySelectorAll('.mark').forEach(m=>m.innerHTML=MARK);
document.querySelectorAll('.mico').forEach(m=>m.innerHTML=ICO.mic);
document.querySelectorAll('.callico').forEach(m=>m.innerHTML=ICO.phone);
$('back').innerHTML=ICO.back;$('listenX').innerHTML=ICO.x;
$('retry').innerHTML=ICO.restart+' Try again';$('reset').innerHTML=ICO.restart+' Start over';

const EXAMPLES=["he collapsed and isn't breathing","my dad is choking on food","her arm is bleeding heavily","someone overdosed, lips are blue","kid spilled boiling water on her arm","i think he's having a stroke"];
$('chips').innerHTML=EXAMPLES.map(e=>`<button class="chip" role="listitem">${e}</button>`).join('');
document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{$('txt').value=c.textContent;ask(c.textContent);});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let lastSpeak='';let lastQuery='';let busy=false;
function buzz(p){try{if(navigator.vibrate&&!REDUCED)navigator.vibrate(p);}catch(e){}}
function showScreen(n){$('homeScreen').classList.toggle('active',n==='home');$('resultScreen').classList.toggle('active',n==='result');}

// large-text (persisted, both toggles stay in sync)
function applyLarge(on){document.body.classList.toggle('large',on);$('bigtext').setAttribute('aria-pressed',on?'true':'false');$('bigtext2').setAttribute('aria-pressed',on?'true':'false');try{localStorage.setItem('lifeline-large',on?'1':'0');}catch(e){}}
try{if(localStorage.getItem('lifeline-large')==='1')applyLarge(true);}catch(e){}
$('bigtext').onclick=$('bigtext2').onclick=()=>applyLarge(!document.body.classList.contains('large'));

// speech
function setSpeaking(on){$('speakind').classList.toggle('on',on);const b=$('repeat');if(b){b.innerHTML=(on?ICO.stop+' Stop':ICO.vol+' Repeat steps');b.setAttribute('aria-pressed',on?'true':'false');}}
function speakRaw(t){try{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(t);u.rate=1.04;u.onstart=()=>setSpeaking(true);u.onend=()=>setSpeaking(false);u.onerror=()=>setSpeaking(false);speechSynthesis.speak(u);}catch(e){}}
function speak(t){lastSpeak=t;speakRaw(t);}
function stopSpeech(){try{speechSynthesis.cancel();}catch(e){}setSpeaking(false);}
function announce(t){$('live').textContent=t;}
setSpeaking(false);

async function ask(text){
  text=(text||'').trim();
  if(!text){announce('Please describe the emergency first.');return;}
  if(busy)return; busy=true; lastQuery=text;
  $('txt').blur();$('go').disabled=true;$('mic').disabled=true;
  showScreen('result');
  setTimeout(()=>{try{$('back').focus();}catch(e){}},60);
  try{
    stopSpeech();
    $('you').innerHTML='“ '+text+' ”';
    $('actions').style.display='flex';$('retry').style.display='none';
    $('status').innerHTML='<span class="pill">recognizing…</span>';
    $('elbl').textContent='Drafting answers and checking each against the official protocol…';$('ecount').textContent='';
    $('dots').innerHTML='';$('fill').style.width='0';$('shim').classList.add('on');$('legend').style.display='none';
    $('stepsCard').style.display='none';$('steps').innerHTML='';$('taphint').style.display='none';
    announce('Working on it.');
    let r;
    const ctrl=new AbortController();const to=setTimeout(()=>ctrl.abort(),30000);
    try{
      r=await(await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text}),signal:ctrl.signal})).json();
    }catch(e){
      buzz(40);$('shim').classList.remove('on');
      $('status').innerHTML='<span class="pill critical">Network unavailable — call 911</span>';
      $('stepsCard').style.display='block';$('stepsH').textContent='What to do';
      renderSteps(['Call 911 now and describe what you see.']);
      $('retry').style.display='';speak('Network unavailable. Call 911 now.');announce('Network unavailable. Call 911 now.');return;
    }finally{clearTimeout(to);}

    if(!r.recognized){
      $('shim').classList.remove('on');
      $('status').innerHTML='<span class="pill critical">Unrecognized emergency — call 911</span>';
      $('stepsCard').style.display='block';$('stepsH').textContent='What to do';
      const msg=r.spoken||'Call 911 now and describe what you see.';
      renderSteps([msg]);speak(msg);announce(msg);return;
    }
    $('status').innerHTML=
      `<span class="pill proto">${r.protocol}</span>`+
      `<span class="pill ${r.regime}">${r.regime}</span>`+
      `<span class="pill ${r.fallback?'fallback':'verified'}">${r.fallback?'⚠ Fallback: official protocol':'✓ model-verified'}</span>`;
    const cands=r.candidates&&r.candidates.length?r.candidates:[{ok:true}];
    $('legend').style.display=cands.length>1?'block':'none';
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
    $('shim').classList.remove('on');buzz(r.fallback?[10,30,10]:18);
    $('elbl').textContent=r.fallback
      ? 'No draft passed the protocol check — showing the official protocol'
      : `verified after ${cands.length} ${cands.length>1?'tries':'try'} · ${r.denoising_steps} denoising steps · ${r.latency_ms}ms`;
    if(!REDUCED)await sleep(150);
    $('stepsCard').style.display='block';$('stepsH').textContent=r.protocol+' — what to do now';
    const answerArr=Array.isArray(r.answer)?r.answer:[String(r.answer||'Call 911 now.')];
    renderSteps(answerArr);
    speak(r.protocol+'. '+answerArr.join('. '));
    announce(r.protocol+'. '+answerArr.join('. '));
  }finally{
    busy=false;$('go').disabled=false;$('mic').disabled=false;
  }
}
function renderSteps(arr){
  if(!Array.isArray(arr))arr=[String(arr||'Call 911 now.')];
  const box=$('steps');box.innerHTML='';
  $('taphint').style.display=arr.length>1?'block':'none';
  arr.forEach((s,i)=>{
    const row=document.createElement('li');row.className='step';
    row.setAttribute('role','button');row.tabIndex=0;
    row.setAttribute('aria-label','Step '+(i+1)+': '+s+'. Tap to hear again.');
    row.innerHTML=`<div class="num" aria-hidden="true">${i+1}</div><div class="txt">${s}</div>`;
    const say=()=>{buzz(8);speakRaw(s);announce('Step '+(i+1));row.classList.add('flash');setTimeout(()=>row.classList.remove('flash'),700);};
    row.onclick=say;
    row.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();say();}};
    box.appendChild(row);
    if(REDUCED)row.classList.add('in');else setTimeout(()=>row.classList.add('in'),130*i);
  });
}
function resetAll(){stopSpeech();hideListen();lastSpeak='';showScreen('home');$('txt').value='';$('txt').focus();announce('Ready.');}
$('go').onclick=()=>ask($('txt').value);
$('txt').addEventListener('keydown',e=>{if(e.key==='Enter')ask($('txt').value);});
$('repeat').onclick=()=>{if($('speakind').classList.contains('on'))stopSpeech();else if(lastSpeak)speak(lastSpeak);};
$('retry').onclick=()=>{if(lastQuery)ask(lastQuery);};
$('reset').onclick=resetAll;$('back').onclick=resetAll;
document.addEventListener('keydown',e=>{if(e.key==='Escape'){stopSpeech();if($('listen').classList.contains('on'))hideListen();}});

// immersive listening
function showListen(){$('partial').textContent='';$('listen').classList.add('on');}
function hideListen(){$('listen').classList.remove('on');try{$('mic').focus();}catch(e){}}
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
if(SR){const rec=new SR();rec.lang='en-US';rec.interimResults=true;const m=$('mic');let finalT='';let cancelled=false;
 m.onclick=()=>{try{finalT='';cancelled=false;buzz(20);rec.start();m.classList.add('listening');$('miclbl').textContent='listening…';showListen();announce('Listening.');}catch(e){}};
 $('listenX').onclick=()=>{cancelled=true;try{rec.stop();}catch(e){}hideListen();};
 rec.onresult=e=>{let txt='';for(let i=0;i<e.results.length;i++)txt+=e.results[i][0].transcript;$('partial').textContent=txt;
   if(e.results[e.results.length-1].isFinal){finalT=txt;}};
 rec.onerror=()=>{m.classList.remove('listening');$('miclbl').textContent='Tap & speak';hideListen();announce('Speech recognition failed. Please type instead.');};
 rec.onend=()=>{m.classList.remove('listening');$('miclbl').textContent='Tap & speak';hideListen();const t=($('partial').textContent||finalT).trim();if(!cancelled&&t)ask(t);cancelled=false;};
}else{const m=$('mic');m.querySelector('#miclbl').textContent='Type below';m.disabled=true;m.style.opacity=.5;}

// PWA
if('serviceWorker' in navigator){window.addEventListener('load',()=>{navigator.serviceWorker.register('/sw.js').catch(()=>{});});}
</script></body></html>
"""
