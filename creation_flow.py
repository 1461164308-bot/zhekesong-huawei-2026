"""Server-side approvals for brief -> style -> idea -> final copy.

Reference copy is used only by the style-card extractor, never as product evidence.
State is per Gradio session. Persisted favourites contain cards, not sample copy.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import time

from policy import PLATFORM_RULES, SCENE_RULES
from public_payload import sanitize_public

REQUEST_FIELDS = ("product", "audience", "scenario", "platform", "goal", "requirements")
PLAN_FIELDS = (("angle", "内容切入点"), ("outline", "段落大纲"),
               ("images", "配图与位置"), ("action", "行动引导"), ("boundaries", "保留条件与取舍"))


class FlowError(ValueError):
    """A display-safe missing or stale approval."""


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def request_from_values(*values) -> dict:
    return {key: str(value or "").strip() for key, value in zip(REQUEST_FIELDS, values)}


def request_key(request: dict) -> str:
    return digest({key: str(request.get(key) or "").strip() for key in REQUEST_FIELDS})


def validate_brief(request: dict) -> dict:
    request = request_from_values(*(request.get(key) for key in REQUEST_FIELDS))
    if not request["product"] or not request["audience"]:
        raise FlowError("请先填写准确产品型号和目标人群，再确认需求。")
    if request["scenario"] not in SCENE_RULES or request["platform"] not in PLATFORM_RULES:
        raise FlowError("请选择有效的使用场景和发布平台。")
    if not request["goal"]:
        raise FlowError("请选择营销目标。")
    for key, limit in (("product", 180), ("audience", 300), ("goal", 120), ("requirements", 2500)):
        if len(request[key]) > limit:
            raise FlowError(f"输入过长，请将{dict(product='型号', audience='人群', goal='目标', requirements='补充要求')[key]}精简到{limit}字以内。")
    return request


def style_source_key(description="", reference="") -> str:
    return digest([str(description or "").strip(), str(reference or "").strip()])


def confirm_brief(request: dict) -> dict:
    request = validate_brief(request)
    return {"stage": "brief_confirmed", "request_key": request_key(request),
            "request": sanitize_public(request)}


def check_brief(state: dict, request: dict):
    validate_brief(request)
    if not state or state.get("request_key") != request_key(request):
        raise FlowError("需求尚未确认，或产品、人群、平台等已修改。请先点击「确认需求」。")


def confirm_style(state: dict, request: dict, card: dict, description="", reference="", draft_source="") -> dict:
    from style_cards import normalize_style
    check_brief(state, request)
    source_key = style_source_key(description, reference)
    if (str(description or "").strip() or str(reference or "").strip()) and draft_source != source_key:
        raise FlowError("描述或参考文案已变化，请先重新提炼风格卡；也可以清空参考输入后直接编辑风格卡。")
    card = normalize_style(card)
    updated = {k: deepcopy(v) for k, v in state.items() if k in {"request_key", "request"}}
    updated.update(stage="style_confirmed", style_card=card, style_key=digest(card), style_source=source_key)
    return updated


def check_style(state: dict, request: dict, card: dict, description="", reference=""):
    from style_cards import normalize_style
    check_brief(state, request)
    if (state.get("style_key") != digest(normalize_style(card))
            or state.get("style_source") != style_source_key(description, reference)):
        raise FlowError("风格尚未确认或已修改，请先确认当前风格卡。")


def normalize_plan(plan: dict) -> dict:
    if not isinstance(plan, dict):
        raise FlowError("请先生成并编辑创作思路。")
    normalized = {}
    for key, label in PLAN_FIELDS:
        value = plan.get(key, "")
        if not isinstance(value, str) or len(value.strip()) > 2400:
            raise FlowError(f"{label}需要是2400字以内的文字。")
        normalized[key] = value.strip()
    if not all(normalized[key] for key in ("angle", "outline", "images", "action")):
        raise FlowError("请补全切入点、段落大纲、配图位置和行动引导，再确认思路。")
    return sanitize_public(normalized)


def plan_from_values(*values) -> dict:
    return normalize_plan({key: value for (key, _), value in zip(PLAN_FIELDS, values)})


def make_plan(context: dict) -> dict:
    """Build an editable idea from reviewed facts, actual images and platform rules."""
    task, strategy = context["task"], context["strategy"]
    insight = strategy.get("customer_insight") or {}
    if not isinstance(insight, dict):
        insight = {}
    facts = context["facts"][:4]
    platform = task["platform"]
    count = 1 if platform == "门店朋友圈" else min(len(facts), 3 if platform == "门店海报" else 4)
    outline = [f"开头：从{insight.get('situation') or strategy['pain']}切入。"]
    outline.extend(f"第{i}部分：[{fact['id']}] {fact['statement']}" for i, fact in enumerate(facts[:count], 1))
    outline.append("结尾：保留适用条件，请顾客带具体任务到店核对。")
    selected = context["images"][:strategy["image_min"]]
    image_lines = [f"[{image['id']}] {'封面主视觉' if i == 0 else f'第{i}部分后'}：{image.get('caption') or image.get('title', '')}"
                   for i, image in enumerate(selected)]
    conditions = list(context.get("extracted", {}).get("constraints", []))
    conditions.extend(condition for fact in facts for condition in fact.get("conditions", []))
    return normalize_plan({
        "angle": str(insight.get("empathy_anchor") or f"围绕{strategy['pain']}，帮助{task['audience']}做选择。"),
        "outline": f"{platform}｜{strategy['body_target']}｜{strategy['structure']}\n" + "\n".join(outline),
        "images": "\n".join(image_lines), "action": strategy["cta"],
        "boundaries": "\n".join(dict.fromkeys(str(x) for x in conditions))[:1800] or "核对具体销售SKU与软件适配，不写未核实价格和个人体验。",
    })


def attach_idea(state: dict, result: dict) -> dict:
    if result.get("status") != "plan_ready":
        return {k: deepcopy(v) for k, v in state.items() if k not in {"prepared", "plan_key", "final_key", "final_result"}}
    updated = deepcopy(state)
    updated.update(stage="idea_ready", prepared=result["prepared"], idea=normalize_plan(result["plan"]))
    for key in ("plan_key", "final_key", "final_result"):
        updated.pop(key, None)
    return updated


def confirm_plan(state: dict, request: dict, card: dict, plan: dict, description="", reference="") -> dict:
    check_style(state, request, card, description, reference)
    prepared = state.get("prepared") or {}
    if prepared.get("input_key") != request_key(request) or prepared.get("style_key") != state["style_key"]:
        raise FlowError("创作思路已失效，请按当前需求和风格重新生成思路。")
    if time.time() - prepared.get("created_at", 0) > 3600:
        raise FlowError("资料读取已超过一小时，请重新生成思路以核对来源。")
    updated = deepcopy(state)
    updated.update(stage="plan_confirmed", idea=normalize_plan(plan), plan_key=digest(normalize_plan(plan)))
    updated.pop("final_result", None)
    updated.pop("final_key", None)
    return updated


def generation_args(state: dict, request: dict, card: dict, plan: dict, description="", reference="") -> dict:
    checked = confirm_plan(state, request, card, plan, description, reference)
    if state.get("plan_key") != checked["plan_key"]:
        raise FlowError("思路尚未确认或已修改，请先点击「确认思路」。")
    return {"style_card": checked["style_card"], "approved_plan": checked["idea"], "prepared": checked["prepared"]}


def attach_final(state: dict, result: dict) -> dict:
    updated = deepcopy(state)
    updated.pop("final_key", None)
    if result.get("status") == "ready":
        updated.update(stage="final_review", final_result=result)
    else:
        updated.pop("final_result", None)
    return updated


def confirm_final(state: dict, request: dict, card: dict, plan: dict, description="", reference="") -> dict:
    generation_args(state, request, card, plan, description, reference)
    result = state.get("final_result") or {}
    if result.get("status") != "ready" or not result.get("copy_text"):
        raise FlowError("请先生成终稿并检查图文内容。")
    # 平台格式未达标时仍允许确认，但标记为草稿：下载的 HTML/ZIP 会写明"草稿 · 未达标"。
    draft = result.get("checks", {}).get("platform_ready") is False
    updated = deepcopy(state)
    updated.update(stage="final_confirmed", final_key=digest(result["copy_text"]),
                   final_draft=draft)
    return updated
