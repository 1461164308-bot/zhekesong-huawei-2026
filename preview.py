"""Safe, self-contained visual preview made only from verified local ima images."""
from __future__ import annotations

import base64
from html import escape
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


def build_preview(units: list[dict], images: list[dict], task: dict, mode_label: str) -> str:
    def text(value: str) -> str:
        return escape(str(value)).replace("\n", "<br>")

    def picture(image: dict) -> str:
        try:
            path = Path(image["path"])
            with Image.open(path) as im:
                im = ImageOps.exif_transpose(im)
                # Fit, never stretch. Convert only for display; original remains untouched.
                im.thumbnail((1200, 1200))
                if im.mode == "RGBA":
                    bg = Image.new("RGB", im.size, "white")
                    bg.paste(im, mask=im.getchannel("A"))
                    im = bg
                else:
                    im = im.convert("RGB")
                output = BytesIO()
                im.save(output, "JPEG", quality=88)
            data = base64.b64encode(output.getvalue()).decode("ascii")
        except (OSError, ValueError, KeyError):
            return ""
        return (f'<figure style="margin:20px 0"><img src="data:image/jpeg;base64,{data}" '
                f'alt="{escape(str(image.get("title", "ima配图")), quote=True)}" '
                'style="display:block;width:100%;max-height:520px;object-fit:contain;border-radius:12px;background:#f6f8fa">'
                f'<figcaption style="font-size:11px;color:#61778b;line-height:1.65;margin-top:7px">'
                f'[{text(image["id"])}] {text(image["caption"])}<br>来源：{text(image.get("source_title", ""))}'
                f' · 型号：{text(image["model"])} · {text(mode_label)}</figcaption></figure>')

    by_slot: dict[int, list[dict]] = {}
    for image in images:
        try:
            slot = max(0, min(20, int(image.get("slot", 0))))
        except (TypeError, ValueError):
            slot = 0
        by_slot.setdefault(slot, []).append(image)
    chunks = ['<article style="max-width:820px;margin:0 auto;padding:26px 28px;background:white;color:#18324a;line-height:1.9;border:1px solid #dce6ed;border-radius:16px;font-family:Inter,Microsoft YaHei,sans-serif">',
              f'<div style="font-size:11px;color:#087e83;letter-spacing:.04em">知衡 · {text(task["platform"])}图文方案 · {text(mode_label)}</div>']
    section = 0
    for unit in units:
        uid = unit["id"]
        content = text(unit["text"])
        refs = " ".join("[" + text(x) + "]" for x in unit.get("fact_ids", []))
        if uid == "title":
            chunks.append(f'<h1 style="font-size:27px;line-height:1.45;margin:16px 0">{content}</h1>')
        elif uid == "intro":
            chunks.append(f'<p style="font-size:15px;color:#425f77">{content} <small style="color:#087e83">{refs}</small></p>')
            chunks.extend(picture(x) for x in by_slot.pop(0, []))
        elif uid.startswith("section_"):
            section += 1
            if unit.get("heading"):
                chunks.append(f'<h2 style="font-size:18px;margin:24px 0 8px">{text(unit["heading"])}</h2>')
            chunks.append(f'<p style="font-size:14px;margin:9px 0">{content} <small style="color:#087e83">{refs}</small></p>')
            chunks.extend(picture(x) for x in by_slot.pop(section, []))
        elif uid == "cta":
            # Remaining images are inserted before the closing CTA, not below the footer.
            for slot in sorted(by_slot):
                chunks.extend(picture(x) for x in by_slot[slot])
            by_slot.clear()
            chunks.append(f'<p style="padding:14px 16px;background:#eff8f6;border-left:3px solid #087e83;font-size:14px">{content}</p>')
        elif uid == "tags":
            chunks.append(f'<p style="font-size:12px;color:#087e83">{content}</p>')
    for slot in sorted(by_slot):
        chunks.extend(picture(x) for x in by_slot[slot])
    chunks.append('<div style="border-top:1px solid #e3ebf1;margin-top:20px;padding-top:12px;font-size:11px;color:#718496">'
                  '团队独立开发，非华为官方产品。产品事实请对照核验记录；具体款式、软件适配及当天销售政策须发布前确认。</div></article>')
    return "".join(chunks)
