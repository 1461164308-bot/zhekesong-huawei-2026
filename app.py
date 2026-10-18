# -*- coding: utf-8 -*-
"""知衡 · 华为PC图文营销智能体的 Gradio 6 界面。

agent 在交互发生时加载；导入本模块和构建界面均不访问外部服务。
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import gradio as gr
from visual_theme import DESKTOP_HTML, DESKTOP_CSS, DESKTOP_JS

APP_TITLE = "知衡 · 华为PC图文营销智能体"
PLATFORMS = ["小红书", "微信公众号", "门店朋友圈", "门店海报"]
SCENARIOS = ["开学季", "职场办公", "内容创作", "家庭换新", "企业采购", "门店到访", "新品首发", "节日营销"]
GOALS = ["种草了解", "选购决策", "到店体验", "企业咨询"]
FALLBACK_PRODUCTS = [
    "HUAWEI MateBook Pro S",
    "HUAWEI MateBook 14 酷睿 Ultra",
    "HUAWEI MateBook D 16 2024",
]

EXAMPLES = [
    {
        "product": FALLBACK_PRODUCTS[0],
        "tokens": ("matebookpros",),
        "audience": "即将入学、希望兼顾课程学习与日常记录的大学生",
        "scenario": "开学季",
        "platform": "小红书",
        "goal": "种草了解",
        "requirements": "语气自然，用学习和校园生活场景展开。只使用有依据的产品信息，不编造价格、优惠或使用体验。",
    },
    {
        "product": FALLBACK_PRODUCTS[1],
        "tokens": ("matebook14", "ultra"),
        "audience": "经常处理文档、参加线上会议的职场办公人群",
        "scenario": "职场办公",
        "platform": "微信公众号",
        "goal": "选购决策",
        "requirements": "表达专业、克制，说明哪些办公需求值得重点关注。给出清楚的配图位置，避免无依据的性能比较。",
    },
    {
        "product": FALLBACK_PRODUCTS[2],
        "tokens": ("matebookd16", "2024"),
        "audience": "近期准备换新电脑、希望先到店体验的本地顾客",
        "scenario": "门店到访",
        "platform": "门店朋友圈",
        "goal": "到店体验",
        "requirements": "短句、亲切，邀请顾客到店了解和体验。未提供门店地址、活动时间和优惠时，不自行补写。",
    },
]

CSS = """
:root {
  --zh-navy: #122b49;
  --zh-teal: #087e83;
  --zh-muted: #5c7185;
  --zh-border: #dce6ed;
}
.gradio-container {
  width: 100% !important;
  min-width: 0 !important;
  box-sizing: border-box;
  max-width: 1440px !important;
  margin: 0 auto !important;
  padding: 26px 28px 18px !important;
  background: #f5f8fb;
  color: #17324d;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif !important;
}
#zh-hero {
  border: 1px solid #274661;
  border-radius: 22px;
  background: linear-gradient(115deg, #102b49 0%, #173d56 63%, #12666b 100%);
  padding: 30px 34px;
  color: #fff;
  position: relative;
  overflow: hidden;
  box-shadow: 0 12px 34px #17324d12;
}
#zh-hero:after {
  content: "";
  position: absolute;
  right: -50px;
  top: -110px;
  width: 320px;
  height: 320px;
  border: 1px solid #a0e7de30;
  border-radius: 50%;
  pointer-events: none;
}
.zh-eyebrow { color: #99e7dc; font-size: 11px; letter-spacing: .16em; font-weight: 650; }
.zh-title { margin: 12px 0 10px; font-size: clamp(24px, 3vw, 34px); line-height: 1.35; font-weight: 720; letter-spacing: .025em; }
.zh-title em { font-style: normal; color: #80e1d3; }
.zh-subtitle { margin: 0; color: #d9e7f0; font-size: 14px; line-height: 1.9; max-width: 860px; }
.zh-pills { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 21px; }
.zh-pills span { padding: 5px 11px; border: 1px solid #a7d7df3d; border-radius: 20px; color: #dfefef; font-size: 11px; background: #ffffff08; }
#zh-guide { margin: 2px 4px 10px; color: var(--zh-muted); font-size: 13px; }
#zh-workspace { gap: 20px; align-items: stretch; }
#zh-inputs, #zh-results { background: #fff; border: 1px solid var(--zh-border); border-radius: 18px; padding: 22px; box-shadow: 0 5px 20px #19355204; }
.zh-section h3 { color: var(--zh-navy); margin: 0 0 5px; font-size: 18px; }
.zh-section p { color: var(--zh-muted); font-size: 12px; line-height: 1.8; margin-bottom: 13px; }
#zh-generate { margin-top: 6px; border-radius: 11px; min-height: 48px; font-size: 15px; font-weight: 650; background: linear-gradient(110deg, #087e83, #07988e); border: 0; color: #fff; box-shadow: 0 4px 12px #087e831c; }
#zh-revise { border-radius: 10px; background: #eaf7f5; color: #126b68; border-color: #c8e9e2; min-height: 42px; }
#zh-examples { gap: 7px; }
#zh-examples button { font-size: 12px; min-width: 100px; border-radius: 9px; color: #365870; background: #f6f9fc; border-color: #e1e9f0; }
#zh-status { background: #f0f7fa; border: 1px solid #ddeaf0; border-radius: 11px; padding: 13px 16px; margin-bottom: 8px; min-height: 48px; }
#zh-status p { margin: 0; color: #36556c; font-size: 13px; line-height: 1.75; }
#zh-status h3 { font-size: 14px; margin: 0 0 5px; color: var(--zh-navy); }
#zh-preview { min-height: 380px; padding: 14px 5px; line-height: 1.9; }
#zh-preview img { max-width: 100%; height: auto; object-fit: contain; border-radius: 10px; }
#zh-report { min-height: 380px; padding: 9px 5px 16px; }
#zh-report h2 { color: #173d56; font-size: 19px; border-bottom: 1px solid #e8eff4; padding-bottom: 9px; margin-top: 24px; }
#zh-report h3 { color: #186b70; font-size: 16px; }
#zh-report p, #zh-report li { line-height: 1.9; }
#zh-tabs { margin-top: 5px; }
#zh-tabs .tab-nav { border-bottom-color: #e0e9ef; gap: 3px; }
#zh-tabs .tab-nav button { font-size: 13px; color: #5c7185; padding: 11px 12px; }
#zh-tabs .tab-nav button.selected { color: #087e83; border-bottom-color: #087e83; }
#zh-images img { object-fit: contain !important; }
#zh-image-sources { font-size: 13px; padding: 6px 2px; }
#zh-connection { border: 1px solid var(--zh-border); border-radius: 13px; background: #fff; margin-top: 6px; }
#zh-connection-body { padding: 4px 2px; font-size: 13px; line-height: 1.8; }
#zh-refresh { min-height: 38px; border-radius: 8px; }
#zh-footer { text-align: center; padding: 9px 6px 1px; font-size: 12px; color: #728497; }
#zh-footer a { color: #377b85; text-decoration: none; }
#zh-footer p { margin: 5px 0; }
.gradio-container .main, .gradio-container .wrap {
  min-width: 0 !important;
  max-width: 100% !important;
  box-sizing: border-box;
}
@media (max-width: 860px) {
  .gradio-container { padding: 14px 12px !important; }
  .gradio-container > .main { padding: 0 !important; }
  #zh-workspace { flex-direction: column; flex-wrap: nowrap; }
  #zh-inputs, #zh-results { min-width: 0 !important; width: 100% !important; box-sizing: border-box; flex: 1 1 auto !important; }
  #zh-connection { flex-direction: column; }
  #zh-connection > .column, .gradio-container .block { min-width: 0 !important; }
  .gradio-container .prose { overflow-wrap: anywhere; }
  #zh-hero { padding: 24px 21px; border-radius: 17px; }
  #zh-inputs, #zh-results { padding: 16px; }
  #zh-workspace { gap: 13px; }
  #zh-report { min-height: 260px; }
}
"""

THEME = gr.themes.Soft(
    primary_hue=gr.themes.colors.teal,
    secondary_hue=gr.themes.colors.blue,
    neutral_hue=gr.themes.colors.slate,
    font=["Inter", "PingFang SC", "Microsoft YaHei", "sans-serif"],
).set(
    body_background_fill="#f5f8fb",
    body_background_fill_dark="#101d2b",
    block_background_fill="#ffffff",
    block_border_color="#dce6ed",
    block_label_text_color="#24475f",
    input_background_fill="#f9fbfd",
    input_border_color="#dce6ed",
    input_radius="9px",
    button_primary_background_fill="#087e83",
    button_primary_background_fill_hover="#086c73",
    button_primary_text_color="#ffffff",
    button_primary_border_color="#087e83",
    block_radius="12px",
)


def _backend():
    return importlib.import_module("agent")


def _safe_text(value: Any) -> str:
    """最后一层展示脱敏；异常对象本身从不送往界面。"""
    text = str(value) if value is not None else ""
    text = re.sub(r"(?i)\bBearer\s+[^\s`<>]+", "Bearer [已隐藏]", text)
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}", "[密钥已隐藏]", text)
    text = re.sub(
        r"(?i)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|authorization|password|client_secret)\s*[=:]\s*[\"']?)[^\s&,;\"'<>`]+",
        r"\1[已隐藏]",
        text,
    )
    text = re.sub(r"https?://[^\s<>\"'\]\)]+", lambda match: _source_link(match.group(0)), text)
    return text


def _safe_json(value: Any, depth: int = 0) -> Any:
    if depth > 10:
        return "…"
    if isinstance(value, dict):
        return {
            _safe_text(key): "[已隐藏]"
            if str(key).lower() in {"api_key", "apikey", "authorization", "token", "access_token", "refresh_token", "secret", "password", "client_secret"}
            else _safe_json(item, depth + 1)
            for key, item in value.items()
            if str(key).lower() not in {"media_id", "headers", "request_headers", "response_headers"}
        }
    if isinstance(value, (list, tuple)):
        return [_safe_json(item, depth + 1) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _safe_text(value)


def _local_file(value: Any, suffixes: set[str]) -> str | None:
    if not isinstance(value, (str, Path)) or not value:
        return None
    try:
        path = Path(value).expanduser()
        return str(path.resolve()) if path.suffix.lower() in suffixes and path.is_file() else None
    except (OSError, RuntimeError, ValueError):
        return None


def _source_link(value: Any) -> str:
    """图源链接只展示公开地址，不回传可能含鉴权信息的查询串。"""
    if not isinstance(value, str):
        return ""
    try:
        url = urlsplit(value)
        if url.scheme not in {"https", "http"} or not url.hostname:
            return ""
        host = url.hostname
        if ":" in host:
            host = f"[{host}]"
        if url.port:
            host += f":{url.port}"
        return urlunsplit((url.scheme, host, url.path, "", ""))
    except ValueError:
        return ""


def _markdown_inline(value: Any) -> str:
    return re.sub(r"([\\`*_{}\[\]<>|])", r"\\\1", _safe_text(value)).replace("\n", " ")


def _image_outputs(images: Any) -> tuple[list, str]:
    gallery, notes = [], []
    if not isinstance(images, list):
        images = []
    for index, image in enumerate(images, 1):
        if not isinstance(image, dict):
            continue
        path = _local_file(image.get("path"), {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"})
        title = _safe_text(image.get("title") or f"配图 {index}")
        caption = _safe_text(image.get("caption") or "")
        placement = _safe_text(image.get("placement") or "请参考完整报告中的图文编排建议")
        if path:
            gallery.append((path, f"{title} · {placement}"))
        source = image.get("source")
        if isinstance(source, dict):
            source_name = source.get("title") or source.get("name") or source.get("filename") or "ima 共享知识库"
            source_url = source.get("url")
        else:
            source_name = source or image.get("source_title") or image.get("source_name") or image.get("document_title") or "ima 共享知识库"
            source_url = None
        url = _source_link(image.get("source_url") or source_url)
        source_label = _markdown_inline(source_name)
        if url:
            source_label = f"[{source_label}](<{url}>)"
        lines = [f"**{index}. {_markdown_inline(title)}**", f"- 来源：{source_label}", f"- 建议位置：{_markdown_inline(placement)}"]
        if caption:
            lines.append(f"- 配图说明：{_markdown_inline(caption)}")
        if not path:
            lines.append("- 图片状态：本地图片暂不可用，请查看报告中的配图说明。")
        notes.append("\n".join(lines))
    if not notes:
        return [], "本次未返回可展示的 同型号知识库配图。请查看报告中的说明，或补充产品信息后重试。"
    return gallery, "\n\n".join(notes)


def _trace_rows(trace: Any) -> list[list]:
    rows = []
    if not isinstance(trace, list):
        return rows
    labels = {"ready": "完成", "completed": "完成", "success": "完成", "running": "进行中", "blocked": "待处理", "error": "异常", "skipped": "跳过"}
    for item in trace:
        if not isinstance(item, dict):
            continue
        try:
            seconds = round(float(item.get("elapsed_ms", 0) or 0) / 1000, 2)
        except (TypeError, ValueError, OverflowError):
            seconds = 0
        status = _safe_text(item.get("status", ""))
        rows.append([_safe_text(item.get("step", "")), labels.get(status, status), _safe_text(item.get("detail", "")), seconds])
    return rows


def _notice_result(message: str, status: str = "needs_clarification") -> dict:
    return {
        "status": status,
        "report": (
            f"## 一、需求与策略\n\n{message}\n\n"
            "## 二、最终文案\n\n暂未生成可发布文案。\n\n"
            "## 三、配图与编排\n\n暂未生成配图方案。\n\n"
            "## 四、来源与核验\n\n请完成上述处理后重新生成。"
        ),
        "copy_text": "",
        "strategy": {},
        "facts": [],
        "images": [],
        "checks": {"状态": "待处理", "说明": message},
        "trace": [],
    }


def _render_result(result: dict, request: dict) -> tuple:
    status = result.get("status", "error")
    notices = {
        "ready": "### ✓ 图文方案已生成\n先阅读报告与核验结果，再复制文案、选用配图或下载方案。",
        "needs_clarification": "### ◇ 请先补充信息\n请查看下方报告中的追问，完善左侧需求后再次生成。",
        "blocked": "### ◇ 本次生成暂未完成\n请按报告中的提示处理连接、授权或资料问题，再重试。",
        "error": "### ◇ 本次生成遇到问题\n请查看报告中的处理建议，稍后重试或刷新连接状态。",
    }
    if status not in notices:
        result = _notice_result("生成服务返回的结果暂不可用，请稍后重试。", "error")
        status = "error"
    gallery, image_notes = _image_outputs(result.get("images", []))
    ready = status == "ready" and bool(result.get("copy_text"))
    return (
        notices[status],
        _safe_text(result.get("report") or "本次未返回报告，请稍后重试。"),
        _safe_text(result.get("copy_text", "")),
        gallery,
        image_notes,
        _safe_json(result.get("checks", {})),
        _safe_json(result.get("facts", [])),
        _safe_json(result.get("strategy", {})),
        _trace_rows(result.get("trace", [])),
        _local_file(result.get("export_markdown"), {".md", ".markdown"}),
        _local_file(result.get("export_json"), {".json"}),
        request if ready else {},
        gr.update(interactive=ready),
        # preview_html 由 agent 转义文本并内嵌 ima 图片；保留可信的 HTML 与 base64 图片。
        str(result.get("preview_html") or "<p>本次暂无图文成稿预览，请查看完整报告中的说明。</p>"),
    )


def _run(request: dict, revision: str = "", progress=None) -> tuple:
    if not request.get("product"):
        return _render_result(_notice_result("请选择或输入产品型号。型号暂不明确时，可以填写 MateBook 等线索，由智能体进一步追问。"), {})
    if not request.get("audience"):
        return _render_result(_notice_result("请补充目标人群，例如：准备开学的大学生，或经常移动办公的职场人。"), {})
    for field, values, label in (("scenario", SCENARIOS, "使用场景"), ("platform", PLATFORMS, "发布渠道"), ("goal", GOALS, "营销目标")):
        if request.get(field) not in values:
            return _render_result(_notice_result(f"请选择有效的{label}。"), {})
    if any(len(value) > 6000 for value in [*request.values(), revision]):
        return _render_result(_notice_result("单项输入过长，请将需求或修改说明精简到 6000 字以内。"), {})

    def report_progress(value, description=""):
        if progress is None:
            return
        try:
            progress(max(0.0, min(1.0, float(value))), desc=_safe_text(description)[:180])
        except (TypeError, ValueError):
            pass

    try:
        report_progress(0.02, "正在理解需求…")
        result = _backend().run_task(**request, revision=revision, progress=report_progress)
        if not isinstance(result, dict):
            result = _notice_result("生成服务返回的结果暂不可用，请稍后重试。", "error")
        output = _render_result(result, request)
        report_progress(1.0, "处理完成")
        return output
    except Exception:
        # 不在公开界面或异常堆栈中暴露请求 URL、账号凭据及第三方响应。
        return _render_result(_notice_result("生成服务暂时不可用。请刷新下方连接状态，确认知识库与模型可用后重试。", "error"), {})


def generate_copy(product, audience, scenario, platform, goal, requirements, progress=gr.Progress()):
    request = {
        "product": (product or "").strip(),
        "audience": (audience or "").strip(),
        "scenario": (scenario or "").strip(),
        "platform": (platform or "").strip(),
        "goal": (goal or "").strip(),
        "requirements": (requirements or "").strip(),
    }
    return _run(request, progress=progress)


def revise_copy(revision, previous_request, progress=gr.Progress()):
    revision = (revision or "").strip()
    if not previous_request:
        return _render_result(_notice_result("请先生成一份图文方案，再填写修改要求进行重写。"), {})
    if not revision:
        return ("### ◇ 请填写修改要求\n例如：将文案缩短到 150 字，并把到店邀请放在结尾。", *(gr.update() for _ in range(13)))
    output = list(_run(dict(previous_request), revision=revision, progress=progress))
    output[11] = previous_request
    output[12] = gr.update(interactive=True)
    return tuple(output)


def refresh_connection(current_product, current_catalog):
    catalog = list(current_catalog or FALLBACK_PRODUCTS)
    notes = []
    try:
        backend = _backend()
    except Exception:
        return "**连接状态暂不可用**\n\n请稍后点击刷新。仍可先填写需求，生成时会显示具体处理建议。", gr.update(choices=catalog, value=current_product or None), catalog
    try:
        connection = _safe_text(backend.get_connection_status())
    except Exception:
        connection = "**暂未取得连接状态。** 请稍后刷新，确认授权账号、共享知识库与模型连接。"
    try:
        products = backend.get_products()
        if isinstance(products, list):
            products = list(dict.fromkeys(item.strip() for item in products if isinstance(item, str) and item.strip()))
            if products:
                catalog = products
            else:
                notes.append("产品目录暂为空；可输入型号，生成时将进一步确认。")
    except Exception:
        notes.append("暂未刷新产品目录；可输入型号，或稍后重新刷新。")
    if notes:
        connection += "\n\n" + " ".join(notes)
    return connection, gr.update(choices=catalog, value=current_product or None), catalog


def _example_product(example: dict, catalog: list[str]) -> str:
    def normalize(value):
        return re.sub(r"[\W_]", "", value.lower().replace("huawei", ""))

    target = normalize(example["product"])
    for name in catalog or []:
        if normalize(name) == target:
            return name
    for name in catalog or []:
        if all(token in normalize(name) for token in example["tokens"]):
            return name
    # 不把样例静默替换成其他型号；未知型号交由后端澄清。
    return example["product"]


def load_example(index: int, catalog: list[str]) -> tuple:
    example = EXAMPLES[index]
    return (_example_product(example, catalog), *(example[key] for key in ("audience", "scenario", "platform", "goal", "requirements")))


def build_demo() -> gr.Blocks:
    # Gradio 6 的主题与 CSS 由 launch 接收，不传入 Blocks。
    with gr.Blocks(title=APP_TITLE, analytics_enabled=False) as app:
        catalog_state = gr.State(list(FALLBACK_PRODUCTS))
        request_state = gr.State({})
        gr.HTML(DESKTOP_HTML)
        gr.Markdown("## 知衡 · 华为PC图文营销智能体\n自研流程完成客户洞察、事实检索、图文创作、门店演示与独立核验。", elem_id="zh-app-title")
        gr.Markdown("选产品、填人群 → 生成图文方案 → 核对来源后复制、下载；需要调整时，填写修改要求重写。", elem_id="zh-guide")
        with gr.Row(elem_id="zh-connection"):
            with gr.Column(scale=8):
                connection = gr.Markdown("正在核对资料模式与共享库授权…", elem_id="zh-connection-body")
            with gr.Column(scale=1, min_width=130):
                refresh_button = gr.Button("刷新资料状态", size="sm", elem_id="zh-refresh")
        with gr.Row(elem_id="zh-workspace"):
            with gr.Column(scale=4, min_width=310, elem_id="zh-inputs"):
                gr.Markdown("### 01 / 描述这次营销需求\n从一个具体的人群和场景开始。", elem_classes="zh-section")
                product = gr.Dropdown(
                    choices=FALLBACK_PRODUCTS,
                    value=None,
                    label="产品型号",
                    info="支持直接输入；型号不明确时，智能体会进一步追问。",
                    allow_custom_value=True,
                    filterable=True,
                    interactive=True,
                )
                audience = gr.Textbox(label="目标人群", placeholder="例如：准备开学、注重学习效率的大学生", lines=2, max_lines=4)
                with gr.Row():
                    scenario = gr.Dropdown(choices=SCENARIOS, value="开学季", label="营销场景", interactive=True)
                    platform = gr.Dropdown(choices=PLATFORMS, value="小红书", label="发布渠道", interactive=True)
                goal = gr.Dropdown(choices=GOALS, value="种草了解", label="营销目标", interactive=True)
                requirements = gr.Textbox(
                    label="补充要求 / 华为官方商城商品链接（选填）",
                    placeholder="语气、篇幅、门店信息，或 https://www.vmall.com/product/商品编号.html",
                    lines=3,
                    max_lines=6,
                )
                generate_button = gr.Button("生成图文方案  →", variant="primary", elem_id="zh-generate")
                gr.Markdown("**试试这三个场景** · 点击只填入需求", elem_classes="zh-section")
                with gr.Row(elem_id="zh-examples"):
                    example_buttons = [gr.Button(label, size="sm", min_width=100) for label in ["开学季 · 小红书", "办公选购 · 公众号", "门店体验 · 朋友圈"]]
                with gr.Accordion("修改这份方案", open=True):
                    revision = gr.Textbox(
                        label="修改要求",
                        placeholder="例如：缩短至 150 字，语气更自然，把到店邀请放在结尾。",
                        info="沿用最近一次生成的需求；更换产品或人群后，请重新生成。",
                        lines=2,
                    )
                    revise_button = gr.Button("按修改要求重写", interactive=False, elem_id="zh-revise")
            with gr.Column(scale=7, min_width=360, elem_id="zh-results"):
                gr.Markdown("### 02 / 查看图文方案\n从内容到依据，在同一处完成检查与交付。", elem_classes="zh-section")
                status_output = gr.Markdown("### 准备好，让知识变成内容\n填写左侧需求，或先选择一个场景示例。", elem_id="zh-status")
                with gr.Tabs(elem_id="zh-tabs"):
                    with gr.Tab("图文成稿预览"):
                        preview = gr.HTML(
                            '<div style="padding:28px 16px;color:#5c7185;text-align:center">'
                            '<p style="font-size:18px;color:#173d56;font-weight:600">让文字与图片，一起讲清产品价值。</p>'
                            '<p>生成后，在这里预览按段落编排的文案与 同型号知识库配图。</p></div>',
                            elem_id="zh-preview",
                        )
                    with gr.Tab("完整报告"):
                        report = gr.Markdown(
                            "## 你的下一份营销内容，从这里开始\n\n生成后将展示需求策略、最终文案、图文编排与来源核验。\n\n"
                            "> 具体产品参数、价格与活动信息以可核验资料为依据；信息不足时会先向你追问。",
                            elem_id="zh-report",
                        )
                    with gr.Tab("最终文案"):
                        copy_text = gr.Textbox(label="可复制文案", value="", placeholder="生成后在这里直接复制文案。", lines=20, max_lines=35, buttons=["copy"], interactive=False)
                    with gr.Tab("知识库配图"):
                        gr.Markdown("配图只取自同型号共享库资料。实时 ima、ima 缓存或获授权主办方归档模式以页面状态和核验记录为准。")
                        gallery = gr.Gallery(label="知识库同型号原图",  columns=2, rows=2, height=430, object_fit="contain", show_label=False, elem_id="zh-images")
                        image_sources = gr.Markdown("生成后展示图片来源、说明与建议插入位置。", elem_id="zh-image-sources")
                    with gr.Tab("事实与核验"):
                        checks = gr.JSON(label="核验结果", value={"说明": "生成后展示事实、表达与图文核验结果。"})
                        with gr.Accordion("查看引用事实", open=False):
                            facts = gr.JSON(label="事实依据", value=[])
                        with gr.Accordion("查看营销策略", open=False):
                            strategy = gr.JSON(label="策略", value={})
                    with gr.Tab("执行与下载"):
                        trace = gr.Dataframe(headers=["阶段", "状态", "说明", "耗时（秒）"], datatype=["str", "str", "str", "number"], value=[], interactive=False, wrap=True, label="执行轨迹")
                        gr.Markdown("**下载完整方案** · Markdown 便于编辑，JSON 便于保存结构化结果。")
                        with gr.Row():
                            markdown_file = gr.File(label="Markdown 报告", file_types=[".md", ".markdown"], interactive=False)
                            json_file = gr.File(label="JSON 结果", file_types=[".json"], interactive=False)
        gr.Markdown(
            "知衡意为知识来源与核验 · 浙客松 2026 参赛作品，由团队独立开发，非华为官方产品。\n\n"
            "[GitHub](https://github.com/xiaoma-iqoo/zhekesong-huawei-2026) · "
            "[ModelScope 创空间](https://www.modelscope.cn/studios/xiaoma2008/zhekesong-huawei-2026)",
            elem_id="zh-footer",
        )
        inputs = [product, audience, scenario, platform, goal, requirements]
        outputs = [status_output, report, copy_text, gallery, image_sources, checks, facts, strategy, trace, markdown_file, json_file, request_state, revise_button, preview]
        generate_button.click(
            generate_copy,
            inputs=inputs,
            outputs=outputs,
            api_name="generate_copy",
            concurrency_limit=1,
            concurrency_id="zhiheng_generation",
            trigger_mode="once",
            show_progress="full",
        )
        revise_button.click(
            revise_copy,
            inputs=[revision, request_state],
            outputs=outputs,
            api_name="revise_copy",
            concurrency_limit=1,
            concurrency_id="zhiheng_generation",
            trigger_mode="once",
            show_progress="full",
        )
        for index, button in enumerate(example_buttons):
            def fill_example(catalog, index=index):
                return load_example(index, catalog)

            button.click(fill_example, inputs=[catalog_state], outputs=inputs, api_visibility="private", queue=False)
        connection_inputs = [product, catalog_state]
        connection_outputs = [connection, product, catalog_state]
        refresh_button.click(refresh_connection, inputs=connection_inputs, outputs=connection_outputs, api_visibility="private", concurrency_limit=1, concurrency_id="zhiheng_generation", trigger_mode="once")
        app.load(refresh_connection, inputs=connection_inputs, outputs=connection_outputs, api_visibility="private", concurrency_limit=1, concurrency_id="zhiheng_generation")
    return app


demo = build_demo()
demo.queue(default_concurrency_limit=1, max_size=8, api_open=False)

if __name__ == "__main__":
    demo.launch(theme=THEME, css=CSS + DESKTOP_CSS, js=DESKTOP_JS, max_threads=2, show_error=False)
