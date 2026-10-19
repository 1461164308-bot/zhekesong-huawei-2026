"""ZhiHeng: retrieval -> grounded facts -> platform writing -> independent review.

No bundled product answers or fixed marketing results. Every successful run uses
live ima material or an explicitly authorized archive, optionally supplemented by
verified Huawei Mall product pages, plus independent model calls. Credentials are only
read from server environment and never included in the result or exported files.
"""
from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import html
import threading
import json
import os
from pathlib import Path
import tempfile
import time

from ima_client import IMAClient, IMAError
from llm_client import DEFAULT_MODEL, LLMClient, ModelError, server_api_configured
from policy import (PLATFORM_RULES, SCENE_RULES, draft_units, evidence_facts,
                    normalize, strategy_for, text_violations, validate_inputs)
from prompts import EXTRACT_PROMPT, COMPOSE_PROMPT, AUDIT_PROMPT, FACT_REVIEW_PROMPT
from preview import build_preview
from public_payload import sanitize_public
from vmall_client import VmallError, fetch_vmall_sources
from creation_flow import (FlowError, digest, make_plan, normalize_plan, request_key)
from style_cards import normalize_style
from platform_delivery import export_delivery
from PIL import Image

PLATFORMS = list(PLATFORM_RULES)
SCENARIOS = list(SCENE_RULES)
VERSION = "1.0.0"


_SESSION_IMA: ContextVar[dict | None] = ContextVar("zhiheng_session_ima", default=None)
_SESSION_CLIENTS: OrderedDict[str, IMAClient] = OrderedDict()
_SESSION_LOCK = threading.Lock()


def resolve_ima_config(raw: dict | None) -> dict | None:
    """Validate a user's per-session live ima settings; empty means use the default source.

    The result lives only in that user's Gradio session state: never written to
    disk, exported, logged or echoed back to the page.
    """
    if not isinstance(raw, dict):
        return None
    client_id = str(raw.get("client_id", "") or "").strip()
    api_key = str(raw.get("api_key", "") or "").strip()
    kb_name = str(raw.get("kb_name", "") or "").strip()
    if not client_id and not api_key and not kb_name:
        return None
    if not client_id or not api_key or not kb_name:
        raise IMAError("实时 ima 需要同时填写 ClientID、API Key 和共享知识库名称。")
    if len(client_id) > 200 or len(api_key) > 400 or len(kb_name) > 120:
        raise IMAError("ima 配置过长，请检查后重试。")
    if any(ch in value for value in (client_id, api_key) for ch in " \t\r\n"):
        raise IMAError("ClientID 与 API Key 不能包含空白字符。")
    return {"client_id": client_id, "api_key": api_key, "kb_name": kb_name}


@contextmanager
def ima_session(config: dict | None):
    """Route every _ima() call in this block to the session's live ima settings."""
    token = _SESSION_IMA.set(config or None)
    try:
        yield
    finally:
        _SESSION_IMA.reset(token)


def _session_client(config: dict) -> IMAClient:
    # Reuse a bounded set of clients so catalog and knowledge-base lookups stay cached.
    key = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
    with _SESSION_LOCK:
        client = _SESSION_CLIENTS.get(key)
        if client is None:
            client = IMAClient(client_id=config["client_id"], api_key=config["api_key"], kb_name=config["kb_name"])
            _SESSION_CLIENTS[key] = client
            while len(_SESSION_CLIENTS) > 8:
                _SESSION_CLIENTS.popitem(last=False)
        else:
            _SESSION_CLIENTS.move_to_end(key)
        return client


def _ima() -> IMAClient:
    session = _SESSION_IMA.get()
    if session:
        # User-supplied live ima always wins and never falls back to local material.
        return _session_client(session)
    from knowledge_store import get_archive_path, get_workspace_archive
    explicit = "IMA_SOURCE_MODE" in os.environ
    archive_configured = any(key in os.environ for key in ("IMA_ARCHIVE_PATH", "IMA_ARCHIVE_URL", "IMA_ARCHIVE_SHA256", "IMA_ARCHIVE_TOKEN"))
    mode = os.environ.get("IMA_SOURCE_MODE", "archive" if archive_configured else "live").strip().lower()
    if mode not in {"live", "archive"}:
        raise IMAError("资料模式配置无效，请部署者将 IMA_SOURCE_MODE 设为 live 或 archive。")
    client = IMAClient()
    workspace = False
    path = None
    if not explicit and not archive_configured:
        path = get_workspace_archive()
        workspace = bool(path)
    if mode == "archive":
        path = get_archive_path()
        if not path:
            raise IMAError("显式归档配置无效或缓存尚未就绪，请检查 IMA_ARCHIVE_PATH / URL 与私有存储配置；未自动使用工作区资料。")
    if path:
        client.load_archive(path)
        client._workspace_authorized = workspace
    return client


def get_products() -> list[str]:
    try:
        return _ima().catalog()
    except Exception:
        return []


def get_connection_status() -> str:
    try:
        state = _ima().connection_status()
        if state.get("workspace_authorized"):
            message = "**工作区授权知识库 · 本地只读 · 非实时 ima**  \n资料仅用于获授权工作流，读取时间不代表资料更新日期。"
        elif state.get("offline_archive"):
            message = ("**主办方 ZIP 缓存模式 · 非实时 ima 检索**  \n"
                       f"资料对应：{html.escape(state.get('kb_name', '指定共享知识库'))}；"
                       "本部署按用户授权使用主办方同库资料包；原文配额恢复后可由部署者切回实时模式。")
        elif state.get("connected"):
            message = (f"**ima 已连接** · {html.escape(state.get('kb_name', '指定共享知识库'))}  \n"
                       f"授权账号：{html.escape(state.get('account_label', '已授权账号'))} · "
                       f"角色：{html.escape(str(state.get('role', '已授权成员')))}")
        else:
            message = "**ima 尚未连接** · " + html.escape(state.get("message", "请联系部署者核对服务端凭证与共享库权限。"))
    except IMAError as exc:
        message = "**知识库来源未就绪** · " + html.escape(str(exc))
    except Exception:
        message = "**ima 暂未连接** · 请刷新连接状态，或联系部署者核对共享库权限。"
    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)
    model_state = (f"模型配置就绪（{html.escape(model)}；生成时实际连接）" if server_api_configured()
                   else "未内置模型 API · 请在左侧「00 / 模型 API 设置」填写你自己的服务地址与密钥")
    return message + "  \n" + model_state + " · 允许华为官方商城商品页补充事实，是否读取以本次核验记录为准；图源仍为同型号授权知识库。"


def _empty(status: str, report: str, trace: list | None = None, **extra) -> dict:
    result = {"status": status, "report": report, "copy_text": "", "strategy": {},
              "facts": [], "images": [], "checks": {"publication": "未交付可发布文案"},
              "trace": trace or [], "export_markdown": None, "export_json": None, "preview_html": ""}
    result.update(extra)
    return sanitize_public(result)


def _displayable_image(image: dict) -> bool:
    try:
        path = Path(str(image.get("path", "")))
        if not path.is_file():
            return False
        with Image.open(path) as picture:
            if picture.width * picture.height > 40_000_000:
                return False
            picture.load()
        return True
    except (OSError, ValueError, Image.DecompressionBombError):
        return False


def _origin_label(origin: str) -> str:
    return {"live_ima": "实时 ima", "ima_cache": "ima 已检索缓存",
            "offline_archive": "主办方 ZIP 缓存（非实时 ima）",
            "official_vmall": "华为官方商城本次读取"}.get(origin, "未识别来源")


def _public_sources(sources: list[dict]) -> list[dict]:
    # Do not expose signed ima download URLs, request headers, or media IDs.
    return [{"id": s["id"], "title": s.get("title", ""),
             "official_url": _public_url(s.get("official_url", "")),
             "retrieved_at": s.get("retrieved_at", ""),
             "origin": s.get("origin", "live_ima")} for s in sources]


def _public_url(value: str) -> str:
    from urllib.parse import urlsplit
    try:
        parsed = urlsplit(str(value))
        if parsed.scheme != "https" or not parsed.hostname or parsed.query or parsed.username:
            return ""
        if not any(parsed.hostname == d or parsed.hostname.endswith("." + d) for d in ("huawei.com", "vmall.com")):
            return ""
        return str(value)
    except ValueError:
        return ""


def _format_copy(units: list[dict], product: str, strategy: dict) -> str:
    chunks = []
    for unit in units:
        if unit["id"].startswith("demo_"):
            continue
        text = unit["text"].strip()
        if not text:
            continue
        if unit["id"] == "title":
            chunks.append(text)
        elif unit["id"].startswith("section_"):
            heading = unit.get("heading", "").strip()
            refs = " ".join(f"[{f}]" for f in unit.get("fact_ids", []))
            chunks.append((heading + "\n" if heading else "") + text + (" " + refs if refs else ""))
        else:
            refs = " ".join(f"[{f}]" for f in unit.get("fact_ids", []))
            chunks.append(text + (" " + refs if refs else ""))
    return "\n\n".join(chunks)


def _report(task: dict, strategy: dict, facts: list[dict], copy: str, images: list[dict], checks: dict, sources: list[dict]) -> str:
    lines = ["## 一、场景判断", f"**产品：** {task['product']}  ",
             f"**目标人群 / 使用场景：** {task['audience']} / {task['scenario']}  ",
             f"**内容目标 / 平台：** {task['goal']} / {task['platform']}",
             f"\n**用户问题：** {strategy['pain']}",
             f"\n**本次切入点：** {strategy.get('angle', strategy['pain'])}",
             "\n**卖点顺序：** " + " → ".join(strategy.get("selected_priorities", strategy['priorities'])),
             f"\n**平台策略：** {strategy['structure']}；{strategy['tone']}；目标 {strategy['body_target']}；配图 {len(images)} 张。",
             ]
    insight = strategy.get("customer_insight", {})
    if isinstance(insight, dict) and insight:
        lines.append("\n### 客户洞察卡")
        for key, label in (("situation", "客户处境"), ("decision_barrier", "决策阻力"), ("empathy_anchor", "共情切入")):
            if insight.get(key):
                lines.append(f"\n**{label}：** {insight[key]}")
        for key, label in (("basis", "判断依据（推测需确认）"), ("questions", "到店先问")):
            if insight.get(key):
                lines.append(f"\n**{label}：** " + "；".join(str(x) for x in insight[key][:4]))
    lines.append("\n## 二、知识依据")
    for f in facts:
        lines.append(f"\n**[{f['id']}] {f['statement']}**  \n来源：[{f['source_id']}] {f['source_title']}")
        lines.append("\n> " + f['quote'].replace("\n", "\n> "))
        if f.get("conditions"):
            lines.append("\n适用条件：" + "；".join(f["conditions"]))
    mode_label = checks.get("data_mode_label", "ima 检索")
    lines += [f"\n**来源清单（{mode_label}）：**"]
    for s in _public_sources(sources):
        line = f"- [{s['id']}] {s['title']} · {_origin_label(s['origin'])}"
        if s["retrieved_at"]:
            line += f" · 读取时间：{s['retrieved_at']}"
        if s["official_url"]:
            link_label = "华为官方商城商品页" if s["origin"] == "official_vmall" else "资料标注的官方入口"
            line += f" · [{link_label}]({s['official_url']})"
        lines.append(line)
    lines += ["\n## 三、图文软文", "\n" + copy]
    if strategy.get("demo_steps"):
        lines.append("\n### 门店演示脚本（经审核）")
        for n, demo in enumerate(strategy["demo_steps"], 1):
            refs = " ".join(f"[{x}]" for x in demo.get("fact_ids", []))
            lines.append(f"\n**第{n}步 · 操作：** {demo['action']}  \n**可照读话术：** {demo['speech']}  \n**让顾客确认：** {demo['observe']} {refs}")
    lines.append("\n### 配图方案")
    for i in images:
        image_origin = _origin_label(i.get("origin", "live_ima"))
        lines.append(f"\n**[{i['id']}] {i['title']}**  \n来源：{image_origin}「{i.get('source_title', '')}」；型号：{i['model']}  \n插入位置：{i['placement']}  \n说明：{i['caption']}")
        if _public_url(i.get("url", "")):
            lines.append(f"\n[查看素材原始官方地址]({_public_url(i['url'])})")
    if not images:
        lines.append("\n未找到可验证的同型号图片，本次没有使用其他型号或外部配图。")
    lines += ["\n## 四、核验结果", f"\n**交付状态：** {checks['publication']}",
              f"\n- 资料模式：{mode_label}。缓存读取时间不等于资料发布日期。",
              f"- 产品事实：{checks['accepted_facts']} 项事实通过逐字来源校验及独立证据复核；正文单元通过独立模型审核及规则检查。",
              f"- 图片型号：{len(images)} 张图来自{checks.get('image_mode_label', mode_label)}中的同型号目录；未使用其他型号或外部搜索配图。",
              "- 合规：未核实的价格、补贴、库存和赠品不进入文案；不伪造体验，不使用无依据对比。",
              "- 校验范围：本次检索资料及模型/规则复核，不等同于法律审查或当天销售政策核验。"]
    if checks.get("removed_facts"):
        lines.append("\n**证据复核删除的候选事实：**")
        for x in checks["removed_facts"]:
            lines.append(f"- {x['id']}：{x['reason']}")
    if checks.get("removed_units"):
        lines.append("\n**本次拦截与删减：**")
        for x in checks["removed_units"]:
            lines.append(f"- {x['id']}：{x['reason']}")
    if checks.get("rejected_requests"):
        lines.append("\n**未执行的要求：** " + "；".join(checks["rejected_requests"]))
    if checks.get("pending"):
        lines.append("\n**待确认信息：**")
        lines.extend("- " + str(x) for x in checks["pending"])
    if checks.get("warnings"):
        lines.append("\n**资料与核验提示：**")
        lines.extend("- " + str(x) for x in dict.fromkeys(checks["warnings"]))
    return "\n".join(lines)


def run_task(product: str, audience: str, scenario: str, platform: str, goal: str,
             requirements: str = "", revision: str = "", progress=None, *,
             phase: str = "final", style_card: dict | None = None,
             approved_plan: dict | None = None, prepared: dict | None = None,
             api_config: dict | None = None) -> dict:
    """Read evidence for an idea, or write/review a final using approved evidence.

    The GUI enforces brief/style/idea/final approvals in its per-session flow.
    Legacy internal callers can still run the complete audited pipeline.
    """
    started = time.perf_counter()
    trace: list[dict] = []
    stage_start = started

    def step(name: str, fraction: float, detail: str):
        nonlocal stage_start
        now = time.perf_counter()
        trace.append({"step": name, "status": "完成", "detail": detail,
                      "elapsed_ms": round((now-stage_start)*1000)})
        stage_start = now
        if progress:
            try:
                progress(fraction, detail)
            except Exception:
                pass

    product, audience = str(product or "").strip()[:180], str(audience or "").strip()[:300]
    requirements, revision = str(requirements or "").strip()[:2500], str(revision or "").strip()[:1500]
    goal = str(goal or "种草了解")[:120]
    if not product or not audience or not scenario or not platform:
        fields = [name for name, value in [("准确产品型号", product), ("目标人群", audience), ("使用场景", scenario), ("发布平台", platform)] if not value]
        return _empty("needs_clarification", "### 请先补充任务\n\n" + "\n".join("- " + x for x in fields))
    if not api_config and not server_api_configured():
        return _empty("needs_clarification",
                      "### 请先配置模型 API\n\n本应用不内置任何密钥。请在页面「00 / 模型 API 设置」填写你自己的 "
                      "OpenAI 兼容服务地址与密钥并点击「应用自定义 API」，然后再生成。", trace)
    try:
        input_key = request_key({"product": product, "audience": audience, "scenario": scenario,
                                 "platform": platform, "goal": goal, "requirements": requirements})
        card = normalize_style(style_card) if style_card is not None else None
        if prepared is not None:
            if (phase != "final" or prepared.get("input_key") != input_key
                    or prepared.get("style_key") != digest(card)
                    or time.time() - prepared.get("created_at", 0) > 3600):
                raise FlowError("需求、风格或资料确认已失效，请重新生成并确认思路。")
            if not approved_plan:
                raise FlowError("请先确认创作思路。")
            task, strategy = prepared["task"].copy(), prepared["strategy"].copy()
            product = task["product"]
            facts, images = prepared["facts"], prepared["images"]
            if any(not _displayable_image(image) for image in images):
                raise FlowError("已确认的配图暂不可读，请重新生成思路。")
            sources, extracted = prepared["sources"], prepared["extracted"]
            result = {"warnings": prepared.get("retrieval_warnings", [])}
            mode, mode_label = prepared["mode"], prepared["mode_label"]
            knowledge_mode = prepared["knowledge_mode"]
            mall_sources = prepared["mall_sources"]
            rejected, evidence_removed = prepared["rejected"], prepared["evidence_removed"]
            image_meta = [{k: image.get(k, "") for k in ("id", "title", "caption", "model")} for image in images]
            model = LLMClient(api_config) if api_config else LLMClient()
            trace.extend(prepared.get("trace", []))
            step("用户确认", 0.5, "需求、风格卡和创作思路已确认；使用思路阶段已核验的事实与配图。")
        else:
            products = get_products()
            if not products:
                return _empty("error", "### 暂未能读取产品目录\n\n请刷新连接状态；本次没有用外部资料或预置答案代替 ima。", trace)
            canonical, questions = validate_inputs(product, audience, scenario, platform, products)
            if questions:
                return _empty("needs_clarification", "### 需要先确认的信息\n\n" + "\n".join("- " + q for q in questions), trace)
            product = canonical
            source_requests = requirements + "\n" + revision
            task = sanitize_public({"product": product, "audience": audience, "scenario": scenario, "platform": platform,
                                    "goal": goal, "requirements": requirements, "revision": revision})
            audience, requirements = task["audience"], task["requirements"]
            strategy = strategy_for(audience, scenario, platform, task["goal"])
            step("场景与平台策略", 0.1, f"已确定{scenario}的使用问题与{platform}的结构/配图规则。")
            result = _ima().retrieve(product, query=f"{scenario} {audience} {requirements}", max_sources=5,
                                      max_images=strategy["image_max"])
            if normalize(result.get("product", "")) != normalize(product):
                return _empty("blocked", "### 型号核对未通过\n\n检索返回的型号与任务不一致，本次停止生成，请重新选择准确型号。", trace)
            mode = result.get("retrieval_mode", "live_ima")
            valid_origins = {"live_ima", "ima_cache", "offline_archive"}
            origins = {item.get("origin", mode) for item in result.get("sources", []) + result.get("images", [])}
            source_mismatch = (mode not in valid_origins | {"mixed"}
                               or bool(result.get("offline_archive", False)) != (mode == "offline_archive")
                               or not origins <= valid_origins
                               or (mode != "mixed" and bool(origins - {mode}))
                               or (mode == "mixed" and "offline_archive" in origins))
            if source_mismatch:
                return _empty("blocked", "### 资料来源模式未通过核对\n\n返回的来源标记未知或互相矛盾，请部署者检查配置；本次未调用写作模型。", trace)
            knowledge_mode = mode
            mode_label = {"live_ima": "实时 ima", "ima_cache": "ima 已检索缓存",
                          "offline_archive": "主办方 ZIP 缓存（非实时 ima）", "mixed": "ima 检索与缓存混合"}[mode]
            sources = [s.copy() for s in result.get("sources", []) if s.get("text")]
            mall_sources = fetch_vmall_sources(product, source_requests)
            used_source_ids = {s["id"] for s in sources}
            next_source = 1
            for source in mall_sources:
                while f"S{next_source}" in used_source_ids:
                    next_source += 1
                source = source.copy()
                source["id"] = f"S{next_source}"
                used_source_ids.add(source["id"])
                sources.append(source)
            if mall_sources:
                mode = "mixed"
                mode_label += " + 华为官方商城本次读取"
            if not sources:
                return _empty("blocked", "### 没有可用的事实依据\n\n未能获取该型号的授权知识库正文或华为官方商城商品正文，本次停止生成。请确认资料权限或提供准确的官方商城商品页链接。", trace)
            images = [i.copy() for i in result.get("images", []) if normalize(i.get("model", "")) == normalize(product)
                      and _displayable_image(i)]
            if len(images) < strategy["image_min"]:
                return _empty("needs_clarification", f"### 同型号配图数量不足\n\n{platform}需要至少{strategy['image_min']}张图片，本次只有{len(images)}张可验证的同型号素材。请补充获授权的同型号图库，或换用图片数量要求较少的平台。\n\n没有使用其他型号图片凑数。", trace,
                              strategy=strategy, checks={"publication": "配图不足，未交付文案"})
            step("资料与配图检索", 0.3, f"{mode_label}：已读取{len(sources)}份型号资料（含{len(mall_sources)}份官方商城正文）、{len(images)}张知识库同型号原图。")
            model = LLMClient(api_config) if api_config else LLMClient()
            # Full per-product facts/limits are supplied; historical marketing/price docs are not trusted facts.
            payload_sources = [{"id": s["id"], "title": s["title"], "kind": s.get("kind", "facts"),
                                "origin": s.get("origin", knowledge_mode),
                                "official_url": _public_url(s.get("official_url", "")),
                                "retrieved_at": s.get("retrieved_at", ""),
                                "text": s["text"][:26000]} for s in sources if s.get("kind") != "price"]
            image_meta = [{k: i.get(k, "") for k in ("id", "title", "caption", "model")} for i in images]
            extracted = model.json(EXTRACT_PROMPT, {"task": task, "strategy": strategy, "sources": payload_sources,
                                                   "available_images": image_meta})
            if isinstance(extracted.get("customer_insight"), dict):
                strategy["customer_insight"] = extracted["customer_insight"]
            if extracted.get("conflicts"):
                return _empty("blocked", "### 资料存在冲突，请人工确认\n\n" + "\n".join("- " + str(x) for x in extracted['conflicts']) + "\n\n本次没有交付营销稿。", trace,
                              checks={"publication": "资料冲突，停止生成", "conflicts": extracted["conflicts"]})
            facts, rejected = evidence_facts(extracted, sources)
            if not facts:
                return _empty("blocked", "### 事实来源校验未通过\n\n没有事实能够在本次授权知识库或华为官方商城正文中逐字定位，本次停止生成。请重试或核对资料。", trace)
            evidence_review = model.json(FACT_REVIEW_PROMPT, {"facts": facts}, max_tokens=2500)
            fact_verdicts = {x.get("id"): x for x in evidence_review.get("facts", []) if isinstance(x, dict)}
            evidence_removed = [{"id": f["id"], "reason": str(fact_verdicts.get(f["id"], {}).get("reason", "证据复核未确认该事实。"))}
                                for f in facts if fact_verdicts.get(f["id"], {}).get("verdict") != "pass"]
            facts = [f for f in facts if fact_verdicts.get(f["id"], {}).get("verdict") == "pass"]
            if not facts:
                return _empty("blocked", "### 事实证据复核未通过\n\n引文不能充分支持提取的事实，本次停止生成。", trace,
                              checks={"publication": "未交付文案", "removed_facts": evidence_removed})
            step("事实提取与引文/语义复核", 0.5, f"{len(facts)}项事实同时通过原文定位和独立证据复核。")
        if phase == "plan":
            context = {"task": task, "strategy": strategy, "facts": facts, "images": images,
                       "sources": _public_sources(sources), "extracted": {k: extracted.get(k, []) for k in ("constraints", "unknowns")},
                       "mode": mode, "mode_label": mode_label, "knowledge_mode": knowledge_mode,
                       "mall_sources": [s for s in _public_sources(sources) if s.get("origin") == "official_vmall"],
                       "rejected": rejected, "evidence_removed": evidence_removed,
                       "retrieval_warnings": sanitize_public(result.get("warnings", [])),
                       "input_key": input_key, "style_key": digest(card), "created_at": time.time(), "trace": trace}
            return {"status": "plan_ready", "plan": make_plan(context), "prepared": context,
                    "facts": sanitize_public(facts), "images": images, "strategy": sanitize_public(strategy),
                    "checks": {"data_mode_label": mode_label}, "trace": sanitize_public(trace)}
        if card:
            strategy["style_card"] = card
        if approved_plan:
            strategy["approved_plan"] = normalize_plan(approved_plan)
        compose_payload = {"task": task, "strategy": strategy, "facts": facts,
                           "style_card": card, "approved_plan": strategy.get("approved_plan"),
                           "constraints": extracted.get("constraints", []), "images": image_meta}
        draft = model.json(COMPOSE_PROMPT, compose_payload)
        # One bounded writing repair, always followed by the same independent audit.
        import re
        body_text = str(draft.get("intro", "")) + str(draft.get("cta", "")) + "".join(
            str(s.get("text", "")) for s in draft.get("sections", []) if isinstance(s, dict))
        body_chars = len(re.findall(r"[\u4e00-\u9fff]", body_text))
        max_chars = {"小红书": 650, "微信公众号": 1000, "门店朋友圈": 180, "门店海报": 120}[platform]
        min_chars = {"小红书": 350, "微信公众号": 650, "门店朋友圈": 80, "门店海报": 40}[platform]
        repair = []
        if body_chars > max_chars or (phase == "final" and prepared is not None and body_chars < min_chars):
            repair.append(f"正文当前{body_chars}个汉字，调整至{strategy['body_target']}；补足场景建议和选购取舍，不编造事实，不重复凑字。")
        if len(str(draft.get("title", ""))) > strategy["title_max"]:
            repair.append(f"标题控制在{strategy['title_max']}个字符以内。")
        if prepared is not None and platform == "微信公众号" and (not draft.get("intro") or any(not s.get("heading") for s in draft.get("sections", []) if isinstance(s, dict))):
            repair.append("公众号必须有导语，每个正文段落有论证小标题，正文与给定配图按slot穿插。")
        if prepared is not None and platform == "小红书" and not draft.get("tags"):
            repair.append("小红书补充与本次内容相关的话题标签，不在标签加入无依据产品结论。")
        if re.search(r"\b(?:usually|basically|actually|anyway|whatever)\b", body_text, re.I):
            repair.append("移除无意义的夹杂英文，改为自然简体中文。")
        gate_feedback = []
        for unit in draft_units(draft, strategy):
            if unit["id"] == "customer_insight":
                continue
            refs = set(unit.get("fact_ids", []))
            unit_facts = [fact for fact in facts if fact["id"] in refs]
            violations = text_violations(unit.get("heading", "") + " " + unit["text"], unit_facts, product)
            if violations:
                gate_feedback.append(f"{unit['id']}: " + "；".join(violations))
        if gate_feedback:
            repair.append("确定性事实门控发现以下文本与该单元引用不一致。仅修改这些单元：删除不支持表述，或补上真正支持数值与单位的fact_ids；不要复述F编号作为文案。\n" + "\n".join(gate_feedback[:8]))
        if repair:
            draft = model.json(COMPOSE_PROMPT, {**compose_payload, "previous_draft": draft,
                                               "quality_revision": repair})
        strategy["angle"] = str(draft.get("angle", strategy["pain"]))
        strategy["selected_priorities"] = [str(x) for x in draft.get("priorities", strategy['priorities'])]
        units = draft_units(draft, strategy)
        if strategy.get("customer_insight"):
            units.append({"id": "customer_insight", "text": json.dumps(strategy["customer_insight"], ensure_ascii=False), "fact_ids": []})
        step("图文编排与软文生成", 0.7, "已按人群、场景与平台生成草稿，进入独立审核。")
        audit = model.json(AUDIT_PROMPT, {"task": task, "units": units, "facts": facts,
                           "constraints": extracted.get("constraints", []), "available_images": image_meta,
                           "retrieval_mode": mode}, max_tokens=4500)
        if audit.get("conflict"):
            return _empty("blocked", "### 核验发现产品事实冲突\n\n请人工核实资料与具体款式，本次停止交付。", trace)
        reviewed = {u.get("id"): u for u in audit.get("units", []) if isinstance(u, dict)}
        allowed_ids = {f['id'] for f in facts}
        accepted, removed = [], []
        for unit in units:
            if not unit["text"].strip():
                continue
            verdict = reviewed.get(unit["id"], {})
            unit_facts = [fact for fact in facts if fact["id"] in unit.get("fact_ids", [])]
            # Insights describe user needs and explicit assumptions, not product evidence.
            # Keep the independent semantic audit for unsupported product claims, but do
            # not apply product-number/unit gates to ordinary user questions or conditions.
            issues = [] if unit["id"] == "customer_insight" else text_violations(
                unit.get("heading", "") + " " + unit["text"], unit_facts, product)
            invalid_refs = set(unit.get("fact_ids", [])) - allowed_ids
            if invalid_refs:
                issues.append("引用了未通过校验的事实编号。")
            if verdict.get("verdict") != "pass":
                issues.append(str(verdict.get("reason", "审核节点未确认该单元。")))
            if unit["id"] == "customer_insight":
                if issues:
                    strategy.pop("customer_insight", None)
                    removed.append({"id": unit["id"], "reason": "；".join(issues)})
                continue
            if issues:
                removed.append({"id": unit["id"], "reason": "；".join(issues)})
                if unit["id"] == "title":
                    accepted.append({"id": "title", "text": product + "｜" + scenario + "选购参考", "fact_ids": []})
                elif unit["id"] == "cta":
                    accepted.append({"id": "cta", "text": strategy["cta"], "fact_ids": []})
            else:
                unit["fact_ids"] = [x for x in unit.get("fact_ids", []) if x in allowed_ids]
                accepted.append(unit)
        body_units = [x for x in accepted if x['id'].startswith('section_')]
        if not body_units:
            return _empty("blocked", "### 草稿未通过发布核验\n\n正文存在无法确认的产品事实或营销表述，已拦截。请调整任务后重试。", trace,
                          strategy=strategy, facts=facts, checks={"publication": "已拦截，未发布文案", "removed_units": removed})
        image_by_id = {i['id']: i for i in images}
        selected = []
        used = set()
        for plan in draft.get("image_plan", []):
            iid = plan.get("image_id") if isinstance(plan, dict) else None
            if iid in image_by_id and iid not in used:
                item = image_by_id[iid].copy()
                # Keep the knowledge-base caption, not the model's unverified visual claims.
                item["placement"] = str(plan.get("placement", "正文配图"))[:120]
                try:
                    item["slot"] = max(0, min(len(body_units), int(plan.get("slot", len(selected)))))
                except (TypeError, ValueError):
                    item["slot"] = min(len(selected), len(body_units))
                item["caption"] = str(item.get("caption") or item.get("title", ""))
                selected.append(item)
                used.add(iid)
        for image in images:
            if len(selected) >= strategy["image_min"]:
                break
            if image["id"] not in used:
                image["slot"] = min(len(selected), len(body_units))
                image["placement"] = "主视觉" if not selected else f"第{len(selected)}个场景段落之后"
                selected.append(image)
                used.add(image['id'])
        selected = selected[:strategy['image_max']]
        warnings = list(result.get("warnings", [])) + rejected
        if len(selected) < strategy["image_min"]:
            return _empty("needs_clarification", "### 同型号配图数量不足\n\n未能完成平台要求的图文编排，请补充获授权素材或更换平台；本次不交付文案。", trace,
                          strategy=strategy, checks={"publication": "配图不足，未交付文案"})
        pending = [str(x) for x in extracted.get("unknowns", [])] + [str(x) for x in audit.get("warnings", [])]
        pending.append("当天价格、补贴、库存、赠品及具体销售SKU需另行人工确认，未写入本稿。")
        demos = [{k: u[k] for k in ("action", "speech", "observe", "fact_ids")}
                 for u in accepted if u["id"].startswith("demo_")]
        strategy["demo_steps"] = demos
        checks = {"publication": "已通过本次资料依据与内容核验；发布前请复核目标SKU和当天政策",
                  "accepted_demo_steps": len(demos),
                   "knowledge_retrieval_mode": knowledge_mode,
                   "source_origins": sorted({s.get("origin", knowledge_mode) for s in sources + selected}),
                   "official_vmall_sources": len(mall_sources),
                   "image_mode_label": "、".join(sorted({_origin_label(i.get("origin", knowledge_mode)) for i in selected})),
                  "retrieval_mode": mode, "data_mode_label": mode_label,
                  "accepted_facts": len(facts), "accepted_text_units": len(accepted), "ima_images": len(selected),
                  "removed_facts": evidence_removed,
                  "removed_units": removed, "rejected_requests": [str(x) for x in draft.get("rejected_requests", [])],
                  "pending": list(dict.fromkeys(pending)), "warnings": warnings,
                  "model": model.model, "total_seconds": round(time.perf_counter()-started, 2)}
        public = sanitize_public({"task": task, "strategy": strategy, "facts": facts,
                                  "accepted": accepted, "images": selected, "checks": checks,
                                  "sources": _public_sources(sources)})
        task, strategy, facts = public["task"], public["strategy"], public["facts"]
        accepted, selected, checks = public["accepted"], public["images"], public["checks"]
        copy = _format_copy(accepted, product, strategy)
        checks["copy_chinese_chars"] = len(re.findall(r"[\u4e00-\u9fff]", copy))
        checks["writing_repairs"] = sanitize_public(repair)
        body_copy = "".join(u["text"] for u in accepted if u["id"] in {"intro", "cta"} or u["id"].startswith("section_"))
        checks["body_chinese_chars"] = len(re.findall(r"[\u4e00-\u9fff]", body_copy))
        minimum = {"小红书": 350, "微信公众号": 650, "门店朋友圈": 80, "门店海报": 40}[platform]
        checks["length_target_met"] = minimum <= checks["body_chinese_chars"] <= max_chars
        if not checks["length_target_met"]:
            checks["warnings"].append("审核删减后正文篇幅未达平台目标；保留已核验内容，建议修改后再发布。")
        preview = build_preview(accepted, selected, task, mode_label)
        if preview.count('<img src="data:image/') < strategy["image_min"]:
            return _empty("needs_clarification", "### 配图预览校验失败\n\n图片无法完整显示，未达到平台最低图数；请补充可读取的同型号素材后重试。", trace)
        out_dir = Path(tempfile.mkdtemp(prefix="zhiheng-export-"))
        delivery = export_delivery(accepted, selected, task, mode_label, out_dir, copy)
        checks["platform_checks"] = delivery["platform_checks"]
        checks["platform_ready"] = bool(delivery["platform_checks"].get("ready"))
        if not checks["platform_ready"]:
            checks["warnings"].extend(delivery["platform_checks"].get("issues", []))
            checks["publication"] = "待修改：平台格式未全部达标；当前为待审草稿"
        report = _report(task, strategy, facts, copy, selected, checks, public["sources"])
        report += "\n\n## 平台排版与交付\n\n" + delivery["delivery_notes"]
        step("事实、图片与合规核验", 0.94, f"已审核{len(units)}个文本单元，拦截{len(removed)}项风险；核对{len(selected)}张图片。")
        md = out_dir / "知衡-图文营销方案.md"
        js = out_dir / "知衡-核验记录.json"
        md.write_text(report, encoding="utf-8")
        public_images = [{k: v for k, v in i.items() if k in ("id", "title", "caption", "placement", "slot", "source_title", "source_id", "model", "origin")} for i in selected]
        step("导出", 1.0, "已生成图文方案 Markdown 与可追溯核验 JSON。")
        checks["total_seconds"] = round(time.perf_counter()-started, 2)
        trace = sanitize_public(trace)
        artifact = {"version": VERSION, "generated_at": datetime.now(timezone.utc).isoformat(),
                    "retrieval_mode": mode, "data_mode_label": mode_label, "task": task,
                    "strategy": strategy, "facts": facts, "sources": public["sources"],
                    "copy_text": copy, "images": public_images, "checks": checks, "trace": trace}
        js.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"status": "ready", "report": report, "copy_text": copy, "strategy": strategy,
                "facts": facts, "images": selected, "checks": checks, "trace": trace,
                "export_markdown": str(md), "export_json": str(js), "preview_html": preview, **delivery}
    except FlowError as exc:
        return _empty("needs_clarification", "### 请先完成确认\n\n" + html.escape(str(exc)), trace)
    except ValueError:
        return _empty("needs_clarification", "### 风格卡或思路不完整\n\n请检查文本长度和必填字段后重新确认。", trace)
    except VmallError as exc:
        return _empty("needs_clarification", "### 华为官方商城资料需要确认\n\n" + html.escape(str(exc)) + "\n\n本次未使用模型记忆或第三方页面补写。", trace)
    except (IMAError, ModelError) as exc:
        # These client exceptions are deliberately sanitized at their boundary.
        return _empty("error", "### 本次任务未完成\n\n" + html.escape(str(exc)), trace)
    except Exception:
        # Do not surface request URLs, authorization headers, or downloaded content.
        return _empty("error", "### 本次任务未完成\n\n服务暂时异常，请稍后重试；本次未交付可发布文案。", trace)
