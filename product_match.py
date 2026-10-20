"""把用户手输的型号文本匹配到目录里的准确型号。

两种模式的产品字段都允许自由输入（`allow_custom_value=True`）。本模块只做
**匹配**，不造型号：输入会先归一化（全角/大小写/华为前缀/空格），再用型号
家族、系列、年份、系统、版本后缀逐项对齐；分数不够就返回候选让人选，绝不
自作主张把「MateBook 14」当成某一年某一版。

匹配结果三种状态：
- ``matched``：唯一命中，可以继续生成；
- ``ambiguous``：有多个候选，需要用户从候选里挑一个；
- ``unknown``：目录里没有相近型号，提示补全型号或提供官方商城商品页链接。

对外只有一个入口 :func:`resolve`，是纯函数、不访问网络，方便离线回归。
"""
from __future__ import annotations

import difflib
import re
import unicodedata

# 命中阈值：低于它不算同一个型号；领先第二名不足 MARGIN 时按歧义处理。
MATCH_SCORE = 0.92
MARGIN = 0.06
SUGGEST_SCORE = 0.42

_MODEL_FAMILY = re.compile(
    r"(matebook|matestation|mateview|matepad|watch|freebuds|freeclip|freearc|"
    r"nova|pura|mate\b|畅享|智慧屏|路由|router|手环|band|eyewear|vision)",
    re.I)
_YEAR = re.compile(r"20\d{2}")
_SERIES = re.compile(r"(?<![a-z])(x\s*pro|gt\s*\d*|d\s*\d+|matebook\s*\d+|pro\s*s|pro|fold|se|air)(?![a-z])", re.I)
_SIZE = re.compile(r"(?<!\d)(1[0-9]|2[0-9])(?!\d)")
_HARMONY = re.compile(r"鸿蒙|harmony", re.I)
_WINDOWS = re.compile(r"windows", re.I)
_ULTRA = re.compile(r"酷睿\s*ultra|ultra", re.I)
_PREFIX = re.compile(r"^(?:huawei|华为)\s*", re.I)
_NOISE = re.compile(r"[\s·\-_/\\()（）\[\]【】{}<>《》'\"“”‘’,，、:：;；]+")


def normalize(text: str) -> str:
    """NFKC + 去品牌前缀 + 去分隔符，便于比较「MateBook 14（鸿蒙版）」和「matebook14鸿蒙版」。"""
    value = unicodedata.normalize("NFKC", str(text or "")).casefold()
    value = _PREFIX.sub("", value.strip())
    return _NOISE.sub("", value)


def _features(text: str) -> dict:
    raw = unicodedata.normalize("NFKC", str(text or "")).casefold()
    norm = normalize(text)
    family = _MODEL_FAMILY.search(raw) or _MODEL_FAMILY.search(norm)
    series = _SERIES.search(raw) or _SERIES.search(norm)
    years = _YEAR.findall(raw) or _YEAR.findall(norm)
    # 屏幕尺寸只认紧跟型号关键字的数字，避免把年份 2024 里的 20/24 当成尺寸。
    size_match = re.search(r"(?:matebook\s*|d\s*|gt\s*|pro\s*)(1[0-9]|2[0-9])", raw) or \
        re.search(r"(?:matebook|d|gt|pro)(1[0-9]|2[0-9])", norm)
    size = size_match.group(1) if size_match else ""
    return {
        "family": (family.group(1).strip() if family else "").replace(" ", ""),
        "series": re.sub(r"\s+", "", series.group(1)) if series else "",
        "year": years[0] if years else "",
        "size": size or "",
        "system": "harmony" if _HARMONY.search(raw) or "鸿蒙" in norm else
                  "windows" if _WINDOWS.search(raw) else "",
        "ultra": bool(_ULTRA.search(raw)),
        "se": "se" in norm,
        "pro_s": bool(re.search(r"pros(?![a-z])", norm)),
    }


def _incompatible(left: dict, right: dict) -> bool:
    """硬性冲突：家族/年份/系统对不上时，再像也不是同一个型号。"""
    if left["family"] and right["family"] and left["family"] != right["family"]:
        return True
    if left["year"] and right["year"] and left["year"] != right["year"]:
        return True
    if left["system"] and right["system"] and left["system"] != right["system"]:
        return True
    return False


def score(query: str, candidate: str) -> float:
    """0-1 的匹配分：字面相似度打底，型号要素逐项加分。"""
    left, right = _features(query), _features(candidate)
    if _incompatible(left, right):
        return 0.0
    base = difflib.SequenceMatcher(None, normalize(query), normalize(candidate)).ratio()
    bonus = 0.0
    if left["series"] and left["series"] == right["series"]:
        bonus += 0.22
    elif left["series"] and right["series"]:
        bonus -= 0.08
    if left["size"] and left["size"] == right["size"]:
        bonus += 0.10
    if left["year"] and left["year"] == right["year"]:
        bonus += 0.06
    for key in ("se", "pro_s", "ultra"):
        if left[key] and left[key] == right[key]:
            bonus += 0.04
    if left["system"] and left["system"] == right["system"]:
        bonus += 0.03
    return min(1.0, max(0.0, base + bonus))


def candidates(products, extra=()) -> list[str]:
    """候选池：目录在前、补充来源在后，按归一化去重，保留原始写法。"""
    seen, result = set(), []
    for item in list(products or []) + list(extra or []):
        name = str(item or "").strip()
        key = normalize(name)
        if not name or not key or key in seen:
            continue
        seen.add(key)
        result.append(name)
    return result


def ranked(query: str, products, extra=(), limit: int = 5) -> list[tuple[str, float]]:
    rows = [(name, score(query, name)) for name in candidates(products, extra)]
    rows = [row for row in rows if row[1] > 0]
    rows.sort(key=lambda row: (-row[1], row[0]))
    return rows[:limit]


def _peer(query: dict, candidate: str) -> bool:
    """候选是否与查询的家族/系列/尺寸一致（用于判断「唯一对应」）。"""
    right = _features(candidate)
    if _incompatible(query, right):
        return False
    if query["family"] and right["family"] != query["family"]:
        return False
    if query["series"] and right["series"] != query["series"]:
        return False
    if query["size"] and right["size"] != query["size"]:
        return False
    return True


def _auto_match_allowed(query: str, candidate: str, pool: list[str]) -> bool:
    """简写能不能直接落地成候选型号，取决于缺的信息是否还有别的候选。

    用户写了「鸿蒙版/Windows」而候选没写系统，或候选带年份/版本而查询没写时：
    目录里只有这一个对应型号才敢自动填；有两个以上就当歧义，让用户自己挑。
    """
    left, right = _features(query), _features(candidate)
    if left["system"] and not right["system"]:
        return False
    if right["system"] and not left["system"]:
        return False
    # 年份决定资料归属，缺了就必须问，不能因为目录里只有一个就替用户认定。
    if right["year"] and not left["year"]:
        return False
    if right["series"] and right["series"] != left["series"]:
        return False
    suffix_missing = any([
        right["se"] and not left["se"],
        right["pro_s"] and not left["pro_s"],
        right["ultra"] and not left["ultra"],
    ])
    if not suffix_missing:
        return True
    peers = [name for name in pool if _peer(left, name)]
    return len(peers) == 1 and peers[0] == candidate


def resolve(query: str, products, extra=()) -> dict:
    """把自由输入解析成目录里的一个型号；拿不准就返回候选，不替用户决定。"""
    text = str(query or "").strip()
    pool = candidates(products, extra)
    if not text:
        return {"status": "unknown", "product": None, "score": 0.0, "candidates": [],
                "message": "请先填写产品型号，例如「MateBook D 14 2024」或「MateBook Pro」。"}
    norm = normalize(text)
    wanted_year = _YEAR.search(unicodedata.normalize("NFKC", text))
    if wanted_year and not any(wanted_year.group() in name for name in pool):
        return {"status": "unknown", "product": None, "score": 0.0, "candidates": [],
                "message": f"目录里没有 {wanted_year.group()} 年款的「{text}」。"
                           "请确认年份是否写错，或从目录里选择对应年份的型号。"}
    exact = [name for name in pool if normalize(name) == norm]
    if len(exact) == 1:
        return {"status": "matched", "product": exact[0], "score": 1.0,
                "candidates": [{"product": exact[0], "score": 1.0}],
                "message": f"已匹配到「{exact[0]}」。"}
    rows = ranked(text, pool)
    top = [{"product": name, "score": round(value, 3)} for name, value in rows]
    if not rows or rows[0][1] < SUGGEST_SCORE:
        hint = ""
        if rows:
            hint = "目录里最接近的是：" + "、".join(name for name, _ in rows[:3]) + "。"
        return {"status": "unknown", "product": None, "score": rows[0][1] if rows else 0.0,
                "candidates": top,
                "message": f"目录里没有「{text}」这个型号。{hint}"
                           "请补全准确型号（含年份/系统/款式），或提供华为官方商城商品页链接（https://www.vmall.com/product/数字.html）。"}
    best, second = rows[0][1], (rows[1][1] if len(rows) > 1 else 0.0)
    if best >= MATCH_SCORE and best - second >= MARGIN and _auto_match_allowed(text, rows[0][0], pool):
        return {"status": "matched", "product": rows[0][0], "score": round(best, 3),
                "candidates": top, "message": f"已匹配到「{rows[0][0]}」。"}
    names = "、".join(f"「{name}」" for name, _ in rows[:3])
    return {"status": "ambiguous", "product": None, "score": round(best, 3), "candidates": top,
            "message": f"「{text}」可能对应多个型号：{names}。请从候选里选一个准确型号，"
                       "年份、Windows/鸿蒙与款式不同，资料和参数也不同。"}
