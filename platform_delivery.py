"""Clean, local-only publishing artifacts and deterministic platform checks."""
from __future__ import annotations

from html import escape
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile

from policy import PLATFORM_RULES
from preview import clean_publish_text, prepare_images, publish_units, render_platform


_BODY_LIMITS = {"小红书": (350, 650), "微信公众号": (650, 1000),
                "门店朋友圈": (80, 180), "门店海报": (40, 120)}


def _platform_checks(units: list[dict], pictures: list[dict], images: list[dict], task: dict) -> dict:
    platform = str(task.get("platform", ""))
    rules = PLATFORM_RULES.get(platform, PLATFORM_RULES["门店朋友圈"])
    clean = publish_units(units, platform)
    by_id = {unit["id"]: unit for unit in clean}
    sections = [unit for unit in clean if unit["id"].startswith("section_")]
    title = by_id.get("title", {}).get("text", "")
    body = "".join(unit["text"] for unit in clean
                   if unit["id"] in {"intro", "cta"} or unit["id"].startswith("section_"))
    count = len(re.findall(r"[\u4e00-\u9fff]", body))
    minimum, maximum = _BODY_LIMITS.get(platform, (80, 180))
    headings = sum(bool(unit.get("heading")) for unit in sections)
    headings_required = platform in {"小红书", "微信公众号"}
    tags = by_id.get("tags", {}).get("text", "")
    has_tags = bool(re.search(r"#[^\s#]+", tags))
    checks = {
        "platform": platform,
        "title": {"characters": len(title), "max": rules["title_max"],
                  "ok": bool(title) and len(title) <= rules["title_max"]},
        "body": {"chinese_characters": count, "min": minimum, "max": maximum,
                 "ok": minimum <= count <= maximum},
        "images": {"count": len(pictures), "min": rules["image_min"], "max": rules["image_max"],
                   "requested": len(images),
                   "ok": rules["image_min"] <= len(pictures) <= rules["image_max"] and len(pictures) == len(images)},
        "sections": {"count": len(sections), "max": rules["sections"],
                     "ok": 1 <= len(sections) <= rules["sections"]},
        "headings": {"count": headings, "required": headings_required,
                     "ok": not headings_required or bool(sections) and headings == len(sections)},
        "tags": {"required": bool(rules["tags"]), "present": has_tags,
                 "ok": has_tags if rules["tags"] else not bool(tags)},
        "intro": {"present": "intro" in by_id, "required": platform in {"微信公众号", "门店海报"},
                  "ok": platform not in {"微信公众号", "门店海报"} or "intro" in by_id},
        "cta": {"present": "cta" in by_id, "ok": "cta" in by_id},
    }
    issues = []
    if platform not in PLATFORM_RULES:
        issues.append("请选择受支持的发布平台。")
    if not checks["title"]["ok"]:
        issues.append(f"标题需填写且不超过{rules['title_max']}个字符，当前{len(title)}个。")
    if not checks["body"]["ok"]:
        issues.append(f"正文需为{minimum}–{maximum}个汉字（不含标题、分节标题和话题），当前{count}个。")
    if not checks["images"]["ok"]:
        issues.append(f"需{rules['image_min']}–{rules['image_max']}张可读取的同型号本地图片；提交{len(images)}张，实际排版{len(pictures)}张。")
    if not checks["sections"]["ok"]:
        issues.append(f"正文需1–{rules['sections']}个分节，当前{len(sections)}个。")
    if not checks["headings"]["ok"]:
        issues.append("请为每个正文分节补充短标题。")
    if not checks["tags"]["ok"]:
        issues.append("小红书需至少一个以 # 开头的话题。" if rules["tags"] else "此平台请移除话题标签。")
    if not checks["intro"]["ok"]:
        issues.append("请补充导语或海报副标题。")
    if not checks["cta"]["ok"]:
        issues.append("请补充到店、私信或评论引导。")
    checks["ready"], checks["issues"] = not issues, issues
    return checks


def _delivery_notes(platform: str, count: int, ready: bool) -> str:
    status = "格式检查已通过。" if ready else "当前为排版草稿，请先按格式检查提示修改。"
    instructions = {
        "小红书": "复制发布文案，在小红书创作页按 images/01.jpg 起的编号顺序上传图片，核对封面、短段落和话题后发布。",
        "微信公众号": "在公众号后台新建图文，参照 HTML 的标题、导语、分节、图注与结尾引导排版。需先在公众号后台逐张上传 images/ 中的图片，再插入对应位置；本地 HTML 的 base64/Data URI 图片不能保证被后台保留，不能把此文件当作可直接导入或自动发布的接口。",
        "门店朋友圈": "复制短文到朋友圈，按 images/ 中的编号顺序选择配图，预览正文与图库后手动发布。",
        "门店海报": "参照 HTML 的主标题、副标题、短卖点和到店引导排版，使用 images/01.jpg 作为单一主视觉；HTML 是排版参考，可交给门店设计工具制作海报。",
    }
    return (f"{platform}发布说明\n\n{status}\n\n"
            "排版.html：离线可打开的自包含排版参考。\n"
            "发布文案.txt：已移除核验引用编号的可复制文案。\n"
            f"images/：{count}张按出现顺序编号的 JPG 配图，已重新编码并去除源文件元数据，保持原始比例。\n\n"
            + instructions.get(platform, "请先选择受支持的平台后重新生成。")
            + "\n\n本交付不连接发布账号，不上传素材，也不自动发布。发布前请核对具体款式、图片使用授权和当天销售政策。\n")


def export_delivery(units: list[dict], images: list[dict], task: dict, mode_label: str,
                    out_dir: Path, copy_text: str) -> dict:
    """Write HTML and a minimal publishing ZIP; return paths, clean copy and checks.

    ``copy_text`` is a fallback for callers with no publication units. Reviewed
    structured units otherwise determine both the HTML and the clean text. Audit
    sources, full quotations, task parameters and local paths are never bundled.
    """
    platform = str(task.get("platform", ""))
    clean = publish_units(units, platform)
    paragraphs = []
    for unit in clean:
        heading = unit.get("heading", "") if unit["id"].startswith("section_") else ""
        paragraphs.append((heading + "\n" if heading else "") + unit["text"])
    publish_copy = "\n\n".join(paragraphs) or clean_publish_text(copy_text)
    pictures = prepare_images(images, task)
    checks = _platform_checks(units, pictures, images, task)
    notes = _delivery_notes(platform, len(pictures), checks["ready"])
    title = next((unit["text"] for unit in clean if unit["id"] == "title"), platform + "图文排版")
    article = render_platform(clean, pictures, task, mode_label, audit=False)
    document = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{escape(title, quote=True)}</title></head>'
                '<body style="margin:0;padding:18px 10px;background:#f2f5f7">'
                + article + '</body></html>')
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "知衡-发布排版.html"
    bundle_path = out_dir / "知衡-平台图文素材.zip"
    html_path.write_text(document, encoding="utf-8")
    with ZipFile(bundle_path, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr("排版.html", document.encode("utf-8"))
        bundle.writestr("发布文案.txt", publish_copy.encode("utf-8"))
        bundle.writestr("平台使用说明.txt", notes.encode("utf-8"))
        for index, item in enumerate(pictures, 1):
            bundle.writestr(f"images/{index:02d}.jpg", item["jpeg"])
    return {"export_html": str(html_path), "export_bundle": str(bundle_path),
            "publish_copy": publish_copy, "delivery_notes": notes, "platform_checks": checks}
