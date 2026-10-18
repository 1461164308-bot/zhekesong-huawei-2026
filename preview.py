"""Platform layouts using only verified local images, with optional audit labels."""
from __future__ import annotations

import base64
from html import escape
from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageOps

from policy import PLATFORM_RULES, normalize
from public_payload import sanitize_public


_ORIGINS = {
    "live_ima": "实时 ima",
    "ima_cache": "ima 已检索缓存",
    "offline_archive": "主办方 ZIP 缓存（非实时 ima）",
    "official_vmall": "华为官方商城本次读取",
}
_REFERENCE_GROUP = re.compile(r"[\[【（(]\s*[FS]\d+(?:[\s,，、;；/]+[FS]\d+)*\s*[\]】）)]", re.I)
_REFERENCE_ID = re.compile(r"(?<![A-Za-z0-9_])`?[FS]\d+`?(?![A-Za-z0-9_])", re.I)
_LOCAL_PATH = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\)[^\s<>\"'，。；！？]+"
    r"|/(?:Users|home|tmp|private|var|mnt|root|workspace|cache)/[^\s<>\"'，。；！？]+"
)


def clean_publish_text(value: object) -> str:
    """Remove audit citations and private paths without rewriting approved claims."""
    value = str(sanitize_public(str(value or "")))
    value = _LOCAL_PATH.sub("", value)
    value = _REFERENCE_GROUP.sub("", value)
    value = _REFERENCE_ID.sub("", value)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def publish_units(units: list[dict], platform: str) -> list[dict]:
    """Keep publication fields only; internal insights and demo scripts stay out."""
    result = []
    for unit in units:
        uid = str(unit.get("id", ""))
        if uid not in {"title", "intro", "cta", "tags"} and not uid.startswith("section_"):
            continue
        if uid == "tags" and platform != "小红书":
            continue
        content = clean_publish_text(unit.get("text", ""))
        if content:
            result.append({"id": uid, "text": content,
                           "heading": clean_publish_text(unit.get("heading", ""))})
    return result


def prepare_images(images: list[dict], task: dict) -> list[dict]:
    """Decode local files, preserve aspect ratio, and return metadata-free JPGs.

    The caller supplies the verified image selection. This boundary also rejects
    nonlocal paths, unreadable files and a model that contradicts the task. Files
    are never modified, fetched or copied verbatim into an export.
    """
    ordered = []
    for position, image in enumerate(images):
        try:
            slot = max(0, min(20, int(image.get("slot", 0))))
        except (TypeError, ValueError):
            slot = 0
        ordered.append((slot, position, image))
    result = []
    limit = PLATFORM_RULES.get(task.get("platform"), {}).get("image_max", 6)
    for slot, _, image in sorted(ordered, key=lambda item: (item[0], item[1])):
        if len(result) >= limit:
            break
        try:
            raw_path = str(image.get("path", ""))
            if not raw_path or raw_path.lower().startswith(("http:", "https:", "data:", "file:")) or raw_path.startswith(("\\\\", "//")):
                continue
            if task.get("product") and image.get("model") and normalize(task["product"]) != normalize(image["model"]):
                continue
            path = Path(raw_path)
            if not path.is_file():
                continue
            with Image.open(path) as source:
                if source.width * source.height > 40_000_000:
                    continue
                source.load()
                picture = ImageOps.exif_transpose(source)
                picture.thumbnail((1600, 1600))
                # A new pixel buffer drops EXIF, comments, ICC and source metadata.
                rgb = Image.new("RGB", picture.size, "white")
                if picture.mode in {"RGBA", "LA"} or "transparency" in picture.info:
                    rgba = picture.convert("RGBA")
                    rgb.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    rgb.paste(picture.convert("RGB"))
                output = BytesIO()
                rgb.save(output, "JPEG", quality=88)
                result.append({"image": image, "slot": slot, "jpeg": output.getvalue(),
                               "width": rgb.width, "height": rgb.height})
        except (OSError, ValueError, KeyError, TypeError, Image.DecompressionBombError):
            continue
    return result


def _text(value: object, audit: bool = False) -> str:
    plain = str(sanitize_public(str(value or ""))) if audit else clean_publish_text(value)
    return escape(plain, quote=True).replace("\n", "<br>")


def render_platform(units: list[dict], pictures: list[dict], task: dict,
                    mode_label: str = "", *, audit: bool = False) -> str:
    """Render prepared images; audit=False is suitable for the publishing bundle."""
    platform = str(task.get("platform", "门店朋友圈"))
    visible = [u for u in units if str(u.get("id", "")) in {"title", "intro", "cta", "tags"}
               or str(u.get("id", "")).startswith("section_")] if audit else publish_units(units, platform)
    by_id = {str(unit.get("id")): unit for unit in visible}
    sections = [unit for unit in visible if str(unit.get("id", "")).startswith("section_")]
    if platform == "门店海报":
        sections, pictures = sections[:3], pictures[:1]
    text = lambda value: _text(value, audit)

    def refs(unit: dict) -> str:
        ids = " ".join("[" + text(ref) + "]" for ref in unit.get("fact_ids", [])) if audit else ""
        return f' <small style="font-size:11px;color:#087e83">{ids}</small>' if ids else ""

    def body(unit: dict, style: str) -> str:
        return f'<p style="{style}">{text(unit.get("text", ""))}{refs(unit)}</p>'

    def picture(item: dict, index: int) -> str:
        image = item["image"]
        data = base64.b64encode(item["jpeg"]).decode("ascii")
        caption = text(image.get("caption") or image.get("title", ""))
        if audit:
            # A combined article mode may include Mall facts; image origin is separate.
            origin = _ORIGINS.get(image.get("origin"), "未标注图源模式")
            caption = (f'[{text(image.get("id", ""))}] {caption}<br>'
                       f'来源：{text(image.get("source_title", ""))} · {text(origin)}'
                       f' · 型号：{text(image.get("model", ""))}')
        elif platform in {"小红书", "门店朋友圈"}:
            caption = f'{index:02d}' + (f' · {caption}' if caption else "")
        return (f'<figure style="margin:20px 0;min-width:0">'
                f'<img src="data:image/jpeg;base64,{data}" '
                f'alt="{text(image.get("title", "产品配图"))}" '
                'style="display:block;width:100%;height:auto;max-width:100%;object-fit:contain;border-radius:8px;background:#f6f8fa">'
                f'<figcaption style="font-size:12px;color:#718096;line-height:1.65;margin-top:8px;text-align:center">{caption}</figcaption></figure>')

    styles = {
        "小红书": "max-width:720px;padding:24px;background:#fffaf8;color:#253645;line-height:1.85",
        "微信公众号": "max-width:677px;padding:24px 20px;background:#fff;color:#263443;line-height:1.9;letter-spacing:.03em",
        "门店朋友圈": "max-width:560px;padding:22px;background:#fff;color:#253645;line-height:1.8",
        "门店海报": "max-width:600px;padding:30px 26px;background:#eff7f5;color:#143d3a;line-height:1.6;text-align:center",
    }
    style = styles.get(platform, styles["门店朋友圈"])
    chunks = [f'<article data-platform="{escape(platform, quote=True)}" style="{style};margin:0 auto;box-sizing:border-box;font-family:Microsoft YaHei,PingFang SC,sans-serif;overflow-wrap:anywhere">']
    if audit:
        chunks.append(f'<div style="font-size:11px;color:#087e83;margin-bottom:16px">知衡 · {text(platform)}图文方案 · {text(mode_label)}</div>')
    if "title" in by_id:
        size = 34 if platform == "门店海报" else 27 if platform == "微信公众号" else 24
        chunks.append(f'<h1 style="font-size:{size}px;line-height:1.45;margin:4px 0 20px;font-weight:700">{text(by_id["title"].get("text", ""))}{refs(by_id["title"])}</h1>')
    if "intro" in by_id:
        intro_style = "font-size:16px;margin:12px 0 22px;color:#506273"
        if platform == "微信公众号":
            intro_style += ";padding:16px 18px;background:#f5f8fa;border-left:3px solid #147d78"
        elif platform == "门店海报":
            intro_style = "font-size:19px;margin:0 0 22px;color:#466c65"
        chunks.append(body(by_id["intro"], intro_style))

    if platform == "微信公众号":
        by_slot: dict[int, list[tuple[int, dict]]] = {}
        for index, item in enumerate(pictures, 1):
            by_slot.setdefault(item["slot"], []).append((index, item))
        chunks.extend(picture(item, index) for index, item in by_slot.pop(0, []))
        for number, unit in enumerate(sections, 1):
            chunks.append('<section style="margin:28px 0">')
            if unit.get("heading"):
                chunks.append(f'<h2 style="font-size:20px;line-height:1.6;margin:0 0 12px;color:#146d68;border-bottom:1px solid #e1ecea;padding-bottom:9px">{number:02d} · {text(unit["heading"])}</h2>')
            chunks.append(body(unit, "font-size:16px;line-height:1.9;margin:12px 0"))
            chunks.extend(picture(item, index) for index, item in by_slot.pop(number, []))
            chunks.append("</section>")
        for slot in sorted(by_slot):
            chunks.extend(picture(item, index) for index, item in by_slot[slot])
    elif platform == "小红书":
        for number, unit in enumerate(sections, 1):
            chunks.append('<section style="margin:16px 0;padding:18px 20px;border:1px solid #f1e1db;border-radius:14px;background:#fff">')
            if unit.get("heading"):
                chunks.append(f'<h2 style="font-size:18px;line-height:1.6;margin:0 0 10px;color:#b34c43">{number:02d} · {text(unit["heading"])}</h2>')
            chunks.append(body(unit, "font-size:15px;line-height:1.85;margin:8px 0"))
            chunks.append("</section>")
        chunks.append('<section aria-label="有序配图" style="margin:22px 0">')
        chunks.extend(picture(item, index) for index, item in enumerate(pictures, 1))
        chunks.append("</section>")
    elif platform == "门店海报":
        chunks.extend(picture(item, index) for index, item in enumerate(pictures, 1))
        chunks.append('<ul style="list-style:none;text-align:left;padding:0;margin:20px 0">')
        for unit in sections:
            heading = f'<strong>{text(unit["heading"])}</strong><br>' if unit.get("heading") else ""
            chunks.append(f'<li style="padding:11px 14px;margin:8px 0;background:#fff;border-radius:8px;font-size:16px">{heading}{text(unit.get("text", ""))}{refs(unit)}</li>')
        chunks.append("</ul>")
    else:
        for unit in sections:
            if unit.get("heading"):
                chunks.append(f'<p style="font-size:15px;font-weight:700;margin:12px 0 4px">{text(unit["heading"])}</p>')
            chunks.append(body(unit, "font-size:15px;line-height:1.8;margin:8px 0"))

    if "cta" in by_id:
        chunks.append(body(by_id["cta"], "margin:24px 0 12px;padding:15px 17px;background:#e8f4f0;border-radius:8px;font-size:15px;color:#245c51"))
    if platform == "门店朋友圈" or platform not in styles:
        columns = min(3, len(pictures)) or 1
        chunks.append(f'<section aria-label="有序配图" style="display:grid;grid-template-columns:repeat({columns},minmax(0,1fr));gap:10px">')
        chunks.extend(picture(item, index) for index, item in enumerate(pictures, 1))
        chunks.append("</section>")
    if platform == "小红书" and "tags" in by_id:
        chunks.append(body(by_id["tags"], "font-size:13px;color:#b34c43;margin:18px 0 0"))
    if audit:
        chunks.append('<div style="border-top:1px solid #e3ebf1;margin-top:24px;padding-top:12px;font-size:11px;color:#718496;text-align:left">团队独立开发，非华为官方产品。产品事实请对照核验记录；具体款式、软件适配及当天销售政策须发布前确认。</div>')
    chunks.append("</article>")
    return "".join(chunks)


def build_preview(units: list[dict], images: list[dict], task: dict, mode_label: str) -> str:
    """Retain the original public signature and self-contained image contract."""
    return render_platform(units, prepare_images(images, task), task, mode_label, audit=True)
