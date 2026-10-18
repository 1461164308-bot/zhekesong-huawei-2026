"""Original desktop-inspired header, with no remote assets or OS capability claims.

Integration (Gradio 6): gr.HTML(DESKTOP_HTML), then
launch(css=existing_css + DESKTOP_CSS, js=DESKTOP_JS).
"""

DESKTOP_HTML = r"""
<section id="zh-desktop" class="zh-space-desktop" aria-label="知衡原创空间桌面" data-ready="false">
  <div class="zh-space-wallpaper" aria-hidden="true">
    <div class="zh-space-light zh-space-light-a"></div>
    <div class="zh-space-light zh-space-light-b"></div>
    <div class="zh-space-floor"></div>
    <div class="zh-space-orbit-scene">
      <div class="zh-space-orbit zh-space-orbit-a"></div>
      <div class="zh-space-orbit zh-space-orbit-b"></div>
      <div class="zh-space-orbit zh-space-orbit-c"></div>
      <div class="zh-space-sphere"></div>
      <div class="zh-space-pearl zh-space-pearl-a"></div>
      <div class="zh-space-pearl zh-space-pearl-b"></div>
      <div class="zh-space-glass-panel zh-space-glass-a"></div>
      <div class="zh-space-glass-panel zh-space-glass-b"></div>
    </div>
    <canvas class="zh-space-particles"></canvas>
    <div class="zh-space-grain"></div>
  </div>
  <div class="zh-space-topbar">
    <span class="zh-space-wordmark"><span class="zh-space-mark" aria-hidden="true">知</span>知衡空间 <span class="zh-space-en">/ ZHIHENG SPACE</span></span>
    <span class="zh-space-label"><span aria-hidden="true"></span>原创桌面概念</span>
  </div>
  <div class="zh-space-clock-strip">
    <div class="zh-space-clock-face">
      <span class="zh-space-clock-kicker">让每一次创作，都有据可循</span>
      <time class="zh-space-clock" aria-label="当地时间，正在读取" aria-live="off"><span data-zh-hours>--</span><span class="zh-space-colon">:</span><span data-zh-minutes>--</span><span class="zh-space-seconds" data-zh-seconds>--</span></time>
    </div>
    <div class="zh-space-calendar"><span data-zh-date>正在读取本地时间</span><span class="zh-space-zone" data-zh-zone>跟随设备时区</span></div>
  </div>
  <div class="zh-space-caption">
    <span class="zh-space-overline">KNOWLEDGE · CREATE · VERIFY</span>
    <h2>把知识，放进创作空间。</h2>
    <p>华为 PC 图文营销，从一份有来源的需求开始。</p>
  </div>
  <nav class="zh-space-dock" aria-label="营销工作区快捷入口">
    <a class="zh-space-app" href="#zh-inputs"><span class="zh-space-app-icon zh-space-icon-create" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg></span><span>新建方案<small>描述需求</small></span><span class="zh-space-app-arrow" aria-hidden="true">↗</span></a>
    <a class="zh-space-app" href="#zh-results"><span class="zh-space-app-icon zh-space-icon-layout" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><rect x="4.5" y="4.5" width="15" height="15" rx="3" stroke="currentColor" stroke-width="1.5"/><path d="M4.5 10h15M11 10v9.5" stroke="currentColor" stroke-width="1.5"/></svg></span><span>图文工作台<small>预览与交付</small></span><span class="zh-space-app-arrow" aria-hidden="true">↗</span></a>
    <a class="zh-space-app" href="#zh-connection"><span class="zh-space-app-icon zh-space-icon-check" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M12 3.5 19 6v5.5c0 4-3.7 7.5-7 9-3.3-1.5-7-5-7-9V6l7-2.5Z" stroke="currentColor" stroke-width="1.5"/><path d="m8.5 11.5 2.5 2.5 4.5-5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg></span><span>连接状态<small>知识库与模型</small></span><span class="zh-space-app-arrow" aria-hidden="true">↗</span></a>
  </nav>
  <p class="zh-space-disclaimer">鸿蒙 7 桌面灵感 · 原创视觉概念，非华为操作系统或官方功能演示</p>
</section>
"""

DESKTOP_CSS = r"""
#zh-desktop {
  --zh-dx: 0px; --zh-dy: 0px;
  position: relative; isolation: isolate; overflow: hidden; box-sizing: border-box;
  min-height: 472px; width: 100%; padding: 25px 34px 19px; margin: 0 0 17px;
  border-radius: 25px; border: 1px solid #ddedf2; color: #123c52;
  background: #e7f1f5; box-shadow: 0 14px 36px #153c4b0c;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
  contain: layout style;
}
#zh-desktop *, #zh-desktop *::before, #zh-desktop *::after { box-sizing: border-box; }
#zh-desktop .zh-space-wallpaper { position: absolute; inset: 0; z-index: -1; pointer-events: none; overflow: hidden; background: radial-gradient(ellipse at 66% 50%, #f4fffd 0%, #e9f7f7 24%, transparent 59%), linear-gradient(118deg, #dceaf4 0%, #e2f2f5 46%, #b9d9dc 100%); }
#zh-desktop .zh-space-light { position: absolute; border-radius: 50%; filter: blur(44px); opacity: .7; }
#zh-desktop .zh-space-light-a { width: 400px; height: 240px; top: -110px; right: 5%; background: #ffffff; transform: translate(var(--zh-dx), var(--zh-dy)); }
#zh-desktop .zh-space-light-b { width: 330px; height: 220px; bottom: -120px; left: 20%; background: #a6dcd4; }
#zh-desktop .zh-space-floor { position: absolute; width: 1100px; height: 450px; right: -290px; bottom: -315px; border-radius: 50%; background: radial-gradient(ellipse, #35748633, #71afa316 42%, transparent 66%); transform: rotate(-13deg); }
#zh-desktop .zh-space-orbit-scene { position: absolute; width: 500px; height: 410px; right: 17px; top: 11px; perspective: 950px; transform-style: preserve-3d; transform: translate(calc(var(--zh-dx) * -1), calc(var(--zh-dy) * -1)); }
#zh-desktop .zh-space-orbit { position: absolute; left: 98px; top: 50px; width: 285px; height: 285px; border-radius: 50%; transform-style: preserve-3d; box-shadow: inset 0 0 12px #ffffffa6, 0 9px 15px #32687a12; }
#zh-desktop .zh-space-orbit-a { border: 26px solid #87bdca; background: linear-gradient(130deg, #fff7, #ffffff05); transform: translateZ(15px) rotateY(-31deg) rotateX(58deg) rotateZ(-22deg); border-left-color: #c3e1e7; border-top-color: #f0ffff; border-right-color: #5394a6; }
#zh-desktop .zh-space-orbit-b { width: 250px; height: 250px; left: 115px; top: 64px; border: 19px solid #b8e3db; transform: translateZ(42px) rotateY(41deg) rotateX(-25deg) rotateZ(32deg); border-left-color: #eafffa; border-bottom-color: #64a99f; box-shadow: inset 1px 2px 8px #fff9, 8px 12px 20px #396f7715; }
#zh-desktop .zh-space-orbit-c { width: 356px; height: 356px; left: 63px; top: 15px; border: 1px solid #ffffffbd; transform: rotateY(39deg) rotateX(69deg) rotateZ(-27deg); box-shadow: 0 0 0 7px #ffffff12; }
#zh-desktop .zh-space-sphere { position: absolute; top: 127px; left: 189px; width: 114px; height: 114px; border-radius: 50%; background: radial-gradient(circle at 31% 24%, #fbffff 2%, #e6fafa 18%, #83c0c6 48%, #2d778c 82%, #22556e); box-shadow: inset -8px -7px 15px #24506c25, 13px 22px 30px #306c7926; transform: translateZ(90px); }
#zh-desktop .zh-space-pearl { position: absolute; border-radius: 50%; box-shadow: 8px 12px 15px #3c73782c; }
#zh-desktop .zh-space-pearl-a { width: 33px; height: 33px; top: 60px; left: 315px; background: radial-gradient(circle at 30% 25%, #fff 5%, #cae9dc 28%, #529b9b 83%); transform: translateZ(75px); }
#zh-desktop .zh-space-pearl-b { width: 20px; height: 20px; top: 273px; left: 101px; background: radial-gradient(circle at 30% 25%, #fff 6%, #b5d8ec 30%, #5388aa 80%); transform: translateZ(60px); }
#zh-desktop .zh-space-glass-panel { position: absolute; border: 1px solid #ffffffaa; border-radius: 21px; background: linear-gradient(135deg, #ffffff61, #def5f026); box-shadow: 0 12px 25px #205a6a0c; }
#zh-desktop .zh-space-glass-a { width: 110px; height: 100px; right: 19px; top: 202px; transform: rotate(-21deg) rotateY(-25deg) translateZ(20px); }
#zh-desktop .zh-space-glass-b { width: 62px; height: 62px; left: 42px; top: 76px; border-radius: 16px; transform: rotate(17deg) rotateY(20deg) translateZ(5px); }
#zh-desktop .zh-space-particles { position: absolute; width: 100%; height: 100%; inset: 0; pointer-events: none; opacity: .8; }
#zh-desktop .zh-space-grain { position: absolute; inset: 0; background: linear-gradient(110deg, #ffffff38, transparent 60%, #186a7910); }
#zh-desktop .zh-space-topbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; position: relative; z-index: 1; }
#zh-desktop .zh-space-wordmark { display: inline-flex; align-items: center; gap: 9px; font-size: 14px; font-weight: 650; letter-spacing: .04em; }
#zh-desktop .zh-space-mark { display: inline-grid; width: 27px; height: 27px; place-items: center; background: linear-gradient(145deg, #2f7183, #137c7c); border: 1px solid #ffffffb0; border-radius: 8px; color: #fff; font-size: 14px; box-shadow: 0 3px 7px #174c6320; }
#zh-desktop .zh-space-en { font-size: 9px; letter-spacing: .13em; color: #507786; font-weight: 500; margin-left: 3px; }
#zh-desktop .zh-space-label { display: inline-flex; align-items: center; gap: 6px; color: #416b79; padding: 5px 10px; background: #ffffff61; border: 1px solid #ffffff9c; border-radius: 30px; font-size: 10px; }
#zh-desktop .zh-space-label > span { width: 5px; height: 5px; border-radius: 50%; background: #2f9890; }
#zh-desktop .zh-space-clock-strip { display: flex; align-items: center; gap: 25px; position: relative; z-index: 1; width: min(690px, 70%); margin-top: 27px; padding: 10px 21px 13px; border-radius: 18px; background: linear-gradient(100deg, #ffffff70, #ffffff36); border: 1px solid #ffffffb5; box-shadow: 0 8px 22px #235a6c06; }
#zh-desktop .zh-space-clock-face { min-width: 0; }
#zh-desktop .zh-space-clock-kicker { display: block; font-size: 10px; letter-spacing: .13em; color: #547d89; margin: 0 0 0 4px; }
#zh-desktop .zh-space-clock { display: flex; align-items: baseline; color: #193f56; font-size: clamp(58px, 6.7vw, 92px); font-weight: 260; line-height: 1.1; letter-spacing: -.065em; font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; white-space: nowrap; }
#zh-desktop .zh-space-colon { display: inline-block; margin: 0 .035em; transform: translateY(-.035em); }
#zh-desktop .zh-space-seconds { font-size: .28em; font-weight: 400; color: #4a8190; letter-spacing: .015em; margin-left: 13px; min-width: 1.25em; }
#zh-desktop .zh-space-calendar { display: flex; flex-direction: column; gap: 9px; font-size: 12px; color: #285b6c; line-height: 1.4; border-left: 1px solid #6e9eaa38; padding-left: 22px; white-space: nowrap; }
#zh-desktop .zh-space-zone { font-size: 9px; letter-spacing: .035em; color: #658995; max-width: 160px; overflow: hidden; text-overflow: ellipsis; }
#zh-desktop .zh-space-caption { margin: 24px 0 23px 4px; position: relative; z-index: 1; }
#zh-desktop .zh-space-overline { font-size: 8px; letter-spacing: .2em; color: #447e88; }
#zh-desktop .zh-space-caption h2 { margin: 7px 0 7px; font-size: clamp(20px, 2.4vw, 27px); line-height: 1.4; color: #153e52; font-weight: 600; letter-spacing: .055em; }
#zh-desktop .zh-space-caption p { margin: 0; font-size: 12px; color: #507482; line-height: 1.7; }
#zh-desktop .zh-space-dock { position: relative; z-index: 2; display: flex; align-items: stretch; gap: 10px; width: min(700px, 100%); padding: 9px; background: #f9ffff4f; border: 1px solid #ffffffbd; border-radius: 20px; box-shadow: 0 9px 20px #3e718611; }
#zh-desktop .zh-space-app { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; padding: 8px 10px 8px 8px; border-radius: 13px; background: #ffffff7d; border: 1px solid #ffffffa8; color: #224f62; text-decoration: none; transition: transform 180ms ease, box-shadow 180ms ease, background 180ms ease; }
#zh-desktop .zh-space-app:hover { background: #ffffffe6; box-shadow: 0 5px 12px #30677516; transform: translateY(-3px); }
#zh-desktop .zh-space-app:focus-visible { outline: 3px solid #087e83; outline-offset: 4px; background: #fff; }
#zh-desktop .zh-space-app > span:nth-child(2) { display: flex; flex-direction: column; gap: 4px; font-size: 11px; font-weight: 600; white-space: nowrap; }
#zh-desktop .zh-space-app small { color: #62818d; font-size: 9px; font-weight: 400; }
#zh-desktop .zh-space-app-icon { display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; width: 36px; height: 36px; border-radius: 11px; color: #fff; box-shadow: inset 0 1px 1px #ffffff61, 0 4px 7px #2e64731a; }
#zh-desktop .zh-space-app-icon svg { width: 23px; height: 23px; }
#zh-desktop .zh-space-icon-create { background: linear-gradient(145deg, #49bcb4, #168886); }
#zh-desktop .zh-space-icon-layout { background: linear-gradient(145deg, #75b1db, #3e7ba8); }
#zh-desktop .zh-space-icon-check { background: linear-gradient(145deg, #8ebeb5, #4d8e85); }
#zh-desktop .zh-space-app-arrow { font-size: 12px; color: #6f929e; margin-left: auto; }
#zh-desktop .zh-space-disclaimer { margin: 13px 3px 0; font-size: 9px; color: #496c7a; line-height: 1.6; position: relative; z-index: 1; }
#zh-desktop[data-motion="reduced"] .zh-space-orbit-scene, #zh-desktop[data-motion="reduced"] .zh-space-light-a { transform: none; }
#zh-desktop[data-motion="reduced"] .zh-space-particles { display: none; }
@media (max-width: 900px) {
  #zh-desktop { padding: 23px 23px 17px; }
  #zh-desktop .zh-space-clock-strip { width: 78%; gap: 17px; }
  #zh-desktop .zh-space-calendar { padding-left: 15px; font-size: 10px; }
  #zh-desktop .zh-space-orbit-scene { right: -110px; opacity: .72; }
}
@media (max-width: 600px) {
  #zh-desktop { min-height: 432px; padding: 19px 17px 15px; border-radius: 19px; }
  #zh-desktop .zh-space-en { display: none; }
  #zh-desktop .zh-space-wordmark { font-size: 12px; }
  #zh-desktop .zh-space-label { font-size: 8px; padding: 4px 7px; }
  #zh-desktop .zh-space-clock-strip { width: 100%; gap: 11px; padding: 12px 13px; margin-top: 24px; border-radius: 15px; }
  #zh-desktop .zh-space-clock { font-size: clamp(48px, 13vw, 73px); }
  #zh-desktop .zh-space-clock-kicker { font-size: 8px; letter-spacing: .02em; }
  #zh-desktop .zh-space-seconds { margin-left: 8px; }
  #zh-desktop .zh-space-calendar { gap: 7px; padding-left: 11px; font-size: 9px; }
  #zh-desktop .zh-space-zone { max-width: 88px; font-size: 7px; }
  #zh-desktop .zh-space-orbit-scene { right: -206px; top: 99px; opacity: .4; transform: scale(.75); }
  #zh-desktop .zh-space-caption { margin: 24px 0 22px 2px; }
  #zh-desktop .zh-space-caption h2 { font-size: 21px; }
  #zh-desktop .zh-space-caption p { font-size: 10px; max-width: 95%; }
  #zh-desktop .zh-space-dock { gap: 6px; padding: 6px; border-radius: 16px; }
  #zh-desktop .zh-space-app { flex-direction: column; align-items: center; gap: 7px; padding: 10px 3px 8px; text-align: center; border-radius: 11px; }
  #zh-desktop .zh-space-app > span:nth-child(2) { font-size: 10px; gap: 4px; }
  #zh-desktop .zh-space-app-icon { width: 33px; height: 33px; border-radius: 10px; }
  #zh-desktop .zh-space-app small { font-size: 8px; }
  #zh-desktop .zh-space-app-arrow { display: none; }
  #zh-desktop .zh-space-disclaimer { font-size: 8px; margin-top: 11px; }
}
@media (prefers-reduced-motion: reduce) {
  #zh-desktop .zh-space-particles { display: none; }
  #zh-desktop .zh-space-orbit-scene, #zh-desktop .zh-space-light-a { transform: none; }
  #zh-desktop .zh-space-app { transition: none; }
  #zh-desktop .zh-space-app:hover { transform: none; }
}
"""

DESKTOP_JS = r"""
() => {
  const key = '__zhihengDesktopRuntime';
  const previous = window[key];
  const currentRoot = document.getElementById('zh-desktop');
  if (previous && previous.root && previous.root === currentRoot && currentRoot.isConnected && currentRoot.dataset.ready === 'true') return;
  if (previous && typeof previous.dispose === 'function') previous.dispose();
  const runtime = { root: null, disposed: false };
  window[key] = runtime;
  window.__zhiheng_visual_ready = false;
  const cleanups = [];
  let observer = null, observerTimer = 0, clockTimer = 0, frame = 0, resizeFrame = 0;
  const stopObserver = () => {
    if (observer) { observer.disconnect(); observer = null; }
    clearTimeout(observerTimer); observerTimer = 0;
  };
  runtime.dispose = () => {
    if (runtime.disposed) return;
    runtime.disposed = true;
    stopObserver(); clearTimeout(clockTimer); cancelAnimationFrame(frame); cancelAnimationFrame(resizeFrame);
    cleanups.splice(0).forEach(fn => { try { fn(); } catch (_) {} });
    if (runtime.root) { runtime.root.dataset.ready = 'false'; runtime.root.style.removeProperty('--zh-dx'); runtime.root.style.removeProperty('--zh-dy'); }
    if (window[key] === runtime) window.__zhiheng_visual_ready = false;
  };
  const listen = (target, event, fn, options) => {
    target.addEventListener(event, fn, options);
    cleanups.push(() => target.removeEventListener(event, fn, options));
  };
  const init = () => {
    const root = document.getElementById('zh-desktop');
    if (!root || runtime.disposed) return false;
    stopObserver(); runtime.root = root;
    const hours = root.querySelector('[data-zh-hours]');
    const minutes = root.querySelector('[data-zh-minutes]');
    const seconds = root.querySelector('[data-zh-seconds]');
    const date = root.querySelector('[data-zh-date]');
    const zone = root.querySelector('[data-zh-zone]');
    const clock = root.querySelector('time');
    const canvas = root.querySelector('canvas');
    if (!hours || !minutes || !seconds || !date || !zone || !clock || !canvas) { runtime.dispose(); return false; }
    const context = canvas.getContext('2d', { alpha: true });
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    const fine = window.matchMedia('(pointer: fine)');
    let visible = !document.hidden, inViewport = true;
    let width = 1, height = 1, particles = [], lastFrame = 0;
    let pointerX = 0, pointerY = 0, renderedX = 0, renderedY = 0;
    const pad = value => String(value).padStart(2, '0');
    const zoneName = new Intl.DateTimeFormat().resolvedOptions().timeZone || '设备本地时间';
    zone.textContent = zoneName;
    const dateFormatter = new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' });
    const updateClock = () => {
      clearTimeout(clockTimer); clockTimer = 0;
      if (runtime.disposed || !visible) return;
      if (!root.isConnected) { runtime.dispose(); return; }
      const now = new Date();
      hours.textContent = pad(now.getHours()); minutes.textContent = pad(now.getMinutes()); seconds.textContent = pad(now.getSeconds());
      date.textContent = dateFormatter.format(now);
      clock.dateTime = now.toISOString();
      clock.setAttribute('aria-label', '当地时间 ' + pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds()) + '，' + zoneName);
      clockTimer = setTimeout(updateClock, 1020 - (Date.now() % 1000));
    };
    const resize = () => {
      resizeFrame = 0;
      if (runtime.disposed) return;
      const rect = root.getBoundingClientRect();
      width = Math.max(1, rect.width); height = Math.max(1, rect.height);
      const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
      if (context) context.setTransform(ratio, 0, 0, ratio, 0, 0);
      const count = width < 600 ? 12 : 25;
      particles = Array.from({ length: count }, () => ({ x: Math.random() * width, y: Math.random() * height, r: .7 + Math.random() * 1.5, speed: .08 + Math.random() * .18, drift: (Math.random() - .5) * .09, alpha: .15 + Math.random() * .35 }));
    };
    const scheduleResize = () => { if (!resizeFrame && !runtime.disposed && visible) resizeFrame = requestAnimationFrame(resize); };
    const active = () => !runtime.disposed && visible && inViewport && !reduced.matches && !!context;
    const draw = timestamp => {
      frame = 0;
      if (!active()) return;
      if (!root.isConnected) { runtime.dispose(); return; }
      if (timestamp - lastFrame >= 34) {
        const delta = Math.min(2, Math.max(.5, (timestamp - lastFrame) / 34)); lastFrame = timestamp;
        context.clearRect(0, 0, width, height);
        for (const p of particles) {
          p.y -= p.speed * delta; p.x += p.drift * delta;
          if (p.y < -5) { p.y = height + 5; p.x = Math.random() * width; }
          if (p.x < -5) p.x = width + 5; if (p.x > width + 5) p.x = -5;
          context.beginPath(); context.arc(p.x, p.y, p.r, 0, Math.PI * 2);
          context.fillStyle = 'rgba(245,255,255,' + p.alpha + ')'; context.fill();
        }
        const targetX = fine.matches ? pointerX : 0, targetY = fine.matches ? pointerY : 0;
        if (Math.abs(renderedX - targetX) > .03 || Math.abs(renderedY - targetY) > .03) {
          renderedX += (targetX - renderedX) * .12; renderedY += (targetY - renderedY) * .12;
          root.style.setProperty('--zh-dx', renderedX.toFixed(2) + 'px'); root.style.setProperty('--zh-dy', renderedY.toFixed(2) + 'px');
        }
      }
      frame = requestAnimationFrame(draw);
    };
    const syncMotion = () => {
      cancelAnimationFrame(frame); frame = 0; lastFrame = 0;
      root.dataset.motion = reduced.matches ? 'reduced' : 'enabled';
      root.dataset.paused = (!visible || !inViewport) ? 'true' : 'false';
      if (reduced.matches || !fine.matches) {
        pointerX = 0; pointerY = 0; renderedX = 0; renderedY = 0;
        root.style.setProperty('--zh-dx', '0px'); root.style.setProperty('--zh-dy', '0px');
      }
      if (active()) frame = requestAnimationFrame(draw);
      else if (context) context.clearRect(0, 0, width, height);
    };
    listen(root, 'pointermove', event => {
      if (!active() || !fine.matches || event.pointerType === 'touch') return;
      const rect = root.getBoundingClientRect();
      pointerX = ((event.clientX - rect.left) / Math.max(1, rect.width) - .5) * 12;
      pointerY = ((event.clientY - rect.top) / Math.max(1, rect.height) - .5) * 9;
    }, { passive: true });
    listen(root, 'pointerleave', () => { pointerX = 0; pointerY = 0; }, { passive: true });
    listen(document, 'visibilitychange', () => {
      visible = !document.hidden;
      if (!visible) { clearTimeout(clockTimer); clockTimer = 0; cancelAnimationFrame(resizeFrame); resizeFrame = 0; }
      else { resize(); updateClock(); }
      syncMotion();
    });
    listen(window, 'pagehide', () => { visible = false; clearTimeout(clockTimer); clockTimer = 0; cancelAnimationFrame(resizeFrame); resizeFrame = 0; syncMotion(); });
    listen(window, 'pageshow', () => { visible = !document.hidden; if (visible) { resize(); updateClock(); } syncMotion(); });
    if (typeof ResizeObserver !== 'undefined') {
      const resizeObserver = new ResizeObserver(scheduleResize); resizeObserver.observe(root);
      cleanups.push(() => resizeObserver.disconnect());
    } else listen(window, 'resize', scheduleResize, { passive: true });
    if (typeof IntersectionObserver !== 'undefined') {
      const intersection = new IntersectionObserver(entries => { inViewport = !!entries[0]?.isIntersecting; syncMotion(); }, { threshold: 0 });
      intersection.observe(root); cleanups.push(() => intersection.disconnect());
    }
    for (const media of [reduced, fine]) {
      if (media.addEventListener) listen(media, 'change', syncMotion);
      else if (media.addListener) { media.addListener(syncMotion); cleanups.push(() => media.removeListener(syncMotion)); }
    }
    resize(); updateClock(); syncMotion();
    root.dataset.ready = 'true'; window.__zhiheng_visual_ready = true;
    return true;
  };
  if (!init() && !runtime.disposed) {
    observer = new MutationObserver(() => { if (document.getElementById('zh-desktop')) init(); });
    observer.observe(document.body || document.documentElement, { childList: true, subtree: true });
    observerTimer = setTimeout(() => { stopObserver(); if (!runtime.root) runtime.dispose(); }, 10000);
  }
}
"""
