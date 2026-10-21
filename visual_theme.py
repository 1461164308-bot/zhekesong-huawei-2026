"""Liquid glass, live local clock and readable controls for the step workspace."""

DESKTOP_HTML = r"""
<div class="zh-liquid-aurora" aria-hidden="true"><span></span><span></span><span></span></div>
<section id="zh-desktop" data-ready="false" aria-label="知衡液态玻璃创作空间">
  <header class="zh-topbar zh-liquid">
    <div class="zh-brand">
      <svg class="zh-mark" viewBox="0 0 64 64" role="img" aria-label="知衡图标"><g fill="#c7000b" transform="translate(32 32)"><path d="M 0 -6.4 C 5.7 -12.4 6.6 -20.6 0 -27 C -6.6 -20.6 -5.7 -12.4 0 -6.4 Z"/><path d="M 0 -6.4 C 5.7 -12.4 6.6 -20.6 0 -27 C -6.6 -20.6 -5.7 -12.4 0 -6.4 Z" transform="rotate(45)"/><path d="M 0 -6.4 C 5.7 -12.4 6.6 -20.6 0 -27 C -6.6 -20.6 -5.7 -12.4 0 -6.4 Z" transform="rotate(90)"/><path d="M 0 -6.4 C 5.7 -12.4 6.6 -20.6 0 -27 C -6.6 -20.6 -5.7 -12.4 0 -6.4 Z" transform="rotate(135)"/><path d="M 0 -6.4 C 5.7 -12.4 6.6 -20.6 0 -27 C -6.6 -20.6 -5.7 -12.4 0 -6.4 Z" transform="rotate(180)"/><path d="M 0 -6.4 C 5.7 -12.4 6.6 -20.6 0 -27 C -6.6 -20.6 -5.7 -12.4 0 -6.4 Z" transform="rotate(225)"/><path d="M 0 -6.4 C 5.7 -12.4 6.6 -20.6 0 -27 C -6.6 -20.6 -5.7 -12.4 0 -6.4 Z" transform="rotate(270)"/><path d="M 0 -6.4 C 5.7 -12.4 6.6 -20.6 0 -27 C -6.6 -20.6 -5.7 -12.4 0 -6.4 Z" transform="rotate(315)"/></g></svg>
      <strong>知衡</strong><small>华为 PC 图文营销智能体</small>
    </div>
    <span class="zh-local">你的风格 · 有据可循</span>
  </header>
  <div class="zh-liquid-banner">
    <div class="zh-liquid-intro zh-liquid">
      <span class="zh-eyebrow">ZHIHENG · YOUR CREATIVE SPACE</span>
      <h2>让每一篇内容，都有你的风格。</h2>
      <p>一次专注一步，从真实需求走向有据可循的图文。</p>
      <span class="zh-flow-note"><i aria-hidden="true"></i> 逐步创作 · 随时回看</span>
    </div>
    <aside class="zh-liquid-clock zh-liquid" aria-label="创作控制中心">
      <div class="zh-clock-heading"><span>创作控制中心</span><span data-zh-date>正在读取日期</span></div>
      <time aria-label="本地时间"><span data-zh-hours>--</span><span class="zh-clock-colon">:</span><span data-zh-minutes>--</span><small data-zh-seconds>--</small></time>
      <div class="zh-clock-caption"><span>每一步，由你决定。</span><span>LOCAL TIME</span></div>
    </aside>
  </div>
</section>
"""

DESKTOP_CSS = r"""
:root { --zh-navy:#172c49;--zh-teal:#175ddc;--zh-muted:#5b6d85;--zh-border:#d9e2ef; }
body,body.dark { background:#edf2f9 !important; }
.gradio-container { overflow:visible !important;--body-text-color:#172c49;--body-text-color-subdued:#5b6d85;--block-background-fill:#fff;--block-border-color:#d9e2ef;--input-background-fill:#fff;--input-border-color:#c8d4e5;--background-fill-primary:#edf2f9;--background-fill-secondary:#f6f8fc;--button-primary-background-fill:#175ddc;--button-primary-background-fill-hover:#104cbc;--button-primary-text-color:#fff;--color-accent:#175ddc;--link-text-color:#175ddc;background:transparent !important;color:#172c49 !important;font-family:"HarmonyOS Sans SC","Microsoft YaHei",sans-serif !important; }
.gradio-container.gradio-container { max-width:1280px !important;padding:18px 24px 20px !important; }
.gradio-container > .main { padding:0 !important; }
#zh-liquid-header .html-container { padding:0 !important; }
.zh-topbar { display:flex;align-items:center;justify-content:space-between;gap:16px;padding:8px 0 16px;border-bottom:1px solid #d9e2ef;color:#172c49; }
.zh-brand { display:flex;align-items:center;gap:10px; }
.zh-brand .zh-mark { width:30px;height:30px;flex:none;display:block; }
.zh-brand strong { font-size:20px; }
.zh-brand small,.zh-local { font-size:12px;color:#5b6d85; }
#zh-guide { margin:0 !important;font-size:12px;color:#5b6d85 !important; }
#zh-connection { padding:5px 10px !important;background:#f6f8fc !important;border:1px solid #d9e2ef !important;border-radius:12px !important;align-items:center; }
#zh-connection-body { font-size:12px; }
#zh-workspace { gap:20px !important;align-items:flex-start !important; }
#zh-sidebar { position:sticky !important;top:16px;align-self:flex-start !important;flex:0 0 200px !important;min-width:190px !important;background:#f8faff;border:1px solid #d9e2ef;border-radius:16px;padding:16px !important;gap:9px !important;z-index:20; }
#zh-nav-buttons { gap:8px !important;min-width:0 !important; }
#zh-sidebar h3 { font-size:16px;margin:0 0 6px; }
#zh-sidebar p { font-size:12px;color:#5b6d85;line-height:1.6; }
#zh-sidebar button { justify-content:flex-start !important;text-align:left;min-height:43px;border-radius:10px !important; }
#zh-sidebar button.primary { background:#175ddc !important;border-color:#175ddc !important;color:#fff !important; }
#zh-sidebar button.secondary { background:transparent !important;border-color:transparent !important;color:#415875 !important; }
#zh-sidebar button.secondary:hover { background:#e6effe !important; }
#zh-main { min-width:0 !important;gap:14px !important; }
#zh-status { background:#eaf1ff !important;border:1px solid #cdddf7 !important;border-radius:13px !important;padding:12px 16px !important;margin:0 !important;min-height:0; }
#zh-status h3 { font-size:15px;margin:0 0 3px;color:#234678; }
#zh-status p { margin:0;color:#395577;font-size:13px;line-height:1.6; }
#zh-main > [id^="zh-page-"] { background:#fff;border:1px solid #d9e2ef;border-radius:16px;padding:22px !important;gap:14px !important;box-shadow:0 5px 18px #17324d05; }
#zh-main h3 { font-size:18px; }
.gradio-container .block,.gradio-container .form,.gradio-container .panel,.gradio-container .accordion,.gradio-container fieldset,.gradio-container .styler { background:#fff !important;border-color:#d9e2ef !important;border-radius:10px !important; }
.gradio-container textarea,.gradio-container input,.gradio-container [role="combobox"] { background:#fff !important;color:#172c49 !important;border-radius:8px !important; }
.gradio-container label > span,.gradio-container summary { color:#233b59 !important;background:#fff !important; }
.gradio-container button.primary,#zh-generate { background:#175ddc !important;color:#fff !important;border:1px solid #175ddc !important;border-radius:10px !important;min-height:42px;box-shadow:none !important; }
.gradio-container button.primary:hover,#zh-generate:hover { background:#104cbc !important; }
.gradio-container button:disabled { opacity:.45 !important; }
.gradio-container button.secondary { background:#f6f8fc !important;color:#334d6e !important;border:1px solid #d4deeb !important;border-radius:10px !important; }
.gradio-container button:focus-visible { outline:3px solid #6092e9 !important;outline-offset:2px; }
.gradio-container .block:has(.options),.gradio-container .form:has(.options) { overflow:visible !important;position:relative;z-index:100; }
.gradio-container .options,.gradio-container [role="listbox"] { background:#fff !important;opacity:1 !important;border:1px solid #b7c8df !important;box-shadow:0 10px 24px #172c4920 !important;z-index:2147480000 !important; }
.gradio-container [role="option"],.gradio-container .options .item { background:#fff !important;color:#172c49 !important; }
.gradio-container [role="option"]:hover,.gradio-container .options .item:hover { background:#eaf1ff !important; }
.gradio-container [role="option"][aria-selected="true"],.gradio-container .options .item.selected { background:#dce9ff !important;color:#104cbc !important; }
.zh-page-links { border-top:1px solid #e4eaf3;padding-top:14px;margin-top:8px; }
.zh-page-links button { font-size:12px !important; }
#zh-tabs .tab-nav button.selected { color:#175ddc !important;border-bottom-color:#175ddc !important; }
#zh-preview { overflow:auto;min-height:180px !important;padding:4px !important; }
#zh-report { min-height:120px !important; }
#zh-footer { color:#64758b !important;font-size:11px;margin:4px 0 0; }
@media(max-width:760px) {
  .gradio-container.gradio-container { padding:12px !important; }
  .zh-brand small { display:none; }
  .zh-local { font-size:10px; }
  #zh-workspace { flex-direction:column !important;gap:12px !important; }
  #zh-sidebar { position:sticky !important;top:0;flex:0 0 auto !important;min-width:0 !important;width:100% !important;box-sizing:border-box;gap:6px !important;padding:9px !important;box-shadow:0 3px 12px #172c4910; }
  #zh-sidebar > div:not(#zh-nav-buttons) { display:none; }
  #zh-nav-buttons { display:grid !important;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px !important; }
  #zh-sidebar button { min-width:0 !important;min-height:36px;font-size:12px !important;padding:6px !important;justify-content:center !important;text-align:center; }
  #zh-main { width:100% !important; }
  #zh-main > [id^="zh-page-"] { padding:16px !important; }
}
/* Liquid-glass identity surrounds, rather than obscures, the working controls. */
body,body.dark { background:#dbe8fb !important;background-image:linear-gradient(150deg,#eaf2ff 0%,#d6e4fc 48%,#dce5fb 75%,#d6edf4 100%) !important;background-attachment:fixed !important; }
.gradio-container { isolation:isolate;--background-fill-primary:transparent;--zh-mx:50%;--zh-my:35%; }
#zh-liquid-header { background:transparent !important;border:0 !important;padding:0 !important; }
#zh-desktop { color:#16233f;margin-bottom:6px; }
#zh-desktop * { box-sizing:border-box; }
.zh-liquid-aurora { position:fixed;inset:0;z-index:-1;pointer-events:none;overflow:hidden; }
.zh-liquid-aurora span { position:absolute;border-radius:50%;filter:blur(65px);opacity:.65;animation:zh-aurora-flow 26s ease-in-out infinite; }
.zh-liquid-aurora span:nth-child(1) { width:65vw;height:65vw;left:-12vw;top:-25vw;background:radial-gradient(circle,#afcaff,transparent 68%); }
.zh-liquid-aurora span:nth-child(2) { width:58vw;height:58vw;right:-18vw;top:6vh;background:radial-gradient(circle,#c8bff0,transparent 68%);animation-delay:-9s; }
.zh-liquid-aurora span:nth-child(3) { width:55vw;height:55vw;left:22vw;bottom:-30vw;background:radial-gradient(circle,#a7e0eb,transparent 70%);animation-delay:-16s; }
@keyframes zh-aurora-flow { 0%,100% { transform:translate(0,0) scale(1); } 50% { transform:translate(4vw,3vh) scale(1.08); } }
.zh-liquid { position:relative;background:linear-gradient(135deg,#ffffffae,#ffffff57);border:1px solid #ffffffc9;backdrop-filter:blur(28px) saturate(145%);-webkit-backdrop-filter:blur(28px) saturate(145%);box-shadow:0 16px 42px #3557a522,inset 0 1px 1px #ffffffeb,inset 0 -1px 2px #849ad52b; }
.zh-liquid::before { content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;background:radial-gradient(340px circle at var(--zh-mx,50%) var(--zh-my,30%),#ffffff55,transparent 72%); }
.zh-liquid > * { position:relative; }
.zh-topbar { padding:12px 20px;border-radius:24px;gap:12px;margin-bottom:14px; }
.zh-brand .zh-mark { filter:drop-shadow(0 4px 10px #c7000b26); }
/* 快发模式的见闻预选卡：一排小按钮，点一下填空，不生成。 */
#zh-quick-presets-hint { font-size:12px;color:#526581;margin:2px 0 6px !important; }
.zh-quick-preset-row { gap:8px !important;flex-wrap:nowrap !important;align-items:stretch !important; }
.zh-quick-preset-row > * { flex:1 1 0 !important;min-width:0 !important; }
.zh-quick-preset-row button { width:100%;min-width:0 !important;min-height:38px;border-radius:9px !important;
  font-size:12.5px !important;padding:0 4px !important;white-space:nowrap;
  background:#f4f7fb !important;border:1px solid #dbe4ef !important;color:#2b4a74 !important;box-shadow:none !important; }
.zh-quick-preset-row button:hover { background:#e8f0fb !important;border-color:#bcd2ee !important;color:#12488f !important; }
.zh-local { background:#ffffff70;border:1px solid #ffffffa6;border-radius:99px;padding:7px 12px;color:#3260a2;white-space:nowrap; }
.zh-liquid-banner { display:grid;grid-template-columns:1.35fr 1fr;gap:16px; }
.zh-liquid-intro,.zh-liquid-clock { border-radius:26px;padding:22px 26px;min-width:0; }
.zh-liquid-intro { display:flex;flex-direction:column;justify-content:center;gap:10px; }
.zh-eyebrow { font-size:10px;letter-spacing:.13em;font-weight:650;color:#2268d8; }
.zh-liquid-intro h2 { font-size:clamp(22px,2.3vw,30px);line-height:1.45;margin:0;color:#172c49;letter-spacing:-.03em; }
.zh-liquid-intro p { margin:0;font-size:13px;line-height:1.8;color:#526581; }
.zh-flow-note { display:flex;align-items:center;gap:7px;font-size:11px;color:#526581; }
.zh-flow-note i { width:6px;height:6px;border-radius:50%;background:#3b8bcf;box-shadow:0 0 9px #5a99df66; }
.zh-liquid-clock { display:flex;flex-direction:column;justify-content:space-between;gap:12px; }
.zh-clock-heading,.zh-clock-caption { display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:11px;color:#536783; }
.zh-liquid-clock time { display:flex;align-items:baseline;justify-content:center;gap:3px;font-size:62px;font-weight:260;font-variant-numeric:tabular-nums;letter-spacing:-.05em;color:#18345b;line-height:1.1; }
.zh-liquid-clock time small { font-size:19px;letter-spacing:0;margin-left:8px;color:#5d759a; }
.zh-clock-caption > span:last-child { font-size:9px;letter-spacing:.12em;color:#7384a0; }
#zh-sidebar { background:linear-gradient(145deg,#ffffffaa,#ffffff70) !important;border:1px solid #ffffffc9 !important;border-radius:24px !important;backdrop-filter:blur(26px) saturate(140%);-webkit-backdrop-filter:blur(26px) saturate(140%);box-shadow:0 14px 36px #3557a51b,inset 0 1px 1px #ffffffdc; }
#zh-main > [id^="zh-page-"] { background:linear-gradient(145deg,#ffffffb8,#ffffff82) !important;border:1px solid #ffffffd9 !important;border-radius:24px !important;backdrop-filter:blur(24px) saturate(130%);-webkit-backdrop-filter:blur(24px) saturate(130%);box-shadow:0 16px 38px #3557a51a,inset 0 1px 1px #ffffffed; }
#zh-status { background:linear-gradient(135deg,#f3f8ffe6,#e5f0ffbf) !important;border-color:#ffffffd9 !important;border-radius:18px !important;box-shadow:inset 0 1px 1px #ffffffc9; }
#zh-connection-details { background:#ffffff80 !important;border:1px solid #ffffffbf !important;border-radius:17px !important;backdrop-filter:blur(18px); }
#zh-connection-details > .label-wrap { background:transparent !important; }
.gradio-container button.primary,#zh-sidebar button.primary,#zh-generate { background:linear-gradient(135deg,#0a59ef,#4b88f4) !important;border:1px solid #ffffff80 !important;border-radius:15px !important;box-shadow:0 5px 14px #145ddf24,inset 0 1px 1px #ffffff80 !important; }
.gradio-container button.primary:hover,#zh-sidebar button.primary:hover,#zh-generate:hover { background:linear-gradient(135deg,#064bd1,#3f7ce9) !important; }
#zh-sidebar button.secondary { background:#ffffff45 !important;border:1px solid #ffffff88 !important;border-radius:15px !important; }
#zh-sidebar button.secondary:hover { background:#ffffffa8 !important; }
.gradio-container textarea,.gradio-container input,.gradio-container [role="combobox"],.gradio-container .options,.gradio-container [role="listbox"] { background:#fff !important; }
@media(max-width:760px) {
  .zh-topbar { padding:10px 14px;border-radius:20px; }
  .zh-local { padding:6px 9px;font-size:10px; }
  .zh-liquid-banner { grid-template-columns:1fr;gap:10px; }
  .zh-liquid-intro { padding:17px 20px;gap:7px;border-radius:23px; }
  .zh-liquid-intro h2 { font-size:23px; }
  .zh-liquid-intro p { font-size:12px; }
  .zh-flow-note { display:none; }
  .zh-liquid-clock { display:grid;grid-template-columns:1fr auto;align-items:center;gap:9px 12px;padding:15px 20px;border-radius:23px; }
  .zh-clock-heading { flex-direction:column;align-items:flex-start;gap:6px; }
  .zh-liquid-clock time { font-size:43px;gap:2px; }
  .zh-liquid-clock time small { font-size:15px;margin-left:4px; }
  .zh-clock-caption { grid-column:1/-1;font-size:10px; }
  #zh-sidebar { background:#eaf2ffeb !important;border-radius:19px !important; }
}
@media(prefers-reduced-motion:reduce) {
  .zh-liquid-aurora span { animation:none !important; }
  .zh-liquid::before { background:none; }
  html { scroll-behavior:auto; }
}
html[data-zh-hidden="true"] .zh-liquid-aurora span { animation-play-state:paused; }
/* Mode entry is a real choice, not a second set of hidden workflow anchors. */
#zh-mode-home { gap:18px !important;padding:12px 0 18px !important; }
#zh-mode-cards { gap:22px !important;align-items:stretch; }
.zh-mode-card { min-width:280px !important;background:linear-gradient(140deg,#ffffffb8,#ffffff70) !important;border:1px solid #ffffffdf;border-radius:28px;padding:27px !important;backdrop-filter:blur(26px) saturate(140%);box-shadow:0 18px 40px #3557a51b,inset 0 1px 1px #fff;transform:perspective(1100px) rotateX(var(--zh-rx,0deg)) rotateY(var(--zh-ry,0deg)) translateY(var(--zh-lift,0px));transform-style:preserve-3d;will-change:transform;transition:transform .22s ease,box-shadow .22s ease,border-color .22s ease; }
.zh-mode-card:hover,.zh-mode-card:focus-within { --zh-lift:-4px;box-shadow:0 24px 46px #3557a52d,inset 0 1px 1px #fff;border-color:#ffffff !important; }
.zh-mode-card .html-container { padding:0 !important; }
.zh-mode-icon { width:46px;height:46px;display:grid;place-items:center;background:linear-gradient(135deg,#e2eeff,#ffffffad);border:1px solid #ffffffdd;border-radius:16px;font-size:27px;color:#2467cf; }
.zh-mode-card h3 { font-size:27px !important;margin:18px 0 8px !important;color:#172c49; }
.zh-mode-tagline { color:#526581;font-size:15px;margin:0; }
.zh-mode-description { min-height:66px;font-size:13px;line-height:1.8;color:#435b7c;margin:16px 0 12px;opacity:0;transform:translateY(7px);transition:opacity .22s ease,transform .22s ease; }
.zh-mode-card:hover .zh-mode-description,.zh-mode-card:focus-within .zh-mode-description { opacity:1;transform:none; }
#zh-mode-bar { align-items:center;gap:16px !important;padding:10px 15px !important;border:1px solid #ffffffcf;border-radius:18px;background:#ffffff80; }
#zh-mode-label { flex:1;background:transparent !important;border:0 !important; }
#zh-switch-mode { flex:0 0 auto;min-width:100px; }
#zh-simple-layout { align-items:flex-start;gap:18px !important; }
#zh-simple-brief,#zh-simple-conversation,#zh-simple-result { min-width:0 !important;background:linear-gradient(145deg,#ffffffb8,#ffffff82) !important;border:1px solid #ffffffdf;border-radius:25px;padding:21px !important;backdrop-filter:blur(24px) saturate(130%);box-shadow:0 15px 34px #3557a51a; }
#zh-simple-status { background:#eef5ffbd !important;border-radius:16px !important;padding:12px 15px !important; }
#zh-simple-chat { background:#ffffffdd !important;border-radius:18px !important; }
#zh-simple-result { margin-top:15px; }
#zh-simple-preview { min-height:150px;overflow:auto; }
#zh-simple-generate { min-height:46px; }
@media(hover:none) { .zh-mode-description { opacity:1;transform:none; } }
@media(max-width:760px) {
  #zh-mode-cards,#zh-simple-layout { flex-direction:column !important; }
  .zh-mode-card,#zh-simple-brief,#zh-simple-conversation { width:100% !important;min-width:0 !important;box-sizing:border-box; }
  .zh-mode-card { padding:22px !important; }
  .zh-mode-description { opacity:1;transform:none;min-height:0; }
  #zh-simple-brief,#zh-simple-conversation,#zh-simple-result { padding:16px !important; }
}
/* 滚动入场：默认可见，只有 JS 标记 data-zh-reveal="on" 后才先压低再浮起，JS 失效也不会白屏。 */
html[data-zh-reveal="on"] .zh-reveal { opacity:0;translate:0 12px;transition:none; }
html[data-zh-reveal="on"] .zh-reveal.zh-in { opacity:1;translate:0 0;
  transition:opacity .52s ease,translate .58s cubic-bezier(.22,.9,.25,1); }
@media(prefers-reduced-motion:reduce) {
  html[data-zh-reveal="on"] .zh-reveal { opacity:1 !important;translate:none !important;transition:none !important; }
}
/* 指针微交互：卡片高光跟手、按钮轻轻抬起、配图放大、手风琴与标签页都有回应。 */
.zh-liquid,.zh-mode-card { --zh-mx:50%;--zh-my:35%; }
.zh-liquid::before { transition:background .18s ease; }
@media (hover:hover) {
  .gradio-container button:not(.zh-quick-preset-row button),#zh-sidebar button,.zh-mode-card button {
    transition:transform .16s ease,box-shadow .16s ease,background .16s ease,border-color .16s ease;
  }
  .gradio-container button:hover { transform:translateY(-1px); }
  .gradio-container button:active { transform:translateY(0) scale(.985); }
  .gradio-container button.primary:hover,#zh-generate:hover {
    box-shadow:0 9px 22px #145ddf30,inset 0 1px 1px #ffffffa6 !important;
  }
  .zh-mode-card:hover,.zh-mode-card:focus-within { border-color:#ffffff !important; }
  .zh-mode-card:hover .zh-mode-icon,.zh-mode-card:focus-within .zh-mode-icon {
    transform:translateZ(26px) rotate(-7deg) scale(1.08);box-shadow:0 8px 18px #2467cf22;
  }
  .zh-mode-icon { transition:transform .28s cubic-bezier(.22,.9,.25,1),box-shadow .28s ease; }
  .zh-mode-card:hover h3 { color:#0f56c8; }
  .zh-mode-card h3 { transition:color .2s ease; }
  .zh-quick-preset-row button:hover { transform:translateY(-2px);box-shadow:0 6px 14px #2b4a7414 !important; }
  .zh-brand:hover .zh-mark { transform:rotate(45deg) scale(1.06); }
  .zh-brand .zh-mark { transition:transform .45s cubic-bezier(.22,.9,.25,1); }
  #zh-quick-results button[role="tab"]:hover,#zh-mode-tabs button:hover { color:#172c49 !important; }
  #zh-quick-results button[role="tab"] { transition:color .18s ease,border-color .18s ease; }
  .label-wrap:hover,.accordion-header:hover { background:#ffffff8a !important;border-radius:12px; }
  .label-wrap { transition:background .18s ease; }
  [id^="zh-quick-gallery-"] .grid-wrap,[id^="zh-quick-gallery-"] .gallery { border-radius:14px;overflow:hidden; }
  [id^="zh-quick-gallery-"] img { transition:transform .42s cubic-bezier(.22,.9,.25,1),filter .42s ease; }
  [id^="zh-quick-gallery-"] img:hover { transform:scale(1.055);filter:saturate(1.06); }
  .gradio-container textarea:hover,.gradio-container input:hover,.gradio-container [role="combobox"]:hover { border-color:#b9cbe6 !important; }
  #zh-sidebar button:hover { transform:translateX(2px); }
}
@media(prefers-reduced-motion:reduce) { .zh-mode-card,.zh-mode-description { transition:none !important;transform:none !important; } }
@media(prefers-reduced-motion:reduce) {
  .gradio-container button,.zh-mode-icon,.zh-brand .zh-mark,[id^="zh-quick-gallery-"] img,
  .zh-quick-preset-row button,#zh-sidebar button { transition:none !important; }
  .gradio-container button:hover,.gradio-container button:active,.zh-mode-card:hover .zh-mode-icon,
  .zh-brand:hover .zh-mark,[id^="zh-quick-gallery-"] img:hover { transform:none !important; }
}
/* Shared reading rhythm: text surfaces need their own inset, even when Gradio hides the container. */
.gradio-container {
  --zh-copy-size:14px;
  --zh-copy-leading:1.8;
  --zh-text-inset:20px;
  --body-text-size:14px;
  --block-label-text-size:13px;
}
.gradio-container .block:has(> [data-testid="markdown-wrapper"]) {
  box-sizing:border-box;
  padding:16px var(--zh-text-inset) !important;
  border-radius:14px !important;
}
.gradio-container [data-testid="markdown-wrapper"] .prose {
  font-size:var(--zh-copy-size);
  line-height:var(--zh-copy-leading);
  overflow-wrap:anywhere;
  word-break:normal;
}
.gradio-container [data-testid="markdown-wrapper"] :is(h1,h2,h3,h4) {
  line-height:1.5;
  letter-spacing:.015em;
  font-weight:650;
  text-wrap:pretty;
}
.gradio-container [data-testid="markdown-wrapper"] h2 { font-size:24px;margin:0 0 12px; }
.gradio-container [data-testid="markdown-wrapper"] h3 { font-size:19px;margin:22px 0 10px; }
.gradio-container [data-testid="markdown-wrapper"] p { margin:0 0 12px; }
.gradio-container [data-testid="markdown-wrapper"] :is(ul,ol) { padding-inline-start:1.5em;margin:12px 0; }
.gradio-container [data-testid="markdown-wrapper"] li { margin:5px 0; }
.gradio-container [data-testid="markdown-wrapper"] .md > :first-child { margin-top:0 !important; }
.gradio-container [data-testid="markdown-wrapper"] .md > :last-child { margin-bottom:0 !important; }
/* Panels already provide an inset: avoid a second white tile touching its own rounded corners. */
:is(#zh-sidebar,#zh-simple-brief,#zh-simple-conversation,#zh-simple-result,[id^="zh-page-"])
  > .block:has(> [data-testid="markdown-wrapper"]) {
  background:transparent !important;
  border-color:transparent !important;
  padding:0 !important;
}
.zh-mode-card .block:has(> .html-container) { background:transparent !important;border:0 !important; }
.zh-mode-card h3 { font-size:25px !important;line-height:1.45;margin:18px 0 10px !important; }
.zh-mode-tagline { font-size:14px;line-height:1.8; }
.zh-mode-description { line-height:1.85;margin:16px 0 14px; }
.gradio-container textarea { font-size:14px !important;line-height:1.75 !important;padding:12px 14px !important; }
.gradio-container input { font-size:14px !important;line-height:1.6 !important; }
.gradio-container label > span { line-height:1.6 !important; }
#zh-mode-label { padding:0 !important; }
#zh-quick-body { gap:18px !important; }
#zh-quick-presets { gap:10px !important; }
#zh-quick-presets-hint { padding:12px 16px !important; }
#zh-footer { padding:12px 20px !important;line-height:1.8; }
@media(max-width:760px) {
  .gradio-container { --zh-text-inset:16px; }
  .gradio-container .block:has(> [data-testid="markdown-wrapper"]) { padding:14px var(--zh-text-inset) !important; }
  .gradio-container [data-testid="markdown-wrapper"] h2 { font-size:21px; }
  .gradio-container [data-testid="markdown-wrapper"] h3 { font-size:18px; }
  :is(#zh-sidebar,#zh-simple-brief,#zh-simple-conversation,#zh-simple-result,[id^="zh-page-"])
    > .block:has(> [data-testid="markdown-wrapper"]),#zh-mode-label { padding:0 !important; }
  .zh-mode-card h3 { font-size:23px !important; }
  #zh-footer { padding:12px 16px !important; }
}
"""

# A single disposable timer survives Gradio remounts without multiplying clocks.
DESKTOP_JS = r"""
() => {
  window.__zhihengDesktopRuntime?.dispose();
  window.__zhiheng_visual_ready = false;
  let timer = 0, observer = null, observerTimeout = 0, disposed = false, root = null;
  const cleanups = [];
  const listen = (target, name, callback, options) => {
    target.addEventListener(name, callback, options);
    cleanups.push(() => target.removeEventListener(name, callback, options));
  };
  const stopObserver = () => {
    observer?.disconnect(); observer = null;
    clearTimeout(observerTimeout); observerTimeout = 0;
  };
  // 指针高光：玻璃卡片上的柔光跟着鼠标走，离开即回中；一帧只更新一次，不触发重排风暴。
  let spotFrame = 0, spotTarget = null, spotX = 0, spotY = 0;
  const surface = node => (node instanceof Element ? node.closest('.zh-liquid,.zh-mode-card') : null);
  const paintSpot = () => {
    spotFrame = 0;
    if (!spotTarget || !spotTarget.isConnected) return;
    const box = spotTarget.getBoundingClientRect();
    spotTarget.style.setProperty('--zh-mx', `${Math.round(spotX - box.left)}px`);
    spotTarget.style.setProperty('--zh-my', `${Math.round(spotY - box.top)}px`);
  };
  const moveSpot = event => {
    if (event.pointerType === 'touch') return;
    const target = surface(event.target);
    if (!target) return;
    spotTarget = target; spotX = event.clientX; spotY = event.clientY;
    if (!spotFrame) spotFrame = requestAnimationFrame(paintSpot);
    // 模式卡再叠一层 1-2° 的 3D 倾斜：像实体卡片被鼠标压着转了一点。
    if (target.classList.contains('zh-mode-card')) {
      const box = target.getBoundingClientRect();
      const px = (event.clientX - box.left) / box.width - 0.5;
      const py = (event.clientY - box.top) / box.height - 0.5;
      target.style.setProperty('--zh-ry', `${(px * 3.4).toFixed(2)}deg`);
      target.style.setProperty('--zh-rx', `${(-py * 2.6).toFixed(2)}deg`);
    }
  };
  const releaseSpot = event => {
    const target = surface(event.target);
    if (!target || (event.relatedTarget && target.contains(event.relatedTarget))) return;
    target.style.setProperty('--zh-mx', '50%');
    target.style.setProperty('--zh-my', '35%');
    target.style.setProperty('--zh-rx', '0deg');
    target.style.setProperty('--zh-ry', '0deg');
  };
  if (typeof document.addEventListener === 'function' && typeof requestAnimationFrame === 'function') {
    listen(document, 'pointermove', moveSpot, {passive: true});
    listen(document, 'pointerout', releaseSpot, {passive: true});
  }
  // 滚动入场：只在 IntersectionObserver 可用时开启，逐个错峰浮起；DOM 变了（切标签页）会重新扫描。
  const REVEAL_SELECTOR = ['.zh-liquid-banner > .zh-liquid', '.zh-mode-card', '#zh-quick-inputs',
                           '#zh-quick-visit', '#zh-quick-presets', '#zh-quick-actions', '#zh-quick-results'].join(',');
  let revealObserver = null, revealScan = 0, revealWatch = null;
  const revealNode = node => {
    if (!(node instanceof Element) || node.dataset.zhReveal === '1') return;
    node.dataset.zhReveal = '1';
    node.classList.add('zh-reveal');
    if (!revealObserver) { node.classList.add('zh-in'); return; }
    const parent = node.parentElement;
    if (parent) {
      const siblings = Array.from(parent.children).filter(child => child.classList.contains('zh-reveal'));
      node.style.transitionDelay = `${Math.min((siblings.length - 1) * 55, 275)}ms`;
    }
    revealObserver.observe(node);
  };
  const scanReveal = () => {
    if (disposed) return;
    document.querySelectorAll(REVEAL_SELECTOR).forEach(revealNode);
  };
  if (typeof IntersectionObserver === 'function') {
    revealObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const node = entry.target;
        node.classList.add('zh-in');
        revealObserver.unobserve(node);
        // 入场结束后必须把 zh-reveal / zh-in 清掉：残留的 translate 会变成
        // fixed 定位子元素的包含块，导致下拉选项跑到屏幕外（型号选择点不开）。
        setTimeout(() => {
          if (disposed) return;
          node.classList.remove('zh-reveal', 'zh-in');
          node.style.transitionDelay = '';
        }, 1000);
      });
    }, {threshold: 0.06, rootMargin: '0px 0px -6% 0px'});
    document.documentElement.setAttribute('data-zh-reveal', 'on');
    scanReveal();
    revealWatch = new MutationObserver(() => { clearTimeout(revealScan); revealScan = setTimeout(scanReveal, 70); });
    revealWatch.observe(document.documentElement, {childList: true, subtree: true});
    cleanups.push(() => {
      revealWatch?.disconnect(); revealWatch = null;
      clearTimeout(revealScan); revealScan = 0;
      revealObserver?.disconnect(); revealObserver = null;
      document.documentElement.removeAttribute('data-zh-reveal');
      document.querySelectorAll('.zh-reveal').forEach(node => {
        node.classList.remove('zh-reveal', 'zh-in');
        node.style.transitionDelay = '';
        delete node.dataset.zhReveal;
      });
    });
  }
  const runtime = {dispose() {
    disposed = true; clearTimeout(timer); stopObserver();
    if (spotFrame && typeof cancelAnimationFrame === 'function') cancelAnimationFrame(spotFrame);
    spotFrame = 0; spotTarget = null;
    cleanups.splice(0).forEach(fn => fn());
    if (root) root.dataset.ready = 'false';
    window.__zhiheng_visual_ready = false;
  }};
  window.__zhihengDesktopRuntime = runtime;
  const initialize = () => {
    if (disposed) return false;
    root = document.getElementById('zh-desktop');
    if (!root) return false;
    const hours = root.querySelector('[data-zh-hours]');
    const minutes = root.querySelector('[data-zh-minutes]');
    const seconds = root.querySelector('[data-zh-seconds]');
    const date = root.querySelector('[data-zh-date]');
    const time = root.querySelector('time');
    if (!hours || !minutes || !seconds || !date || !time) return false;
    stopObserver();
    const pad = n => String(n).padStart(2, '0');
    const updateClock = () => {
      clearTimeout(timer); timer = 0;
      if (disposed || document.hidden) return;
      if (!root.isConnected) { runtime.dispose(); return; }
      const now = new Date();
      hours.textContent = pad(now.getHours());
      minutes.textContent = pad(now.getMinutes());
      seconds.textContent = pad(now.getSeconds());
      date.textContent = new Intl.DateTimeFormat('zh-CN', {month:'long', day:'numeric', weekday:'short'}).format(now);
      time.dateTime = now.toISOString();
      time.setAttribute('aria-label', '本地时间 ' + pad(now.getHours()) + ':' + pad(now.getMinutes()));
      timer = setTimeout(updateClock, 1020 - Date.now() % 1000);
    };
    const syncVisibility = () => {
      document.documentElement.dataset.zhHidden = document.hidden ? 'true' : 'false';
      if (document.hidden) { clearTimeout(timer); timer = 0; }
      else updateClock();
    };
    listen(document, 'visibilitychange', syncVisibility);
    listen(window, 'pagehide', () => { clearTimeout(timer); timer = 0; document.documentElement.dataset.zhHidden = 'true'; });
    listen(window, 'pageshow', syncVisibility);
    syncVisibility(); root.dataset.ready = 'true'; window.__zhiheng_visual_ready = true;
    return true;
  };
  if (!initialize()) {
    observer = new MutationObserver(initialize);
    observer.observe(document.documentElement, {childList:true, subtree:true});
    observerTimeout = setTimeout(stopObserver, 10000);
  }
}
"""
