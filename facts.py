"""Verified product fact cards: the only factual source of quick publishing.

Each ``P1-产品参数库/<分类>/<型号>/产品事实.md`` file is parsed into a card that
keeps the official wording, the condition that qualifies every value (销售版本、
典型值、限定说明) and the quote the value came from. Templates and models may
only fill slots that already exist here, so a published number is always one the
official page supports. Importing this module touches no network and writes no
files; :func:`main` in ``tools/build_facts.py`` writes the cards.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import tempfile
import unicodedata
import zipfile
from pathlib import Path

FACTS_DIR = Path(__file__).resolve().parent / "facts"
INDEX_FILE = "index.json"
CARD_VERSION = 1
FACT_FILE = "产品事实.md"
# 配图直接从 P1 目录读，不写进事实卡：体积大、有版权，仓库里也不提交源图。
WORKSPACE_ROOT = Path(__file__).resolve().parent
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif")
MAX_IMAGE_BYTES = 8 * 1024 * 1024
_IMAGE_CACHE: dict[str, list[dict]] = {}

_DOC_SECTIONS = frozenset({"来源", "官方规格摘录"})
_COPY_SECTIONS = frozenset({"官网定位", "官方页面卖点标题"})
_HEADING = re.compile(r"^(?P<level>#{1,3})\s+(?P<title>.+?)\s*$")
_CAVEAT = re.compile(r"^\*+\s*(?P<text>.+?)\s*$")
_BULLET = re.compile(r"^[-*•·]\s+(?P<text>.+?)\s*$")
_CAPTURED = re.compile(r"抓取日期[：:]\s*(?P<date>\d{4}-\d{2}-\d{2})")
_URL = re.compile(r"https?://[^\s)）]+")
_PAREN = re.compile(r"[（(](?P<inner>[^（）()]{1,60})[）)]\s*$")
_VARIANT = re.compile(r"^(?P<name>[^：:]{2,32})[：:]$")
_SUBLABEL = re.compile(r"^(?P<name>[^：:]{2,32})[：:]\s*(?P<value>\S.*)$")
_SENTENCE_END = ("。", "；", ";", "！", "!", "？", "?")
# ``3120（长）× 2080（宽）`` names the axis, it is not a condition of the value.
_ORIENTATION = frozenset({"长", "宽", "高", "厚", "左", "右", "上", "下", "侧", "前", "后"})
# Bare display technologies are values, while CPU / NFC / WLAN are field captions.
_VALUE_TOKENS = frozenset({"OLED", "AMOLED", "IPS", "LCD", "LTPS", "MINI-LED", "MICRO-LED"})
_VALUE_STARTS = ("支持", "采用", "约", "最大", "最高", "自带", "搭载", "兼容")

# Slot vocabulary used by the sentence library. A slot resolves to the first
# matching field, so the templates never need to know the section layout.
SLOT_ALIASES: dict[str, tuple[str, ...]] = {
    "重量": ("尺寸与重量|重量", "重量"),
    "厚度": ("尺寸与重量|厚度", "尺寸与重量|高度", "厚度"),
    "屏幕尺寸": ("屏幕|尺寸", "屏幕|屏幕尺寸", "屏幕尺寸"),
    "屏幕类型": ("屏幕|类型", "屏幕类型"),
    "分辨率": ("屏幕|分辨率", "分辨率"),
    "刷新率": ("屏幕|刷新率", "刷新率"),
    "屏占比": ("屏幕|屏占比", "屏占比"),
    "电池": ("电池|容量", "电池", "电池容量"),
    "充电": ("充电", "充电规格"),
    "处理器": ("处理器|CPU", "处理器"),
    "操作系统": ("操作系统",),
    "存储": ("存储|机身内存（ROM）", "存储|存储", "存储"),
    "内存": ("内存", "存储|运行内存（RAM）"),
    "摄像头": ("后置摄像头|后置摄像头", "摄像头"),
    "前置摄像头": ("前置摄像头|前置摄像头", "摄像头"),
    "防尘抗水": ("防尘抗水",),
    "接口": ("接口",),
    "蓝牙": ("无线连接|蓝牙", "蓝牙"),
    "星闪": ("无线连接|星闪", "星闪"),
}

# A figure outside this range is the wrong physical quantity in a notebook spec
# table (a few sources label the body depth as 厚度), so the slot stays empty.
SLOT_MAX_MM = {"厚度": 50.0}
# 只有「支持」两字的取值没有信息量，嵌进句子会变成「还能用支持」，宁可不用。
SLOT_REJECT: dict[str, frozenset[str]] = {
    "星闪": frozenset({"支持", "不支持"}),
    "蓝牙": frozenset({"支持", "不支持"}),
}
# When one field lists several values, the one whose wording matches wins.
SLOT_PREFER: dict[str, tuple[str, ...]] = {
    # 快发模式只做笔记本：机身自带的那颗就是前置摄像头。
    "摄像头": ("前置", "后置"),
    "前置摄像头": ("前置",),
    "操作系统": ("Windows", "HarmonyOS"),
}


def _clean(text: str) -> str:
    """Keep the official wording; only collapse padding and inner whitespace runs."""
    return re.sub(r"[ \t]+", " ", str(text).strip())


def _key(text: str) -> str:
    """Comparison form for field names, never used for published text.

    NFKC would rewrite ``酷睿™`` into ``酷睿TM`` and full-width commas into ASCII
    ones, so it is limited to matching slot names.
    """
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(text))).casefold()


def _looks_like_value(text: str) -> bool:
    """Spec values carry numbers, units, compatibility symbols or prose punctuation."""
    value = text.strip()
    if not value:
        return False
    if re.search(r"\d", value):
        return True
    if re.match(r"^(?:Windows|Linux|HarmonyOS|MacOS|Android)\b", value):
        return True
    if value.upper() in _VALUE_TOKENS or value.upper().startswith(tuple(_VALUE_TOKENS)):
        return True
    # ``双层 OLED（柔性显示屏）`` describes the screen, ``运行内存（RAM）`` is a label.
    if ("（" in value or "(" in value) and len(value) >= 10:
        return True
    if "，" in value or "," in value:
        return True
    if value.endswith(_SENTENCE_END):
        return True
    if len(value) >= 16:
        return True
    return value.startswith(_VALUE_STARTS)


def _is_name(text: str) -> bool:
    """A field caption such as 典型亮度 or CPU, never a bare number like 1000000."""
    value = text.strip()
    if not value or len(value) > 32:
        return False
    if re.search(r"[\u4e00-\u9fff]", value):
        return True
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9 .\-]{0,31}", value))


def _drop_brand(name: str) -> str:
    """``HUAWEI MateBook Pro S 标准屏版`` → ``标准屏版``; short captions untouched."""
    value = name.strip()
    if len(value) <= 12:
        return value
    stripped = re.sub(r"^[A-Za-z][A-Za-z0-9 .\-]*?\s+(?=[\u4e00-\u9fff])", "", value)
    return stripped.strip() or value


def _is_label(text: str) -> bool:
    value = text.strip()
    if not value or "\n" in value or value.startswith("*"):
        return False
    if len(value) > 14 or value.endswith(("：", ":")):
        return False
    return not _looks_like_value(value)


def _blocks(lines: list[str]) -> list[str]:
    """Blank-line separated blocks, keeping a block's internal line breaks."""
    blocks, current = [], []
    for raw in lines:
        line = raw.rstrip()
        if line.strip():
            current.append(line.strip())
        elif current:
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))
    return blocks


def _split_sections(text: str) -> tuple[str, str, list[tuple[str, list[str]]]]:
    """Return the H1 title, the intro blockquote and the ``## `` sections."""
    title, intro = "", ""
    sections: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    for raw in str(text).splitlines():
        heading = _HEADING.match(raw.strip())
        if heading:
            if len(heading["level"]) == 1:
                title = heading["title"]
                current = None
            else:
                sections.append((heading["title"], []))
                current = sections[-1][1]
            continue
        if current is None:
            if raw.strip().startswith(">") and not intro:
                intro = raw.strip().lstrip(">").strip()
            continue
        current.append(raw)
    return title, intro, sections


def _value(text: str, *, variant: str = "", label: str = "") -> dict:
    """Split an inline condition such as ``约 1.33 kg（圆键盘含电池）``."""
    text = _clean(text)
    inline = ""
    matched = _PAREN.search(text)
    if matched and len(matched["inner"]) <= 40 and matched["inner"].strip() not in _ORIENTATION:
        inline = _clean(matched["inner"])
        text = text[: matched.start()].strip()
    # Footnote markers (``USB-C × 1*``) point at the caveats below; the caveat is
    # already collected separately, so the marker itself is not part of the value.
    text = re.sub(r"\*+", "", text).strip().rstrip("；;，,")
    # 官方写法「支持，星闪 E1.0」带着一个是非标记和一个逗号，嵌进句子会断句。
    text = re.sub(r"^支持\s*[，,]\s*", "", text)
    return {"text": text, "variant": variant, "label": label, "inline": inline, "conditions": []}


def _parse_section(title: str, lines: list[str]) -> list[dict]:
    """Pair field labels with the values beneath them inside one section.

    Markdown here is one logical item per line; blank lines only separate. Each
    field keeps the raw lines it was built from, so the official wording can be
    shown next to the value it produced.
    """
    fields: list[dict] = []
    field: dict | None = None
    variant = ""

    def start(name: str) -> dict:
        item = {"section": title, "name": name, "values": [], "conditions": [], "raw": []}
        fields.append(item)
        return item

    def remember(text: str) -> None:
        target = field if field is not None else (fields[-1] if fields else None)
        if target is not None and text not in target["raw"]:
            target["raw"].append(text)

    def append_value(value: dict, text: str) -> None:
        target = field if field is not None else (fields[-1] if fields else start(""))
        target["values"].append(value)
        remember(text)

    for block in (line.strip() for line in lines if line.strip()):
        caveat = _CAVEAT.match(block)
        if caveat:
            target = field or (fields[-1] if fields else None)
            if target is not None:
                target["conditions"].append(_clean(caveat["text"]))
                remember(block)
            continue
        bullet = _BULLET.match(block)
        if bullet:
            append_value(_value(bullet["text"], variant=variant), block)
            continue
        variant_label = _VARIANT.match(block)
        if variant_label and _is_name(variant_label["name"]):
            variant = _drop_brand(_clean(variant_label["name"]))
            field = field or start("")
            remember(block)
            continue
        sub = _SUBLABEL.match(block)
        if sub and _is_name(sub["name"]) and (field or fields):
            target = field or fields[-1]
            caption = _drop_brand(_clean(sub["name"]))
            if not target["values"] and not target["name"]:
                target["name"] = caption
            append_value(_value(sub["value"], variant=variant, label=caption), block)
            continue
        if _is_label(block):
            field = start(_clean(block))
            variant = ""
            remember(block)
            continue
        append_value(_value(block, variant=variant), block)

    for item in fields:
        item["values"] = [value for value in item["values"] if value["text"]]
        item["quote"] = "\n".join(item.pop("raw"))
        for value in item["values"]:
            # A section-level caveat qualifies every value of the field.
            value["conditions"] = list(item["conditions"])
    return [item for item in fields if item["values"]]


def parse_card(text: str, *, folder: str, category: str, library: str) -> dict:
    """Build one fact card from the raw markdown of a ``产品事实.md`` file."""
    title, intro, sections = _split_sections(text)
    model = re.sub(r"\s*[-—]\s*产品事实\s*$", "", title).strip() or folder
    card = {
        "version": CARD_VERSION,
        "model": model,
        "folder": folder,
        "category": category,
        "library": library,
        "captured": (_CAPTURED.search(intro) or {"date": ""})["date"] if intro else "",
        "urls": [],
        "positioning": "",
        "selling_titles": [],
        "source_note": intro,
        "fields": [],
    }
    body_quote: list[str] = []
    for heading, lines in sections:
        if heading in _DOC_SECTIONS:
            for block in _blocks(lines):
                bullet = _BULLET.match(block)
                if heading == "来源":
                    card["urls"].extend(_URL.findall(bullet["text"] if bullet else block))
                elif bullet:
                    card["urls"].extend(_URL.findall(bullet["text"]))
            continue
        if heading in _COPY_SECTIONS:
            if heading == "官网定位":
                card["positioning"] = " ".join(_blocks(lines))
            else:
                titles = [(_BULLET.match(line.strip()) or {"text": line.strip()})["text"]
                          for line in lines if line.strip()]
                card["selling_titles"] = [title.lstrip("-*•· ").strip() for title in titles]
            continue
        card["fields"].extend(_parse_section(heading, lines))
        body_quote.extend(_blocks(lines))
    card["urls"] = list(dict.fromkeys(card["urls"]))
    return card


def card_from_file(path: Path, *, library: str) -> dict:
    """Parse one model folder; the folder names carry the category and model."""
    product_dir = Path(path).resolve().parent
    return parse_card(
        Path(path).read_text(encoding="utf-8", errors="replace"),
        folder=product_dir.name,
        category=product_dir.parent.name,
        library=library,
    )


_VERSION_LABEL = ("版", "态", "款")


def display(value: dict) -> str:
    """Render one value with the condition that must travel with it."""
    text = _clean(value.get("text", ""))
    condition = _clean(value.get("inline") or "") or _clean(value.get("variant") or "")
    label = _clean(value.get("label") or "")
    if label and label not in text:
        # 版本词（标准屏版 / 柔光版 / 典藏版）放在括号里更像人话：「798 g（标准屏版）」；
        # 典型亮度这类属性名必须前置才能读通。值本身已带括号时不再追加，避免两层括号。
        if label.endswith(_VERSION_LABEL) and "（" not in text:
            text = f"{text}（{label}）"
        else:
            text = f"{label} {text}"
    return f"{text}（{condition}）" if condition and condition not in text else text


def slot_key(section: str, name: str) -> str:
    return f"{section}|{name}" if name else section


_PORT_TOKENS = (
    (re.compile(r"USB[\s-]*(?:Type[\s-]*)?C\b", re.I), "USB-C"),
    (re.compile(r"USB[\s-]*(?:Type[\s-]*)?A\b", re.I), "USB-A"),
    (re.compile(r"HDMI\s*[\d.]*", re.I), "HDMI"),
    (re.compile(r"Thunderbolt\s*\d?", re.I), "雷电"),
    (re.compile(r"DisplayPort\s*[\d.]*", re.I), "DP"),
    (re.compile(r"3\.5\s*mm", re.I), "3.5 mm 耳机口"),
    (re.compile(r"SD\s*卡", re.I), "SD 卡槽"),
    (re.compile(r"RJ45", re.I), "网口"),
)


def _port_summary(card: dict) -> str | None:
    """接口的卖点是「有哪几类口」，不是那一整段端口清单。"""
    lines = [str(value.get("text", "")) for field in card.get("fields", [])
             if field["section"] == "接口" for value in field["values"]]
    if not lines:
        return None
    text = " ".join(lines)
    found: list[str] = []
    for pattern, label in _PORT_TOKENS:
        if label not in found and pattern.search(text):
            found.append(label)
    return "、".join(found[:3]) or None


def _millimetres(text: str) -> float | None:
    found = re.search(r"(\d+(?:\.\d+)?)\s*(mm|厘米|cm)", str(text), re.I)
    if not found:
        return None
    number = float(found.group(1))
    return number * 10 if found.group(2).lower() in {"厘米", "cm"} else number


def _pick_value(slot: str, values: list[dict]) -> dict | None:
    """Choose the value a slot should use; ``None`` means no trustworthy value."""
    if not values:
        return None
    hints = SLOT_PREFER.get(slot, ())
    for value in values:
        if any(hint in value["text"] for hint in hints):
            return value
    cap = SLOT_MAX_MM.get(slot)
    if cap is not None:
        for value in values:
            size = _millimetres(value["text"])
            if size is not None and size > cap:
                continue
            return value
        return None
    if len(values) == 1:
        return values[0]
    # A section-level list (CPU / 麒麟 X90, WLAN / Wi-Fi 7) keeps the most
    # informative entry; a named field keeps its first official value.
    return max(values, key=lambda item: len(item["text"]))


def resolve(card: dict, slot: str) -> dict | None:
    """Find the field a sentence-library slot refers to, if the card has it.

    Only declared slots resolve: ``SLOT_ALIASES`` is the sentence library's
    vocabulary, so a template can never reach an arbitrary raw field such as a
    long connector list and paste it into published copy. Fields that repeat
    inside one section (two SKUs in one table) are merged instead of the last
    one silently winning.
    """
    if slot not in SLOT_ALIASES:
        return None
    if slot == "接口":
        summary = _port_summary(card)
        if not summary:
            return None
        field = next((item for item in card.get("fields", []) if item["section"] == "接口"), None)
        quote = (field or {}).get("quote", summary)
        return {"slot": slot, "section": "接口", "name": (field or {}).get("name", ""),
                "text": summary, "raw": summary, "condition": "", "conditions": [],
                "quote": quote, "source": quote, "url": (card.get("urls") or [""])[0]}
    index: dict[str, list[dict]] = {}
    for field in card.get("fields", []):
        index.setdefault(_key(slot_key(field["section"], field["name"])), []).append(field)
    for candidate in SLOT_ALIASES.get(slot, (slot,)):
        fields = index.get(_key(candidate)) or []
        pairs: list[tuple[dict, dict]] = []
        seen: set[str] = set()
        for field in fields:
            for value in field["values"]:
                rendered = display(value)
                if rendered and rendered not in seen:
                    seen.add(rendered)
                    pairs.append((field, value))
        picked = _pick_value(slot, [value for _, value in pairs])
        if picked is None:
            continue
        if _clean(picked["text"]) in SLOT_REJECT.get(slot, frozenset()):
            continue
        # 「点开数字看官方原文」要指到这条值自己的那张表，不是同名段的第一份。
        field = next(candidate_field for candidate_field, value in pairs if value is picked)
        try:
            picked_index = [value for _, value in pairs].index(picked)
        except ValueError:
            picked_index = 0
        quote = field["quote"]
        return {
            "slot": slot,
            "section": field["section"],
            "name": field["name"],
            "text": display(picked),
            "raw": picked["text"],
            "condition": _clean(picked.get("inline") or picked.get("variant") or ""),
            "conditions": list(picked.get("conditions") or []),
            "quote": (picked.get("label") or field["name"] or field["section"]) + "\n\n" + "\n\n".join(
                display(value) for _, value in pairs),
            "source": quote,
            "url": (card.get("urls") or [""])[0],
            "value_index": picked_index,
        }
    return None


def source_dir(card: dict) -> Path | None:
    """Locate the P1 folder a card came from; images are read from there at runtime."""
    library = str((card or {}).get("library", "")).strip()
    category = str((card or {}).get("category", "")).strip()
    folder = str((card or {}).get("folder", "")).strip()
    if not library or not category or not folder:
        return None
    path = WORKSPACE_ROOT / library / "P1-产品参数库" / category / folder
    return path if path.is_dir() else None


def _image_theme(name: str) -> str:
    """``hwpc_matebook-14_高清护眼屏幕_05_ab12.png`` → ``高清护眼屏幕``."""
    parts = Path(name).stem.split("_")
    if len(parts) >= 3 and parts[-2].isdigit():
        return parts[-3].strip()
    return ""


# 两套知识库的配图清单文件名与列名不同，读的时候统一成同一种行结构。
INDEX_FILES = ("图片索引.csv", "images/图片清单.csv")


def _manifest_row(row: dict) -> dict:
    """Normalize 图片索引.csv / 图片清单.csv rows to one shape."""
    return {
        "name": Path(str(row.get("文件名", "")).strip()).name,
        "official": str(row.get("官网图片说明") or row.get("说明") or "").strip(),
        "placement": str(row.get("建议用途", "") or "").strip(),
        "source_url": str(row.get("来源页面") or row.get("来源URL") or "").strip(),
        "width": str(row.get("宽度", "") or "").strip(),
        "height": str(row.get("高度", "") or "").strip(),
    }


def _caption(theme: str, official: str, fallback: str) -> str:
    """文件名主题只在是中文画面描述时优先，官方英文 slug 不如官网说明好读。"""
    if theme and re.search(r"[\u4e00-\u9fff]", theme):
        return theme
    return official or fallback


def _image_rows(folder: Path) -> list[dict]:
    """Read the image manifest when it exists, so captions and usage notes travel with the file."""
    index = next((folder / relative for relative in INDEX_FILES if (folder / relative).is_file()), None)
    if index is None:
        return []
    rows = []
    with index.open(encoding="utf-8-sig", newline="") as stream:
        for raw in csv.DictReader(stream):
            row = _manifest_row(raw)
            if not row["name"]:
                continue
            path = folder / "images" / row["name"]
            if not path.is_file() or path.stat().st_size > MAX_IMAGE_BYTES:
                continue
            rows.append({
                "path": str(path),
                "title": _caption(_image_theme(row["name"]), row["official"], path.stem),
                "official": row["official"],
                "placement": row["placement"],
                "source_url": row["source_url"],
                "width": row["width"],
                "height": row["height"],
            })
    return rows


def images(card: dict) -> list[dict]:
    """同型号官方配图：先按索引取，索引缺失时退回目录里的图片文件。

    图片不进事实卡（体积大、有版权，仓库里也提交不了），运行时按卡片里的
    库/类目/目录名回源目录读；部署在魔搭等环境时没有本地知识库目录，改从
    私有归档 ZIP 里取（见 ``_archive_image_rows``）。两处都取不到时返回空列表。
    """
    folder = source_dir(card)
    if folder is not None:
        cached = _IMAGE_CACHE.get(str(folder))
        if cached is not None:
            return [dict(item) for item in cached]
        rows = _image_rows(folder)
        if not rows:
            for path in sorted((folder / "images").glob("*")) if (folder / "images").is_dir() else []:
                if path.suffix.lower() in IMAGE_SUFFIXES and path.is_file() and path.stat().st_size <= MAX_IMAGE_BYTES:
                    rows.append({"path": str(path), "title": path.stem, "placement": "",
                                 "source_url": "", "width": "", "height": ""})
        _IMAGE_CACHE[str(folder)] = rows
        return [dict(item) for item in rows]
    return _archive_image_rows(card)


# --- 部署环境（魔搭创空间）用：从私有知识库归档 ZIP 里取图 -------------------
ARCHIVE_IMAGE_ROOT = Path(tempfile.gettempdir()) / "zh-quick-images"
_ARCHIVE_CACHE: dict[tuple[str, str], list[dict]] = {}


def _safe_member(name: str) -> bool:
    if not name or name.startswith("/") or "\\" in name or ".." in name.split("/"):
        return False
    return Path(name).name not in {"", ".", ".."}


def _archive_image_rows(card: dict) -> list[dict]:
    """Read 图片索引.csv + images out of the private knowledge archive.

    Studio 里没有工作区知识库目录，图片只存在于部署者提供的私有归档 ZIP
    （``IMA_ARCHIVE_URL`` / ``IMA_ARCHIVE_PATH``）。这里按卡片的类目/目录名在
    归档里定位 ``图片索引.csv``，把被引用的图片解到系统临时目录（Gradio 允许
    读取临时目录），再交给界面；原图不进入代码仓库。
    """
    category = str((card or {}).get("category", "")).strip()
    folder = str((card or {}).get("folder", "")).strip()
    if not category or not folder:
        return []
    try:
        from knowledge_store import get_archive_path

        archive = get_archive_path()
    except Exception:  # 归档未配置或下载失败：界面会说明没有配图
        return []
    if not archive:
        return []
    path = Path(str(archive))
    key = (str(path), f"{category}/{folder}")
    cached = _ARCHIVE_CACHE.get(key)
    if cached is not None:
        return [dict(item) for item in cached]
    try:
        with zipfile.ZipFile(path) as bundle:
            rows = _archive_rows_from_zip(bundle, category, folder)
    except (OSError, zipfile.BadZipFile, RuntimeError):
        return []
    _ARCHIVE_CACHE[key] = rows
    return [dict(item) for item in rows]


def _archive_rows_from_zip(bundle: zipfile.ZipFile, category: str, folder: str) -> list[dict]:
    """Locate either manifest layout inside the archive and extract its images."""
    members = [name for name in bundle.namelist() if _safe_member(name)]
    index, prefix = "", ""
    for relative in INDEX_FILES:
        wanted = f"{category}/{folder}/{relative}"
        found = next((name for name in members if name.endswith(wanted)), "")
        if not found:
            continue
        index = found
        prefix = found[: -len(relative)]
        break
    if not index:
        return []
    import io

    text = bundle.read(index).decode("utf-8-sig", "replace")
    target = ARCHIVE_IMAGE_ROOT / hashlib.sha1(prefix.encode("utf-8")).hexdigest()[:16]
    rows: list[dict] = []
    for raw in csv.DictReader(io.StringIO(text)):
        row = _manifest_row(raw)
        name = row["name"]
        if not name or Path(name).suffix.lower() not in IMAGE_SUFFIXES:
            continue
        try:
            content = bundle.read(f"{prefix}images/{name}")
        except KeyError:
            continue
        if not content or len(content) > MAX_IMAGE_BYTES:
            continue
        extracted = target / name
        if not extracted.is_file():
            target.mkdir(parents=True, exist_ok=True)
            extracted.write_bytes(content)
        rows.append({
            "path": str(extracted),
            "title": _caption(_image_theme(name), row["official"], extracted.stem),
            "official": row["official"],
            "placement": row["placement"],
            "source_url": row["source_url"],
            "width": row["width"],
            "height": row["height"],
        })
    return rows


def slug(model_folder: str, taken: set[str] | None = None) -> str:
    """A filesystem-safe card name; collisions get a numeric suffix."""
    base = re.sub(r'[\\/:*?"<>|]', "_", _clean(model_folder)).strip(" .") or "model"
    if not taken or base not in taken:
        return base
    index = 2
    while f"{base}-{index}" in taken:
        index += 1
    return f"{base}-{index}"


def write_card(card: dict, root: Path = FACTS_DIR) -> Path:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{slug(card['folder'], {p.stem for p in root.glob('*.json')})}.json"
    target.write_text(json.dumps(card, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    return target


def load_index(root: Path = FACTS_DIR) -> dict:
    path = Path(root) / INDEX_FILE
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"cards": {}}


def load_card(model: str, root: Path = FACTS_DIR) -> dict | None:
    """Load one card by model name or folder name; ``None`` when unavailable."""
    cards = load_index(root).get("cards", {})
    entry = cards.get(model)
    if entry is None:
        for name, candidate in cards.items():
            if _key(name) == _key(model):
                entry = candidate
                break
    if entry is None:
        return None
    path = Path(root) / entry["file"]
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def catalogue(root: Path = FACTS_DIR) -> list[str]:
    """Model names that have a generated card, in library order."""
    return sorted(load_index(root).get("cards", {}))
