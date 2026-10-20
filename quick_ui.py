"""快发模式界面：选型号 + 一句门店见闻，三平台成稿与事实依据。

单列布局、大按钮，面向手机竖屏；整个过程不调用模型，也不出现 API、知识库、
风格卡这类术语。成稿只由已核验事实卡里的值填充槽位。
"""
from __future__ import annotations

import re
import time
import zipfile
from pathlib import Path

import gradio as gr

import facts as fact_cards
import quick_flow


def _audience_choices() -> list[str]:
    import sentence_library
    return list(sentence_library.AUDIENCES)


def _model_choices() -> list[str]:
    return quick_flow.models()


def _evidence(result: dict) -> str:
    """事实依据：每个用到的数字都能点开看到官方原文与限定条件。

    Gradio 的 Markdown 会把紧跟段落的 ``- `` 当成正文，所以每条事实压成一行，
    用「·」分隔条件与来源，手机上也不会串成一大段。
    """
    rows = []
    for fact in result.get("facts", []):
        title = fact.get("name") or fact.get("section") or fact.get("slot", "")
        parts = [f"**{title}**：{fact.get('text', '')}"]
        conditions = [str(note) for note in (fact.get("conditions") or []) if str(note).strip()]
        if conditions:
            note = "；".join(conditions[:2])
            parts.append("条件：" + (note if len(note) <= 46 else note[:46] + "…"))
        url = fact.get("url", "")
        if url:
            parts.append(f"来源：[产品规格页](<{url}>)")
        rows.append(" · ".join(parts))
    if not rows:
        return "本篇没有引用产品数字。"
    return "\n\n".join(rows)


def _status(result: dict) -> str:
    if result.get("status") == "blocked":
        return "### 先改一下再生成\n" + "；".join(result.get("checks", {}).get("violations", []))
    checks = result.get("checks", {})
    minimum, maximum = checks.get("target", (0, 0))
    parts = [f"**{checks.get('length', 0)} 字**"]
    if minimum:
        parts.append(f"平台建议 {minimum}-{maximum} 字")
    parts.append(f"与近期稿件相似度 {checks.get('similarity', 0)}")
    if checks.get("within_target") is False:
        parts.append("篇幅需要再调整")
    if checks.get("violations"):
        parts.append("**需修改**：" + "；".join(checks["violations"]))
    else:
        parts.append("事实与合规检查通过")
    return "### 可以复制发布了\n" + " · ".join(parts)


def _images_md(result: dict) -> str:
    """每个平台给几张、分别是哪张、建议放哪一段，都要说清楚。"""
    images = result.get("images") or []
    checks = result.get("checks", {})
    low, high = checks.get("image_target", (0, 0))
    if not images:
        return ("**配图**：当前型号没有可用的官方配图（源知识库没给这个型号的图片文件）。"
                "先用门店实拍也能发，或者让总部补齐同型号图。")
    lines = [f"**配图**：{len(images)} 张（{result.get('platform', '')}建议 {low}-{high} 张）"]
    if checks.get("image_short"):
        lines.append("> 该型号官方图不够，先按现有张数给；发布前可补门店实拍。")
    placements = {str(item.get("placement", "")).strip() for item in images}
    shared_placement = next(iter(placements)) if len(placements) == 1 else ""
    for index, item in enumerate(images, 1):
        row = f"{index}. **{_md(item.get('title') or '官方配图')}**"
        placement = str(item.get("placement", "")).strip()
        if placement and placement != shared_placement:
            row += f" · {_md(placement)}"
        if item.get("source_url"):
            row += f" · [来源页面](<{item['source_url']}>)"
        lines.append(row)
    if shared_placement:
        lines.append(f"> 用法：{_md(shared_placement)}")
    return "  \n".join(lines)


def _md(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]<>|])", r"\\\1", str(text or ""))


def _platform_update(result: dict) -> tuple:
    if not result:
        return ("", "等待生成。", [], "生成后在这里给出同型号官方配图与建议用法。",
                "生成后在此核对每个数字的出处与限定条件。")
    gallery = [(item["path"], item.get("title", "")) for item in result.get("images") or []]
    return (result.get("text", ""), _status(result), gallery, _images_md(result), _evidence(result))


def pack_bundle(results: dict | None) -> str | None:
    """把三平台文案与配图打成一个 ZIP，按平台分文件夹。"""
    if not results:
        return None
    root = Path(__file__).resolve().parent / ".local" / "quick-export"
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"quick-{time.strftime('%Y%m%d-%H%M%S')}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as bundle:
        for platform, result in results.items():
            folder = re.sub(r"[\\/:*?\"<>|]", "_", str(platform))
            notes = [str(result.get("text", "")), "", "配图说明："]
            for index, item in enumerate(result.get("images") or [], 1):
                source = Path(str(item.get("path", "")))
                if not source.is_file():
                    continue
                name = f"{index:02d}_{re.sub(r'[\\\\/:*?\"<>|]', '_', source.name)}"
                bundle.write(source, f"{folder}/{name}")
                detail = " ".join(part for part in (item.get("title", ""), item.get("placement", ""),
                                                    item.get("source_url", "")) if part)
                notes.append(f"- {name}：{detail}".rstrip("："))
            bundle.writestr(f"{folder}/文案.txt", "\n".join(notes))
    return str(target)


def build_quick(store_state=None):
    audiences = _audience_choices()
    with gr.Column(elem_id="zh-quick-body"):
        gr.Markdown("### 快发模式\n选型号，写一句你今天在店里真实遇到的事，几秒钟拿到三个平台的成稿。"
                    "不需要会写文案，也不用配模型。")
        with gr.Row(elem_id="zh-quick-inputs"):
            with gr.Column(scale=3, min_width=240):
                model = gr.Dropdown(_model_choices(), value=None, allow_custom_value=False,
                                    label="今天推哪个型号", elem_id="zh-quick-model")
            with gr.Column(scale=2, min_width=180):
                audience = gr.Dropdown(audiences, value=audiences[0], label="主要说给谁听",
                                       elem_id="zh-quick-audience")
        visit = gr.Textbox(label="今天在店里遇到的一件小事（一句话就行）", lines=3, max_length=200,
                           placeholder="例如：有位老师来问，上网课能不能一边记笔记一边投到教室大屏。",
                           info="这句话会成为稿子的开头。写你真实看到的场景，不要写价格和优惠。",
                           elem_id="zh-quick-visit")
        with gr.Column(elem_id="zh-quick-presets"):
            gr.Markdown("**没灵感？点一个场景**，会自动填好见闻和人群，填完还能改。",
                        elem_id="zh-quick-presets-hint")
            preset_buttons = []
            for row_start in range(0, len(quick_flow.VISIT_PRESETS), 3):
                with gr.Row(elem_classes="zh-quick-preset-row"):
                    for index in range(row_start, min(row_start + 3, len(quick_flow.VISIT_PRESETS))):
                        preset = quick_flow.VISIT_PRESETS[index]
                        preset_buttons.append((
                            gr.Button(preset["label"], size="sm", elem_id=f"zh-quick-preset-{index}"),
                            preset))
        with gr.Accordion("门店档案（填一次，以后自动带上）", open=False, elem_id="zh-quick-store"):
            with gr.Row():
                store_name = gr.Textbox(label="门店名称", max_length=40, elem_id="zh-quick-store-name")
                store_city = gr.Textbox(label="城市", max_length=20, elem_id="zh-quick-store-city")
            gr.Markdown("门店信息只用于稿子结尾的到店引导，不会上传。")
        with gr.Row(elem_id="zh-quick-actions"):
            generate = gr.Button("生成三平台成稿", variant="primary", elem_id="zh-quick-generate")
            again = gr.Button("换一批", elem_id="zh-quick-again")
        notice = gr.Markdown("", elem_id="zh-quick-notice")
        results = gr.State({})
        with gr.Tabs(elem_id="zh-quick-results"):
            tabs = {}
            for platform in quick_flow.PLATFORMS:
                safe = quick_flow.PLATFORMS.index(platform)
                with gr.Tab(platform):
                    text = gr.Textbox(label=f"{platform}成稿", lines=12, interactive=False,
                                      buttons=["copy"], elem_id=f"zh-quick-text-{safe}")
                    status = gr.Markdown("等待生成。", elem_id=f"zh-quick-status-{safe}")
                    gallery = gr.Gallery(label=f"{platform}配图（同型号官方图）", columns=3, height=240,
                                         object_fit="contain", elem_id=f"zh-quick-gallery-{safe}")
                    images_md = gr.Markdown("生成后在这里给出同型号官方配图、建议放哪一段和来源。",
                                            elem_id=f"zh-quick-images-{safe}")
                    with gr.Accordion("这篇用到的数字与官方原文", open=False,
                                      elem_id=f"zh-quick-facts-panel-{safe}"):
                        evidence = gr.Markdown("生成后在此核对每个数字的出处与限定条件。",
                                               elem_id=f"zh-quick-facts-{safe}")
                tabs[platform] = (text, status, gallery, images_md, evidence)
        with gr.Row(elem_id="zh-quick-download"):
            pack = gr.Button("打包三平台配图与文案 ZIP", elem_id="zh-quick-pack")
            bundle = gr.File(label="三平台素材包（文案 txt + 配图）", interactive=False,
                             elem_id="zh-quick-bundle")
        download_notice = gr.Markdown("三版生成后，点上面的按钮生成素材包；生成完再点文件名保存。",
                                      elem_id="zh-quick-download-notice")

    outputs = [results, notice]
    for platform in quick_flow.PLATFORMS:
        outputs.extend(tabs[platform])
    outputs.extend([bundle, download_notice])

    store_input = store_state if store_state is not None else gr.State({})
    inputs = [model, audience, visit, store_input, results]

    def sync_store(store, name, city):
        value = dict(store or {})
        value.update({"name": name or "", "city": city or ""})
        return value

    event = dict(outputs=[*outputs, *([] if store_state is None else [store_state])],
                 api_visibility="private", concurrency_limit=1, concurrency_id="zhiheng_quick",
                 trigger_mode="once")

    def compose(model_name, audience_name, visit_text, store, previous, *, keep_previous=False):
        """Shared handler: every branch returns exactly one update per output."""
        generated, notice_text = {}, ""
        if not model_name:
            notice_text = "### 先选型号\n从「今天推哪个型号」里挑一个。"
        else:
            card = fact_cards.load_card(model_name)
            if not card:
                notice_text = "### 这个型号还没有事实卡\n请换一个型号，或让总部先补上这个型号的资料。"
            else:
                profile = {"name": (store or {}).get("name", ""), "city": (store or {}).get("city", "")}
                seed = None if keep_previous else int(time.time())
                generated = quick_flow.generate_all(card, audience=audience_name or "",
                                                    visit=visit_text or "", store=profile or None, seed=seed)
                blocked = [result for result in generated.values() if result["status"] == "blocked"]
                if blocked:
                    notice_text = "### 还差一点信息\n" + "；".join(blocked[0]["checks"]["violations"])
                else:
                    ready = sum(1 for result in generated.values() if result["status"] == "ready")
                    notice_text = (f"### 三版已生成\n{ready}/3 版检查通过；逐版看"
                                   "「这篇用到的数字与官方原文」，确认后再发。")
        updates = [generated or (previous or {}), notice_text]
        for platform in quick_flow.PLATFORMS:
            updates.extend(_platform_update(generated.get(platform, {})))
        # 上一轮的素材包作废，避免下载到旧图。
        updates.extend([None, "内容已更新，需要重新打包：点「打包三平台配图与文案 ZIP」。"])
        if store_state is not None:
            updates.append(gr.update())
        return updates

    def download(results_state):
        """没有成稿时说清楚原因，别让人以为按钮坏了。"""
        try:
            path = pack_bundle(results_state or {})
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            return None, f"**打包失败**：{exc}。请重新生成后再试。"
        if not path:
            return None, ("**还没有可打包的内容**：先点「生成三平台成稿」，"
                          "生成完再点这个按钮。")
        size = Path(path).stat().st_size / 1024 / 1024
        return path, f"**素材包已生成（{size:.1f} MB）**：点上面的文件名或右侧下载图标保存。包含三平台文案与配图。"

    generate.click(lambda *args: compose(*args), inputs=inputs, **event)
    again.click(lambda *args: compose(*args, keep_previous=True), inputs=inputs, **event)
    pack.click(download, inputs=[results], outputs=[bundle, download_notice],
               api_visibility="private", queue=False)
    for button, preset in preset_buttons:
        def apply_preset(visit_text=preset["visit"], audience_name=preset["audience"]):
            """点预选卡只填字，不生成；店员还能改成自己看到的细节。"""
            return visit_text, audience_name

        button.click(apply_preset, inputs=[], outputs=[visit, audience],
                     api_visibility="private", queue=False)
    if store_state is not None:
        for component in (store_name, store_city):
            component.input(sync_store, inputs=[store_state, store_name, store_city], outputs=[store_state],
                            api_visibility="private", queue=False)
    return locals()
