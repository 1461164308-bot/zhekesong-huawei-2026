"""Liquid glass design adapted from the user's harmony-liquid-glass reference.

Scoped to this studio; no remote fonts/assets or imitation system controls.
"""

DESKTOP_HTML = r"""
<div class="zh-liquid-aurora" aria-hidden="true"><span></span><span></span><span></span><span></span></div>
<div class="zh-liquid-cursor" aria-hidden="true"></div>
<section id="zh-desktop" data-ready="false" aria-label="知衡液态玻璃创作空间">
  <header class="zh-liquid-topbar zh-liquid">
    <a class="zh-liquid-brand" href="#zh-app-title"><span>知</span>知衡 <small>创作空间</small></a>
    <nav aria-label="工作台导航"><a href="#zh-inputs">需求与风格</a><a href="#zh-plan-title">创作思路</a><a href="#zh-results">图文交付</a></nav>
    <span class="zh-liquid-local">本地预审版</span>
  </header>
  <div class="zh-liquid-hero">
    <div class="zh-liquid-copy zh-liquid zh-liquid-tilt">
      <span class="zh-liquid-eyebrow">ZHIHENG · YOUR CREATIVE SPACE</span>
      <h1>让每一篇内容，<br>都有你的风格。</h1>
      <p>从你喜欢的表达开始，先确认思路，再让有据可循的文字与图片，在合适的平台自然呈现。</p>
      <div class="zh-liquid-actions"><a href="#zh-inputs" class="zh-liquid-primary">开始创作 <span aria-hidden="true">↗</span></a><a href="#zh-style-title" class="zh-liquid-secondary">定义我的风格</a></div>
    </div>
    <aside class="zh-liquid-control zh-liquid zh-liquid-tilt" aria-label="创作控制中心">
      <div class="zh-liquid-control-head"><span>创作控制中心</span><span data-zh-date>正在读取日期</span></div>
      <div class="zh-liquid-time"><time aria-label="本地时间"><span data-zh-hours>--</span><span class="zh-liquid-colon">:</span><span data-zh-minutes>--</span><small data-zh-seconds>--</small></time><span>每一步，由你决定。</span></div>
      <nav class="zh-liquid-controls" aria-label="创作步骤快捷入口">
        <a href="#zh-inputs" class="active"><span class="zh-liquid-icon">01</span><span><b>确认需求</b><small>从真实任务出发</small></span></a>
        <a href="#zh-style-title"><span class="zh-liquid-icon">02</span><span><b>我的风格</b><small>选择 · 提炼 · 保存</small></span></a>
        <a href="#zh-plan-title"><span class="zh-liquid-icon">03</span><span><b>创作思路</b><small>先修改，再确认</small></span></a>
        <a href="#zh-results"><span class="zh-liquid-icon">04</span><span><b>图文终稿</b><small>平台排版与交付</small></span></a>
      </nav>
    </aside>
  </div>
</section>
"""

DESKTOP_CSS = r"""
:root { --zh-glass-blue:#0a59f7;--zh-glass-soft:#4c8dff;--zh-glass-ink:#16233f;--zh-mx:50%;--zh-my:40%;--zh-px:0px;--zh-py:0px; }
html { scroll-behavior:smooth;scroll-padding-top:22px; }
body, body.dark { background:#dbe8fb !important;background-image:linear-gradient(160deg,#e9f1fe 0%,#cfe0fb 55%,#c2d6f7 100%) !important;background-attachment:fixed !important; }
.gradio-container { --zh-navy:#16233f;--zh-teal:#0a59f7;--zh-muted:#50617c;--zh-border:#ffffffb3;--body-text-color:#16233f;--body-text-color-subdued:#50617c;--block-background-fill:#ffffff62;--block-border-color:#ffffffb3;--input-background-fill:#ffffff80;--input-border-color:#ffffffbb;--input-border-color-focus:#4c8dff;--button-primary-background-fill:#0a59f7;--button-primary-background-fill-hover:#0649d4;--button-primary-border-color:#ffffff55;--button-primary-text-color:white;--background-fill-primary:transparent;--background-fill-secondary:#ffffff70;--color-accent:#0a59f7;--link-text-color:#0a59f7;background:transparent !important;color:#16233f !important;isolation:isolate;padding:26px 28px 30px !important;font-family:"HarmonyOS Sans SC","PingFang SC","Microsoft YaHei",sans-serif !important; }
.gradio-container .html-container { background:transparent;border:0; }
.zh-liquid-aurora { position:fixed;inset:-8%;z-index:-1;pointer-events:none;overflow:hidden;transform:translate(var(--zh-px),var(--zh-py));transition:transform .5s ease; }
.zh-liquid-aurora span { position:absolute;display:block;border-radius:50%;filter:blur(64px);opacity:.57;animation:zh-liquid-flow 29s ease-in-out infinite; }
.zh-liquid-aurora span:nth-child(1) { width:56vw;height:56vw;left:-8vw;top:-13vw;background:radial-gradient(circle,#a9c8ff,transparent 68%); }
.zh-liquid-aurora span:nth-child(2) { width:48vw;height:48vw;right:-8vw;top:0;background:radial-gradient(circle,#c3bdf5,transparent 68%);animation-duration:32s;animation-direction:reverse; }
.zh-liquid-aurora span:nth-child(3) { width:46vw;height:46vw;left:38vw;bottom:-12vw;background:radial-gradient(circle,#a6e4ee,transparent 68%);animation-duration:26s; }
.zh-liquid-aurora span:nth-child(4) { width:34vw;height:34vw;left:12vw;top:30vh;background:radial-gradient(circle,#b2ccff,transparent 70%);animation-duration:36s;animation-direction:reverse; }
.zh-liquid-cursor { position:fixed;inset:0;z-index:-1;pointer-events:none;background:radial-gradient(280px circle at var(--zh-mx) var(--zh-my),#78a0ff2e,transparent 70%); }
@keyframes zh-liquid-flow { 0%,100% { transform:translate(0,0) scale(1); } 35% { transform:translate(6vw,4vw) scale(1.12); } 70% { transform:translate(-4vw,-6vw) scale(.95); } }
#zh-desktop { margin:0 0 24px;color:#16233f; }
#zh-desktop *,#zh-desktop *::before,#zh-desktop *::after { box-sizing:border-box; }
#zh-desktop a { text-decoration:none; }
.zh-liquid { position:relative;background:linear-gradient(150deg,#ffffff9e,#ffffff57);backdrop-filter:blur(28px) saturate(150%);-webkit-backdrop-filter:blur(28px) saturate(150%);border:1px solid #ffffffb3;box-shadow:0 20px 46px #2850a02e,inset 0 1px 1px #ffffffe6,inset 0 -1px 2px #7896d21f;overflow:hidden; }
.zh-liquid::before,.zh-liquid::after { content:"";position:absolute;inset:0;pointer-events:none;border-radius:inherit;z-index:0; }
.zh-liquid::before { background:linear-gradient(135deg,#ffffff70,transparent 44%);opacity:.6; }
.zh-liquid::after { background:radial-gradient(240px circle at var(--zh-lx,50%) var(--zh-ly,50%),#ffffff61,transparent 60%);opacity:0;transition:opacity .3s ease; }
.zh-liquid:hover::after { opacity:1; }
.zh-liquid > * { position:relative;z-index:1; }
.zh-liquid-tilt { transition:transform .25s ease;transform:perspective(1100px) rotateX(var(--zh-rx,0deg)) rotateY(var(--zh-ry,0deg)); }
.zh-liquid-topbar { display:flex;align-items:center;justify-content:space-between;gap:16px;padding:15px 24px;border-radius:999px;margin-bottom:22px; }
.zh-liquid-brand { display:flex;align-items:center;gap:10px;color:#16233f !important;font-size:20px;font-weight:650;letter-spacing:.3px; }
.zh-liquid-brand > span { display:grid;place-items:center;width:32px;height:32px;border-radius:10px;color:white;font-size:17px;background:linear-gradient(135deg,#0a59f7,#4c8dff);box-shadow:0 4px 14px #0a59f745,inset 0 1px 1px #ffffffb3; }
.zh-liquid-brand small { font-size:12px;font-weight:400;color:#50617c; }
.zh-liquid-topbar nav { display:flex;gap:5px; }
.zh-liquid-topbar nav a { padding:9px 18px;border-radius:999px;color:#50617c;font-size:13px;transition:background .2s; }
.zh-liquid-topbar nav a:hover { color:#0a59f7;background:#ffffffb3; }
.zh-liquid-local { padding:8px 14px;color:#0a59f7;background:#ffffff80;border:1px solid #ffffffb3;border-radius:999px;font-size:11px;white-space:nowrap; }
.zh-liquid-hero { display:grid;grid-template-columns:1.15fr .85fr;gap:22px;align-items:stretch; }
.zh-liquid-copy { padding:36px 40px;border-radius:34px;display:flex;flex-direction:column;justify-content:center; }
.zh-liquid-eyebrow { font-size:10px;font-weight:600;letter-spacing:.12em;color:#0a59f7;display:flex;align-items:center;gap:8px; }
.zh-liquid-eyebrow::before { content:"";width:6px;height:6px;border-radius:50%;background:#0a59f7;box-shadow:0 0 12px #0a59f780; }
.zh-liquid-copy h1 { font-size:clamp(28px,3.1vw,42px);line-height:1.35;font-weight:700;letter-spacing:-.5px;margin:16px 0 14px;color:#16233f; }
.zh-liquid-copy p { color:#50617c;font-size:14px;line-height:1.85;max-width:40ch;margin:0 0 23px; }
.zh-liquid-actions { display:flex;gap:12px;flex-wrap:wrap; }
.zh-liquid-actions a { padding:13px 23px;border-radius:999px;font-size:13px;font-weight:600;transition:transform .2s,box-shadow .2s; }
.zh-liquid-primary { color:#fff !important;background:linear-gradient(135deg,#0a59f7,#4c8dff);box-shadow:0 10px 24px #0a59f740,inset 0 1px 1px #ffffff80; }
.zh-liquid-primary span { margin-left:12px; }
.zh-liquid-secondary { color:#16233f !important;background:#ffffff80;border:1px solid #ffffffcc; }
.zh-liquid-actions a:hover { transform:translateY(-2px); }
.zh-liquid-control { padding:24px;border-radius:34px;display:flex;flex-direction:column;gap:17px; }
.zh-liquid-control-head { display:flex;justify-content:space-between;gap:10px;font-size:11px;color:#50617c; }
.zh-liquid-time { display:flex;align-items:center;justify-content:space-between;gap:15px; }
.zh-liquid-time time { display:flex;align-items:baseline;font-variant-numeric:tabular-nums;white-space:nowrap;font-size:clamp(42px,4.3vw,65px);line-height:1.1;letter-spacing:-.04em;font-weight:260; }
.zh-liquid-time time small { font-size:16px;letter-spacing:0;margin-left:8px;color:#5d7297; }
.zh-liquid-time > span { font-size:11px;color:#50617c; }
.zh-liquid-colon { margin:0 3px; }
.zh-liquid-controls { display:grid;grid-template-columns:1fr 1fr;gap:12px; }
.zh-liquid-controls a { display:flex;gap:10px;align-items:center;padding:14px 12px;background:#ffffff73;border:1px solid #ffffffb3;box-shadow:inset 0 1px 1px #ffffffcc;border-radius:20px;color:#16233f;transition:background .2s,transform .2s; }
.zh-liquid-controls a:hover { background:#ffffffb3;transform:translateY(-2px); }
.zh-liquid-controls a.active { background:linear-gradient(135deg,#0a59f7f2,#4c8dffe6);border-color:transparent;color:white;box-shadow:0 8px 20px #0a59f72e,inset 0 1px 1px #ffffff80; }
.zh-liquid-icon { width:33px;height:33px;border-radius:11px;background:#7896d224;display:grid;place-items:center;font-size:12px;font-weight:600;flex-shrink:0; }
.zh-liquid-controls .active .zh-liquid-icon { background:#ffffff42; }
.zh-liquid-controls b { display:block;font-size:12px;font-weight:600; }
.zh-liquid-controls small { display:block;margin-top:4px;font-size:10px;color:#50617c; }
.zh-liquid-controls .active small { color:#ffffffe6; }
#zh-inputs,#zh-results { position:relative;background:linear-gradient(150deg,#ffffff9e,#ffffff70) !important;backdrop-filter:blur(28px) saturate(150%);-webkit-backdrop-filter:blur(28px) saturate(150%);border:1px solid #ffffffb3 !important;box-shadow:0 20px 46px #2850a020,inset 0 1px 1px #ffffffe6 !important;border-radius:30px !important;padding:25px !important; }
#zh-connection { background:#ffffff70 !important;backdrop-filter:blur(20px);border-color:#ffffffb3 !important;border-radius:22px !important;padding:4px 10px;box-shadow:0 6px 20px #2850a00c; }
#zh-status { background:linear-gradient(135deg,#f6f9ffdb,#e7f0ff9e) !important;border:1px solid #ffffffcc !important;border-radius:22px !important;padding:17px 19px !important; }
#zh-status p,#zh-status h3 { color:#22447c !important; }
#zh-app-title h2 { font-size:20px;color:#16233f; }
#zh-guide { color:#50617c !important; }
.gradio-container button.primary,#zh-generate { background:linear-gradient(135deg,#0a59f7,#4c8dff) !important;color:#fff !important;box-shadow:0 7px 18px #0a59f72e,inset 0 1px 1px #ffffff80 !important;border:1px solid #ffffff66 !important;border-radius:999px !important;min-height:43px; }
.gradio-container button.primary:hover,#zh-generate:hover { background:linear-gradient(135deg,#0649d4,#3979ef) !important; }
.gradio-container button.primary:disabled,#zh-generate:disabled { opacity:.45 !important;box-shadow:none !important; }
.gradio-container button.secondary,#zh-examples button { color:#23446f;background:#ffffff80 !important;border:1px solid #ffffffcc !important;border-radius:999px !important;box-shadow:inset 0 1px 1px #ffffffe6; }
.gradio-container textarea,.gradio-container input { color:#16233f !important;background:#ffffff80 !important;border-radius:15px !important; }
.gradio-container textarea::placeholder,.gradio-container input::placeholder { color:#62748d !important; }
.gradio-container textarea:focus,.gradio-container input:focus { outline:2px solid #4c8dff88 !important;outline-offset:1px; }
.gradio-container .block { border-color:#ffffffaa !important;border-radius:18px !important;background:#ffffff3d; }
#zh-tabs .tab-nav button.selected { color:#0a59f7 !important;border-bottom-color:#0a59f7 !important;background:#ffffff80; }
#zh-report h2,#zh-report h3 { color:#1b4d9b; }
#zh-preview { overflow:auto; }
#zh-preview article { border-radius:18px; }
#zh-footer { color:#50617c !important; }
#zh-desktop a:focus-visible,.gradio-container button:focus-visible { outline:3px solid #0a59f7 !important;outline-offset:3px; }
@media(max-width:960px) { .zh-liquid-copy { padding:30px; } .zh-liquid-control { padding:22px; } .zh-liquid-time > span { display:none; } }
@media(max-width:760px) { .zh-liquid-hero { grid-template-columns:1fr;gap:16px; } .zh-liquid-topbar nav { display:none; } .zh-liquid-copy { padding:28px;border-radius:28px; } .zh-liquid-copy h1 { font-size:33px; } .zh-liquid-control { border-radius:28px; } .zh-liquid-time time { font-size:54px; } .zh-liquid-time > span { display:block; } .zh-liquid-controls { gap:10px; } #zh-inputs,#zh-results { padding:18px !important;border-radius:25px !important; } .gradio-container { padding:16px 12px 24px !important; } .zh-liquid-aurora span { filter:blur(40px); } }
@media(max-width:400px) { .zh-liquid-topbar { padding:13px 16px; } .zh-liquid-brand { font-size:18px;gap:8px; } .zh-liquid-brand small { font-size:10px; } .zh-liquid-copy h1 { font-size:29px; } .zh-liquid-copy { padding:25px; } .zh-liquid-controls a { padding:12px 9px;gap:8px; } .zh-liquid-controls small { font-size:9px; } }
@media(prefers-reduced-motion:reduce) { html { scroll-behavior:auto; } .zh-liquid-aurora span { animation:none !important; } .zh-liquid-aurora,.zh-liquid-tilt,.zh-liquid-actions a,.zh-liquid-controls a { transition:none !important;transform:none !important; } .zh-liquid-cursor { display:none; } }
html[data-zh-hidden="true"] .zh-liquid-aurora span { animation-play-state:paused; }
"""

DESKTOP_JS = r"""
() => {
  const key = '__zhihengDesktopRuntime';
  if (window[key]?.dispose) window[key].dispose();
  const runtime = { disposed:false, root:null };
  window[key] = runtime;
  window.__zhiheng_visual_ready = false;
  const cleanups = [];
  let clockTimer = 0, frame = 0, observer = null, timeout = 0;
  const html = document.documentElement;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const fine = window.matchMedia('(pointer: fine)');
  const listen = (target, type, callback, opts) => {
    target.addEventListener(type, callback, opts);
    cleanups.push(() => target.removeEventListener(type, callback, opts));
  };
  const stopObserver = () => { observer?.disconnect(); observer = null; clearTimeout(timeout); };
  runtime.dispose = () => {
    runtime.disposed = true; stopObserver(); clearTimeout(clockTimer); cancelAnimationFrame(frame);
    cleanups.splice(0).forEach(fn => fn());
    if (runtime.root) runtime.root.dataset.ready = 'false';
    window.__zhiheng_visual_ready = false;
  };
  const init = () => {
    const root = document.getElementById('zh-desktop');
    if (!root || runtime.disposed) return false;
    const hours = root.querySelector('[data-zh-hours]'), minutes = root.querySelector('[data-zh-minutes]');
    const seconds = root.querySelector('[data-zh-seconds]'), date = root.querySelector('[data-zh-date]');
    if (!hours || !minutes || !seconds || !date) return false;
    stopObserver(); runtime.root = root;
    const pad = n => String(n).padStart(2,'0');
    const updateClock = () => {
      clearTimeout(clockTimer);
      if (runtime.disposed || document.hidden) return;
      if (!root.isConnected) { runtime.dispose(); return; }
      const now = new Date();
      hours.textContent = pad(now.getHours()); minutes.textContent = pad(now.getMinutes()); seconds.textContent = pad(now.getSeconds());
      date.textContent = new Intl.DateTimeFormat('zh-CN',{month:'long',day:'numeric',weekday:'short'}).format(now);
      const time = root.querySelector('time');
      time.dateTime = now.toISOString(); time.setAttribute('aria-label','本地时间 '+pad(now.getHours())+':'+pad(now.getMinutes()));
      clockTimer = setTimeout(updateClock,1020-Date.now()%1000);
    };
    let pending = null;
    listen(document,'pointermove',event => {
      if (document.hidden || reduced.matches || !fine.matches || event.pointerType === 'touch') return;
      pending = {x:event.clientX,y:event.clientY,target:event.target};
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        if (!pending || runtime.disposed || document.hidden) return;
        const {x,y,target} = pending;
        html.style.setProperty('--zh-mx',x/innerWidth*100+'%'); html.style.setProperty('--zh-my',y/innerHeight*100+'%');
        html.style.setProperty('--zh-px',(-(x/innerWidth-.5)*20).toFixed(1)+'px');
        html.style.setProperty('--zh-py',(-(y/innerHeight-.5)*20).toFixed(1)+'px');
        const card = target instanceof Element ? target.closest('#zh-desktop .zh-liquid') : null;
        if (card) {
          const r = card.getBoundingClientRect();
          card.style.setProperty('--zh-lx',(x-r.left)+'px'); card.style.setProperty('--zh-ly',(y-r.top)+'px');
          if (card.classList.contains('zh-liquid-tilt')) {
            card.style.setProperty('--zh-ry',((x-r.left)/r.width-.5)*3+'deg');
            card.style.setProperty('--zh-rx',((y-r.top)/r.height-.5)*-3+'deg');
          }
        }
      });
    },{passive:true});
    root.querySelectorAll('.zh-liquid-tilt').forEach(card => listen(card,'pointerleave',() => {
      card.style.setProperty('--zh-rx','0deg');card.style.setProperty('--zh-ry','0deg');
    },{passive:true}));
    const sync = () => {
      html.dataset.zhHidden = document.hidden ? 'true':'false';
      if (document.hidden) { clearTimeout(clockTimer); cancelAnimationFrame(frame);frame=0; }
      else updateClock();
    };
    listen(document,'visibilitychange',sync);
    listen(window,'pagehide',() => { clearTimeout(clockTimer);cancelAnimationFrame(frame);frame=0;html.dataset.zhHidden='true'; });
    listen(window,'pageshow',sync);
    sync(); root.dataset.ready='true';window.__zhiheng_visual_ready=true;
    return true;
  };
  if (!init()) {
    observer = new MutationObserver(init);
    observer.observe(document.body,{childList:true,subtree:true});
    timeout = setTimeout(stopObserver,10000);
  }
}
"""
