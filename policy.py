"""Business strategy and deterministic publication gates (no API dependency)."""
from __future__ import annotations

import re
import unicodedata

PLATFORM_RULES = {
    "小红书": {"title_max": 28, "body_target": "350-650字", "sections": 4,
              "structure": "选购问题切入 → 场景清单 → 有依据的取舍 → 评论/收藏咨询", "tone": "口语、短段落、非亲测口吻",
              "image_min": 3, "image_max": 6, "cta": "说说你的课程和常用软件，带着清单到店试用后再决定。", "tags": True},
    "微信公众号": {"title_max": 45, "body_target": "650-1000字", "sections": 5,
                 "structure": "标题与导语 → 场景问题 → 分点论证 → 适用条件 → 选购建议", "tone": "信息充分、专业克制、有论证",
                 "image_min": 2, "image_max": 4, "cta": "欢迎携带常用设备与软件清单，到店验证具体版本是否适合。", "tags": False},
    "门店朋友圈": {"title_max": 30, "body_target": "80-180字", "sections": 1,
                "structure": "一句场景 → 一个核心卖点 → 到店或私信咨询", "tone": "门店服务口吻、简洁直接、不冒充用户体验",
                "image_min": 1, "image_max": 3, "cta": "私信你的使用需求，预约到店体验；具体款式和适配情况以现场确认为准。", "tags": False},
    "门店海报": {"title_max": 18, "body_target": "40-120字", "sections": 3,
               "structure": "主标题 → 副标题 → 不超过3条短卖点 → 到店引导", "tone": "短句、少信息、单一主视觉",
               "image_min": 1, "image_max": 1, "cta": "到店体验，咨询具体款式与使用条件。", "tags": False},
}

SCENE_RULES = {
    "开学季": {"pain": "课程软件是否适配、教室与宿舍间携带、学习与资料整理", "priorities": ["学习任务与软件条件", "携带和屏幕", "多设备资料流转"], "proof_task": "带课程软件清单和常用资料到店试用"},
    "职场办公": {"pain": "差旅负担、会议效率、文档与手机资料流转", "priorities": ["携带与会议", "协同的设备和版本条件", "隐私与安全"], "proof_task": "用一次真实会议/文档流转任务验证"},
    "内容创作": {"pain": "屏幕查看素材、软件插件适配与素材流转", "priorities": ["素材和屏幕", "具体软件兼容性", "工作流与接口"], "proof_task": "带常用素材、插件与外设验证工作流，不能编造软件测试成绩"},
    "家庭换新": {"pain": "家庭成员的不同任务、旧机资料迁移、操作习惯", "priorities": ["易用性", "资料迁移条件", "全家真实任务"], "proof_task": "列出全家必用软件并咨询迁移步骤"},
    "企业采购": {"pain": "批量部署、业务系统与外设兼容、管理和服务边界", "priorities": ["IT兼容验证", "配置与管理", "服务需官方确认"], "proof_task": "由IT完成小规模POC，未核实政策不承诺"},
    "门店到访": {"pain": "短时间内找到与用户需求相关的体验理由", "priorities": ["单一可体验卖点", "具体体验任务", "咨询引导"], "proof_task": "明确一个能在店内完成的演示"},
    "新品首发": {"pain": "新品适合谁、与用户任务的联系及待确认项", "priorities": ["适合人群", "已证实的新品能力", "配置选择"], "proof_task": "核对具体SKU；不编造首发价格/权益"},
    "节日营销": {"pain": "送礼对象和实际使用习惯匹配", "priorities": ["使用对象与任务", "选择建议", "到店确认"], "proof_task": "核对收礼者必用软件；不编造优惠、库存"},
}

BANNED = [
    r"全网最(?:低|好|强)", r"全国最低", r"全球(?:第一|领先|最好)", r"行业第一", r"销量第一",
    r"绝对(?:领先|安全|流畅|护眼)", r"永不(?:卡顿|故障|掉线)", r"百分之百", r"100\s*%",
    r"零风险", r"终身免费", r"最(?:佳|好|强|低价|顶级)", r"唯一选择", r"闭眼入",
    r"我(?:已经)?(?:用了|使用了|实测|亲测)", r"亲测", r"用了[一二三四五六七八九十\d]+(?:天|周|个月)",
    r"保证.{0,6}(?:兼容|不卡|续航|流畅)", r"吊打", r"碾压", r"完胜",
]
DYNAMIC = re.compile(r"(?:[\d零〇一二两三四五六七八九十百千万]+(?:[\.点][\d零一二三四五六七八九]+)?\s*(?:元|块|折)|[¥￥]\s*\d|国补|补贴|赠品|限时优惠|库存仅剩|包邮|到手价|低至)")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text)).casefold()
    return re.sub(r"[\s\-_（）()·]", "", text)


def normalized_quote(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(text)))


def exact_product(value: str, products: list[str]) -> str | None:
    norm = normalize(value)
    for product in products:
        if norm == normalize(product) or norm == normalize(product.replace("HUAWEI ", "").replace("华为 ", "")):
            return product
    return None


def resolve_product(value: str, products: list[str]) -> dict:
    """把手输型号解析成目录里的准确型号：先精确，再模糊；拿不准就返回候选。

    只在目录内匹配，不会凭「轻薄本」这类泛称造型号；返回结构和
    ``product_match.resolve`` 一致（``matched`` / ``ambiguous`` / ``unknown``）。

    事实卡里的机型名（如「HUAWEI MateBook D 14 2024」）和知识库目录里的
    文件夹写法（如「MateBook D 14」）可能不同：先用事实卡名做别名参与匹配，
    再把命中的别名折算回目录里的原始写法，保证后续检索用的一定是目录标题。
    """
    from product_match import normalize as match_normalize
    from product_match import resolve

    exact = exact_product(value, products)
    if exact:
        return {"status": "matched", "product": exact, "score": 1.0,
                "candidates": [{"product": exact, "score": 1.0}],
                "message": f"已匹配到「{exact}」。"}

    aliases = _fact_aliases()
    result = resolve(value, products, extra=aliases)

    def canonical(name: str) -> str | None:
        norm = match_normalize(name)
        for product in products:
            if match_normalize(product) == norm:
                return product
        folder = aliases.get(name) or ""
        if folder:
            folder_norm = match_normalize(folder)
            for product in products:
                if match_normalize(product) == folder_norm:
                    return product
        return None

    if result["status"] == "matched":
        target = canonical(result["product"])
        if target:
            return {**result, "product": target,
                    "message": f"已匹配到「{target}」。"}
        return {"status": "ambiguous", "product": None, "score": result["score"],
                "candidates": result.get("candidates", []),
                "message": f"「{value}」对应的事实卡存在，但当前知识库目录里没有这个型号的资料。"}

    rows, seen = [], set()
    for item in result.get("candidates", []):
        target = canonical(item["product"]) or item["product"]
        if target in seen:
            continue
        seen.add(target)
        rows.append({"product": target, "score": item["score"]})
    if len(rows) == 1:
        return {"status": "matched", "product": rows[0]["product"], "score": rows[0]["score"],
                "candidates": rows, "message": f"已匹配到「{rows[0]['product']}」。"}
    return {**result, "candidates": rows}


def _fact_aliases() -> dict[str, str]:
    """事实卡机型名 → 知识库目录名；读不到事实卡时返回空表，不影响匹配。"""
    try:
        import facts
    except Exception:
        return {}
    aliases: dict[str, str] = {}
    for model in facts.catalogue():
        card = facts.load_card(model) or {}
        folder = str(card.get("folder") or "").strip()
        if folder:
            aliases[str(model)] = folder
    return aliases


def validate_inputs(product: str, audience: str, scenario: str, platform: str, products: list[str]) -> tuple[str | None, list[str]]:
    questions = []
    match = resolve_product(product, products)
    canonical = match["product"] if match["status"] == "matched" else None
    if not canonical:
        questions.append(match["message"])
    if not audience or len(audience.strip()) < 2:
        questions.append("这篇内容面向谁？例如大学新生、经常出差的职场用户或采购负责人。")
    if scenario not in SCENE_RULES:
        questions.append("请选择业务场景，或补充具体使用任务。")
    if platform not in PLATFORM_RULES:
        questions.append("请选择发布平台：小红书、微信公众号、门店朋友圈或门店海报。")
    return canonical, questions


def strategy_for(audience: str, scenario: str, platform: str, goal: str) -> dict:
    scene = SCENE_RULES[scenario]
    return {"audience": audience, "scenario": scenario, "goal": goal,
            "platform": platform, "pain": scene["pain"], "priorities": scene["priorities"],
            "proof_task": scene["proof_task"], **PLATFORM_RULES[platform]}


def evidence_facts(extracted: dict, sources: list[dict]) -> tuple[list[dict], list[str]]:
    """Accept a fact only when its quoted evidence is in the returned ima source."""
    by_id = {s["id"]: s for s in sources}
    facts, rejected = [], []
    for item in extracted.get("facts", [])[:16]:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("source_id", ""))
        quote = str(item.get("quote", "")).strip()
        statement = str(item.get("statement", "")).strip()
        source = by_id.get(sid)
        if not source or len(quote) < 8 or not statement:
            rejected.append("移除无有效来源或引文不足的事实候选。")
            continue
        if source.get("kind", "facts") != "facts":
            rejected.append("营销案例或价格快照不作为产品事实依据。")
            continue
        if DYNAMIC.search(statement):
            rejected.append("动态价格/权益未经当天核实，未作为营销事实。")
            continue
        if normalized_quote(quote) not in normalized_quote(source.get("text", "")):
            rejected.append("移除无法在来源原文逐字定位的事实候选。")
            continue
        numbers = set(re.findall(r"\d+(?:\.\d+)?", unicodedata.normalize("NFKC", statement)))
        evidence_numbers = set(re.findall(r"\d+(?:\.\d+)?", unicodedata.normalize("NFKC", quote)))
        if numbers - evidence_numbers:
            rejected.append("移除引文未支持数值的事实候选。")
            continue
        facts.append({"id": f"F{len(facts)+1}", "statement": statement, "quote": quote,
                      "source_id": sid, "source_title": source.get("title", ""),
                      "conditions": [str(x) for x in item.get("conditions", [])],
                      "category": item.get("category", "feature")})
        if len(facts) >= 12:
            break
    return facts, list(dict.fromkeys(rejected))


# Deliberately bounded to explicit measurements; unit conversion and prose-level
# entailment remain the independent audit's job. Aliases share a unit, not a scale.
_UNIT_ALIASES = {
    "kg": "kg", "千克": "kg", "公斤": "kg", "g": "g", "克": "g",
    "mm": "mm", "毫米": "mm", "cm": "cm", "厘米": "cm",
    "英寸": "inch", "吋": "inch", "inch": "inch", "inches": "inch",
    "小时": "hour", "h": "hour", "分钟": "minute", "min": "minute", "秒": "second", "s": "second",
    "hz": "hz", "赫兹": "hz", "khz": "khz", "mhz": "mhz", "ghz": "ghz",
    "gb": "gb", "tb": "tb", "mb": "mb", "wh": "wh", "mah": "mah", "w": "w", "瓦": "w",
    "nit": "nit", "nits": "nit", "尼特": "nit", "%": "%", "k": "k", "像素": "px", "px": "px",
}
_UNIT_PATTERN = "(?:" + "|".join(re.escape(x) for x in sorted(_UNIT_ALIASES, key=len, reverse=True)) + r")(?![a-zA-Z])"
_NUMBER_PATTERN = r"(?<![\d.])\d+(?:\.\d+)?"
_MEASURE = re.compile(r"(?P<value>" + _NUMBER_PATTERN + r")\s*(?P<unit>" + _UNIT_PATTERN + r")", re.I)
_MEASURE_RANGE = re.compile(
    r"(?P<first>" + _NUMBER_PATTERN + r")\s*(?:(?P<first_unit>" + _UNIT_PATTERN + r")\s*)?"
    r"(?:到|至|[-~～—–])\s*(?P<last>\d+(?:\.\d+)?)\s*(?P<unit>" + _UNIT_PATTERN + r")", re.I)


def _measurements(text: str) -> list[dict]:
    text = unicodedata.normalize("NFKC", str(text))
    ranges = list(_MEASURE_RANGE.finditer(text))
    matches = [(m, True) for m in ranges]
    matches += [(m, False) for m in _MEASURE.finditer(text)
                if not any(r.start() <= m.start() < r.end() for r in ranges)]
    result, previous_end = [], 0
    for match, is_range in sorted(matches, key=lambda pair: pair[0].start()):
        # A qualifier belongs to this measurement, not an earlier clause/number.
        prefix = re.split(r"[。！？!?；;，,\n]", text[max(previous_end, match.start()-32):match.start()])[-1]
        suffix = text[match.end():match.end()+8]
        unit = _UNIT_ALIASES[match["unit"].casefold()]
        first_unit = match["first_unit"] if is_range else None
        result.append({"values": (match["first"], match["last"]) if is_range else (match["value"],),
                       "unit": unit, "mixed_units": bool(first_unit and _UNIT_ALIASES[first_unit.casefold()] != unit),
                       "approx": bool(re.search(r"约|大概|大致|接近|近", prefix) or re.match(r"\s*(?:左右|上下)", suffix)),
                       "upper": bool(re.search(r"最高|至多|最多|不超过|不高于|上限|最大|高达|可达|≤|<=", prefix)
                                     or re.match(r"\s*(?:以内|以下|为上限)", suffix)),
                       "label": match.group(0)})
        previous_end = match.end()
    return result


def _measurement_violations(text: str, quotes: list[str]) -> list[str]:
    evidence = [measurement for quote in quotes for measurement in _measurements(quote)]
    issues = []
    for claim in _measurements(text):
        if len(claim["values"]) == 2:
            supports = [m for m in evidence if m["unit"] == claim["unit"] and m["values"] == claim["values"] and not m["mixed_units"]]
        else:
            supports = [m for m in evidence if m["unit"] == claim["unit"] and claim["values"][0] in m["values"] and not m["mixed_units"]]
        if not supports or claim["mixed_units"]:
            kind = "数值范围及方向" if len(claim["values"]) == 2 else "数值与单位组合"
            issues.append(f"来源未支持{kind}：{claim['label']}。")
        elif not any((not m["approx"] or claim["approx"]) and (not m["upper"] or claim["upper"]) for m in supports):
            if not claim["approx"] and all(m["approx"] for m in supports):
                issues.append(f"测量值{claim['label']}须保留来源中的约数限定。")
            else:
                issues.append(f"测量值{claim['label']}须保留来源中的最高/至多等上限限定及约数条件。")
    return issues


def text_violations(text: str, facts: list[dict], product: str) -> list[str]:
    text = unicodedata.normalize("NFKC", str(text))
    violations = []
    for pattern in BANNED:
        hit = re.search(pattern, text, re.I)
        if hit:
            violations.append("营销表述需删除：" + hit.group(0))
    if DYNAMIC.search(text):
        violations.append("包含未经当天核实的价格、补贴或促销权益。")
    numbers = set(re.findall(r"\d+(?:\.\d+)?", text))
    evidence = unicodedata.normalize("NFKC", product + " ".join(f["quote"] for f in facts))
    supported = set(re.findall(r"\d+(?:\.\d+)?", evidence))
    if numbers - supported:
        violations.append("出现来源未支持的数值：" + "、".join(sorted(numbers-supported)))
    violations.extend(_measurement_violations(text, [f["quote"] for f in facts]))
    return list(dict.fromkeys(violations))


def draft_units(draft: dict, strategy: dict) -> list[dict]:
    units = [{"id": "title", "text": str(draft.get("title", "")), "fact_ids": draft.get("title_fact_ids", []) or []},
             {"id": "intro", "text": str(draft.get("intro", "")), "fact_ids": draft.get("intro_fact_ids", []) or []}]
    for i, sec in enumerate(draft.get("sections", [])[:strategy["sections"]], 1):
        if isinstance(sec, dict):
            units.append({"id": f"section_{i}", "text": str(sec.get("text", "")),
                          "heading": str(sec.get("heading", "")), "fact_ids": sec.get("fact_ids", [])})
    for i, demo in enumerate(draft.get("demo_steps", [])[:3], 1):
        if not isinstance(demo, dict):
            continue
        action, speech, observe = (str(demo.get(k, "")) for k in ("action", "speech", "observe"))
        if action and speech:
            units.append({"id": f"demo_{i}", "text": f"操作：{action}\n话术：{speech}\n验收：{observe}",
                          "action": action, "speech": speech, "observe": observe,
                          "fact_ids": demo.get("fact_ids", [])})
    units.append({"id": "cta", "text": str(draft.get("cta", "")), "fact_ids": draft.get("cta_fact_ids", []) or []})
    if strategy["tags"]:
        tags = draft.get("tags", [])
        units.append({"id": "tags", "text": " ".join(str(t) for t in tags[:6]), "fact_ids": []})
    return units
