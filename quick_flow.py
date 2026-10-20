"""快发模式：不调用模型，用已核验事实卡和句库组合三平台成稿。

一次生成只做三件事：按人群与平台挑句库片段、用事实卡核验过的值填槽位、
把结果交给 ``policy`` 的安全闸。任何需要事实而卡片里没有的句子整句不用，
所以成稿不会出现知识库里没有的数字。同一门店近几次用过的片段会被降权，
并和近期稿件比相似度，超过阈值就换片段重组。
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import time
from pathlib import Path

import facts as fact_cards
import sentence_library as library
from policy import BANNED, DYNAMIC, PLATFORM_RULES, text_violations

PLATFORMS = ("小红书", "门店朋友圈", "微信公众号")
# 没灵感时的预选卡：一句真实门店场景 + 它最常对应的人群，点一下就填进输入框。
# 文案里不出现价格、优惠和绝对化说法，也不会冒充顾客亲测，安全闸能直接放行。
VISIT_PRESETS: tuple[dict, ...] = (
    {"label": "老师问投屏", "audience": "教师",
     "visit": "上午有位老师来问，上网课能不能一边记笔记一边投到教室大屏。"},
    {"label": "学生问宿舍", "audience": "学生",
     "visit": "下午来了个新生，说宿舍桌子小，问这台能不能塞进包带去图书馆。"},
    {"label": "家长问网课", "audience": "学生",
     "visit": "有位家长带孩子来看，主要怕上网课看久了眼睛累，先问屏幕怎么样。"},
    {"label": "出差问续航", "audience": "商务差旅",
     "visit": "刚有位常出差的顾客，说飞机上要处理一份很长的表格，问能不能撑一路。"},
    {"label": "开会要轻", "audience": "商务差旅",
     "visit": "有位顾客每周跑客户，说最怕背着电脑挤地铁，先问拎着累不累。"},
    {"label": "剪视频问颜色", "audience": "内容创作",
     "visit": "刚给一位做短视频的顾客演示完，他最在意剪素材时屏幕颜色准不准。"},
    {"label": "接口接投影", "audience": "商务差旅",
     "visit": "有位顾客拿着旧转接头来问，能不能直接连会议室的投影和 U 盘。"},
    {"label": "旧机换新", "audience": "旧机换新",
     "visit": "下午有位顾客抱着用了几年的旧机器来问，资料怎么搬过去最省事。"},
    {"label": "老人怕不会用", "audience": "旧机换新",
     "visit": "有位阿姨来帮孩子看电脑，反复问买回去不会用的话怎么办。"},
    {"label": "采购问批量", "audience": "企业采购",
     "visit": "上午来了位公司行政，问十几台一起买能不能统一装好常用软件。"},
    {"label": "负责人问资料", "audience": "管理者",
     "visit": "有位部门负责人来问，会议纪要和客户资料放在机器上安不安全。"},
)
HISTORY_DIR = Path(__file__).resolve().parent / ".local" / "quick-history"
RECENT_FRAGMENTS = 12
RECENT_DRAFTS = 4
REPEAT_PENALTY = 0.2
SIMILARITY_LIMIT = 0.62
MAX_ATTEMPTS = 5
# 每种平台先用一套片段配额，再按字数上下限微调。
PLANS: dict[str, dict[str, int]] = {
    "门店朋友圈": {"scene": 1, "benefit": 2, "store": 1},
    "小红书": {"hook": 1, "scene": 1, "benefit": 3, "evidence": 1, "store": 1, "ending": 1, "tag": 1},
    "微信公众号": {"hook": 1, "scene": 3, "benefit": 5, "evidence": 2, "store": 1, "ending": 1, "tag": 1},
}
_EXTRA_CHOICES = ("benefit", "evidence", "scene", "ending")
_MODEL_NOISE = re.compile(r"^HUAWEI\s+", re.I)
# 句库是照笔记本角色写的（便携、通勤、课件、会议），手机/手表套进去会出硬伤，
# 所以快发模式先只放笔记本类目，其他品类走极简或专业模式。
LAPTOP_CATEGORIES = ("鸿蒙电脑", "笔记本", "MateBook")
# 各平台配图数量直接读 policy 的 image_min / image_max；用途关键词决定先挑哪几张。
PLATFORM_IMAGE_HINTS: dict[str, tuple[str, ...]] = {
    "小红书": ("配色", "外观", "场景", "设计"),
    "门店朋友圈": ("外观", "配色", "产品", "场景"),
    "微信公众号": ("产品", "细节", "屏幕", "接口", "配色"),
}


def image_limits(platform: str) -> tuple[int, int]:
    rules = PLATFORM_RULES.get(platform, {})
    return int(rules.get("image_min", 0) or 0), int(rules.get("image_max", 0) or 0)


def choose_images(card: dict, platform: str, rng: random.Random, taken: set[str] | None = None) -> list[dict]:
    """同型号官方配图，按平台数量与用途挑；图不够就少给，不重复凑数。"""
    available = fact_cards.images(card)
    if not available:
        return []
    low, high = image_limits(platform)
    hints = PLATFORM_IMAGE_HINTS.get(platform, ())
    taken = taken or set()
    scored = []
    for index, item in enumerate(available):
        text = f"{item.get('title', '')} {item.get('placement', '')}"
        score = sum(1 for hint in hints if hint in text)
        # 同一次生成里别的平台已经用过的图降权，三个平台不要端着同一组图。
        score -= 2 if item["path"] in taken else 0
        scored.append((score, rng.random(), index, item))
    scored.sort(key=lambda row: (-row[0], row[1]))
    count = min(len(scored), high or len(scored))
    if count < low and len(scored) >= low:
        count = low
    return [item for _, _, _, item in scored[:count]]


def is_supported(card: dict) -> bool:
    category = str((card or {}).get("category", ""))
    return any(token in category for token in LAPTOP_CATEGORIES)


def limits(platform: str) -> tuple[int, int]:
    """Read the target length of one platform out of ``policy``, in characters."""
    target = str(PLATFORM_RULES.get(platform, {}).get("body_target", ""))
    found = re.findall(r"\d+", target)
    return (int(found[0]), int(found[1])) if len(found) >= 2 else (0, 0)


def short_model(model: str) -> str:
    return _MODEL_NOISE.sub("", str(model or "")).strip() or str(model or "")


def _char_length(text: str) -> int:
    return len(re.sub(r"\s", "", text or ""))


def similarity(left: str, right: str) -> float:
    """Character trigram Jaccard; cheap and language-agnostic enough here."""
    def grams(text: str) -> set[str]:
        value = re.sub(r"[\s#，。！？、；：,.!?;:（）()「」]" , "", text or "")
        return {value[i:i + 3] for i in range(max(0, len(value) - 2))}
    first, second = grams(left), grams(right)
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def _render(fragment: dict, card: dict) -> tuple[str, list[dict]] | None:
    """Fill a fragment's slots; ``None`` means the card cannot support the whole sentence."""
    used: list[dict] = []
    text = str(fragment.get("text", ""))
    for slot in fragment.get("slots", ()):
        found = fact_cards.resolve(card, slot)
        if not found:
            return None
        used.append(found)
        text = text.replace("{" + slot + "}", found["text"])
    if "{" in text or "}" in text:  # 未声明的槽位，整句不用
        return None
    return _spacing(text), used


def _pool(kind: str, audience: str, platform: str, rng: random.Random, recent: set[str]) -> list[dict]:
    items = []
    for fragment in library.fragments(kind, audience, platform):
        weight = max(1, int(fragment.get("weight", 1)))
        penalty = REPEAT_PENALTY if fragment["id"] in recent else 1.0
        items.append((fragment, weight * penalty * rng.random() + penalty * 0.05))
    items.sort(key=lambda pair: pair[1], reverse=True)
    return [fragment for fragment, _ in items]


def _take(kind: str, count: int, *, card, audience, platform, rng, recent, chosen: list[dict]) -> None:
    """Append up to ``count`` usable fragments of one kind, never repeating an id.

    A slot already used by the draft is skipped so two sentences never claim the
    same weight twice: repetition is the fastest way to read like a template.
    """
    if count <= 0:
        return
    taken = {fragment["id"] for fragment in chosen}
    used = {fact["slot"] for item in chosen for fact in item["facts"]}
    added = 0
    for fragment in _pool(kind, audience, platform, rng, recent):
        if added >= count:
            break
        if fragment["id"] in taken or set(fragment.get("slots", ())) & used:
            continue
        rendered = _render(fragment, card)
        if not rendered:
            continue
        text, rendered_facts = rendered
        chosen.append({"id": fragment["id"], "kind": kind, "text": text, "facts": rendered_facts})
        taken.add(fragment["id"])
        used.update(fact["slot"] for fact in rendered_facts)
        added += 1


_KIND_ORDER = {"hook": 0, "scene": 1, "benefit": 2, "evidence": 3, "store": 8, "ending": 9, "tag": 10}
_CJK = "\u4e00-\u9fff"
_SPACE_BEFORE_LATIN = re.compile(rf"(?<=[{_CJK}])(?=[0-9A-Za-z])")
_SPACE_BEFORE_CJK = re.compile(rf"(?<=[0-9A-Za-z%])(?=[{_CJK}])")


def _spacing(text: str) -> str:
    """中文和数字/字母贴在一起会显脏，排一下版（模板自己带空格的不会重复）。"""
    return _SPACE_BEFORE_CJK.sub(" ", _SPACE_BEFORE_LATIN.sub(" ", text))


def _paragraphs(chosen: list[dict], platform: str) -> list[str]:
    """Body paragraphs in reading order;话题标签 has its own place at the end.

    Fragments added later to reach the length target must not land after the
    call-to-action, so the order follows the kind, not the selection order.
    """
    ordered = sorted((item for item in chosen if item["kind"] != "tag" and item["text"].strip()),
                     key=lambda item: _KIND_ORDER.get(item["kind"], 5))
    return [item["text"].strip() for item in ordered]


def _title(chosen: list[dict], card: dict, audience: str, platform: str) -> str:
    model = short_model(card.get("model", ""))
    if platform == "门店朋友圈":
        return ""
    if platform == "微信公众号":
        return f"{model}适合谁：{audience}关注的几件事"
    base = f"{model}｜{audience}"
    hook = next((item["text"] for item in chosen if item["kind"] == "hook"), "")
    limit = int(PLATFORM_RULES["小红书"]["title_max"])
    candidate = f"{base}：{hook}"
    return candidate if hook and len(candidate) <= limit else base


def _fact_list(chosen: list[dict]) -> list[dict]:
    seen, result = set(), []
    for item in chosen:
        for fact in item["facts"]:
            key = (fact["section"], fact["name"])
            if key in seen:
                continue
            seen.add(key)
            result.append(fact)
    return result


def _gate(text: str, card: dict, extra: list[str]) -> list[str]:
    """Run the publication gate; only numbers the card (or user input) supports pass."""
    facts = [{"quote": fact["source"]} for fact in _fact_list_from_card(card)]
    facts += [{"quote": str(value)} for value in extra if value]
    return text_violations(text, facts, str(card.get("model", "")))


def _fact_list_from_card(card: dict) -> list[dict]:
    return [{"source": field.get("quote", "")} for field in card.get("fields", [])]


def check_visit(visit: str) -> list[str]:
    """店员输入的见闻先过一遍闸：拦价格、补贴、绝对化用语和虚构亲测。"""
    text = str(visit or "").strip()
    if not text:
        return []
    issues = []
    for pattern in BANNED:
        hit = re.search(pattern, text, re.I)
        if hit:
            issues.append("门店见闻里的营销表述需要改：" + hit.group(0))
    if DYNAMIC.search(text):
        issues.append("门店见闻里不要写价格、补贴或促销权益。")
    return list(dict.fromkeys(issues))


def _store_line(store: dict | None) -> str:
    if not store:
        return ""
    name = str(store.get("name", "")).strip()
    city = str(store.get("city", "")).strip()
    if name and city:
        return f"{name}（{city}）"
    return name or city


def _store_id(store: dict | None) -> str:
    raw = json.dumps(store or {}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def load_history(store: dict | None, root: Path = HISTORY_DIR) -> dict:
    path = Path(root) / f"{_store_id(store)}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def remember(store: dict | None, fragments: list[str], draft: str, root: Path = HISTORY_DIR) -> None:
    """Remember what this store just published so the next draft differs."""
    data = load_history(store, root)
    used = list(dict.fromkeys([*data.get("fragments", []), *fragments]))[-RECENT_FRAGMENTS * 3:]
    drafts = [*data.get("drafts", []), {"text": draft, "time": int(time.time())}][-RECENT_DRAFTS:]
    path = Path(root) / f"{_store_id(store)}.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"fragments": used, "drafts": drafts}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _compose(card: dict, opportunity: dict) -> dict:
    plan = dict(PLANS[opportunity["platform"]])
    rng = opportunity["rng"]
    recent = opportunity["recent"]
    visit = opportunity["visit"]
    audience = opportunity["audience"]
    platform = opportunity["platform"]
    chosen: list[dict] = []
    for kind, count in plan.items():
        _take(kind, count, card=card, audience=audience, platform=platform, rng=rng,
              recent=recent, chosen=chosen)
    # The real shop moment goes first; the hook stays as the second paragraph.
    paragraphs = _paragraphs(chosen, platform)
    if visit:
        paragraphs.insert(0, visit)
    body = _join(paragraphs, platform)
    minimum, maximum = limits(platform)
    rounds = 0
    while _char_length(body) < minimum and rounds < 10:
        rounds += 1
        before = len(chosen)
        for kind in _EXTRA_CHOICES:
            _take(kind, 1, card=card, audience=audience, platform=platform, rng=rng,
                  recent=recent, chosen=chosen)
            if len(chosen) > before:
                break
        if len(chosen) == before:
            break
        paragraphs = _paragraphs(chosen, platform)
        if visit:
            paragraphs.insert(0, visit)
        body = _join(paragraphs, platform)
    while maximum and _char_length(body) > maximum and len(chosen) > 2:
        drop = next((index for index in range(len(chosen) - 1, -1, -1)
                     if chosen[index]["kind"] in {"ending", "evidence", "scene", "benefit"}), None)
        if drop is None:
            break
        chosen.pop(drop)
        paragraphs = _paragraphs(chosen, platform)
        if visit:
            paragraphs.insert(0, visit)
        body = _join(paragraphs, platform)
    return {"chosen": chosen, "paragraphs": paragraphs, "body": body, "title": _title(chosen, card, audience, platform)}


def _join(paragraphs: list[str], platform: str) -> str:
    if platform == "门店朋友圈":
        return "\n".join(paragraphs)
    return "\n\n".join(paragraphs)


def _tags(chosen: list[dict], card: dict, audience: str, platform: str) -> list[str]:
    if platform == "门店朋友圈":
        return []
    tags = [item["text"].strip() for item in chosen if item["kind"] == "tag" and item["text"].strip()]
    model_tag = re.sub(r"[（）()\s]", "", short_model(card.get("model", "")))
    base = ["#" + model_tag, "#" + audience + "选购"]
    return list(dict.fromkeys([tag if tag.startswith("#") else "#" + tag for tag in tags + base]))[:6]


def generate(card: dict, *, audience: str, platform: str, visit: str = "", store: dict | None = None,
             seed: int | None = None, history: dict | None = None,
             taken_images: set[str] | None = None) -> dict:
    """Compose one platform draft from verified facts; never calls a model."""
    if platform not in PLATFORMS:
        return _blocked(platform, "暂不支持这个平台，请选择小红书、门店朋友圈或微信公众号。")
    if not audience:
        return _blocked(platform, "请先选择这篇内容面向哪类顾客。")
    if not is_supported(card):
        return _blocked(platform, "快发模式目前只覆盖笔记本类目；其他品类请用极简模式或专业模式。")
    visit = str(visit or "").strip()
    visit_issues = check_visit(visit)
    if visit_issues:
        return _blocked(platform, "门店见闻需要先改一下：" + " ".join(visit_issues))
    record = history if history is not None else load_history(store)
    recent = set(record.get("fragments", [])[-RECENT_FRAGMENTS:])
    drafts = [item.get("text", "") for item in record.get("drafts", []) if isinstance(item, dict)]
    # 配图独立取样：同一张卡三个平台拿到的图组不完全相同，但都来自同型号官方图。
    image_rng = random.Random((seed or 0) * 31 + PLATFORMS.index(platform) * 977 + 17)
    gallery = choose_images(card, platform, image_rng, taken_images)
    store_line = _store_line(store)
    extra_sources = [visit, store_line]
    best: dict | None = None
    for attempt in range(MAX_ATTEMPTS):
        rng = random.Random(seed if seed is None else seed + attempt)
        composed = _compose(card, {"rng": rng, "recent": recent, "visit": visit,
                                   "audience": audience, "platform": platform})
        body = composed["body"]
        if store_line:
            body = f"{body}\n\n到店：{store_line}"
        tags = _tags(composed["chosen"], card, audience, platform)
        text = "\n".join([composed["title"], body, " ".join(tags)]).strip() if composed["title"] else "\n".join([body, " ".join(tags)]).strip()
        score = max((similarity(text, draft) for draft in drafts), default=0.0)
        candidate = {"composed": composed, "body": body, "tags": tags, "text": text, "score": score}
        if best is None or candidate["score"] < best["score"]:
            best = candidate
        if score <= SIMILARITY_LIMIT:
            break
    assert best is not None
    used_facts = _fact_list(best["composed"]["chosen"])
    violations = _gate(best["text"], card, extra_sources)
    minimum, maximum = limits(platform)
    length = _char_length(best["body"])
    image_low, image_high = image_limits(platform)
    return {
        "status": "ready" if not violations else "needs_revision",
        "platform": platform,
        "title": best["composed"]["title"],
        "body": best["body"],
        "tags": best["tags"],
        "text": best["text"],
        "facts": used_facts,
        "images": gallery,
        "fragments": [item["id"] for item in best["composed"]["chosen"]],
        "checks": {
            "length": length,
            "target": (minimum, maximum),
            "within_target": (not minimum or length >= minimum) and (not maximum or length <= maximum),
            "violations": violations,
            "similarity": round(best["score"], 3),
            "attempts": attempt + 1,
            "image_count": len(gallery),
            "image_target": (image_low, image_high),
            "image_short": bool(gallery) and len(gallery) < image_low,
            "images_missing": not gallery,
            "store": _store_id(store),
        },
    }


def _blocked(platform: str, message: str) -> dict:
    return {"status": "blocked", "platform": platform, "title": "", "body": "", "tags": [], "text": "",
            "facts": [], "images": [], "fragments": [],
            "checks": {"violations": [message], "length": 0, "target": limits(platform),
                       "image_count": 0, "image_target": image_limits(platform)}}


def generate_all(card: dict, *, audience: str, visit: str = "", store: dict | None = None,
                 seed: int | None = None) -> dict[str, dict]:
    """One click, three platforms; each platform is remembered for next time."""
    record = load_history(store)
    results = {}
    used_images: set[str] = set()
    for platform in PLATFORMS:
        result = generate(card, audience=audience, platform=platform, visit=visit, store=store,
                          seed=seed, history=record, taken_images=used_images)
        results[platform] = result
        used_images.update(item["path"] for item in result.get("images", []))
        if result["status"] == "ready":
            remember(store, result["fragments"], result["text"])
            # Later platforms in this same click must also differ from what we just wrote.
            record = {"fragments": list(dict.fromkeys([*record.get("fragments", []), *result["fragments"]]))[-RECENT_FRAGMENTS * 3:],
                      "drafts": [*record.get("drafts", []), {"text": result["text"], "time": int(time.time())}][-RECENT_DRAFTS:]}
    return results


def models() -> list[str]:
    """Models with a fact card in a category the sentence library covers."""
    index = fact_cards.load_index().get("cards", {})
    return sorted(name for name, entry in index.items()
                  if any(token in str(entry.get("category", "")) for token in LAPTOP_CATEGORIES))
