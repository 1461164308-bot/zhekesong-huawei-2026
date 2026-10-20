"""Build the official Huawei consumer product database from consumer.huawei.com.

Sources are the official product page and specification page for each model, both
public and server-rendered. Nothing is guessed: a model is only written when its
own /specs/ page exists in the official sitemap, and every file records its URL
and fetch date. Prices, promotions and stock are deliberately not collected.

Usage:
    python tools/build_product_db.py --categories phones,tablets --limit 2
    python tools/build_product_db.py --out 华为官方产品库_v1
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import re
import sys
import time

import requests

ROOT = Path(__file__).resolve().parents[1]
SITEMAP = "https://consumer.huawei.com/cn/sitemap.xml"
BASE = "https://consumer.huawei.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "zh-CN,zh;q=0.9"}

# Official category slug -> (folder number, Chinese name). Only main consumer products;
# cables, chargers and services are excluded because they carry no marketing narrative.
CATEGORIES = {
    "phones": ("01-手机", "手机"),
    "tablets": ("02-平板", "平板"),
    "harmonyos-computer": ("03-鸿蒙电脑", "鸿蒙电脑"),
    "laptops": ("04-笔记本", "笔记本"),
    "monitors": ("05-显示器", "显示器"),
    "wearables": ("06-穿戴", "穿戴"),
    "headphones": ("07-耳机", "耳机"),
    "speakers": ("08-音箱", "音箱"),
    "audio": ("09-智能眼镜", "智能眼镜"),
    "visions": ("10-智慧屏", "智慧屏"),
    "routers": ("11-路由与网络", "路由与网络"),
    "smart-lock": ("12-智能门锁", "智能门锁"),
    "wholehome": ("13-全屋智能", "全屋智能"),
    "printers": ("14-打印机", "打印机"),
    "storage": ("15-存储", "存储"),
}

_SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}
_IMG_OK = re.compile(r"\.(?:jpg|jpeg|png|webp)(?:\?|$)", re.I)
_IMG_SKIP = re.compile(r"(?:^|[/_])(?:logo|icon|favicon|footer|sprite|placeholder|arrow|bg-|qr|weixin|weibo)", re.I)


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag="", attrs=(), parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []

    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())

    def text(self) -> str:
        if self.tag in _SKIP_TAGS:
            return ""
        parts = [child.text() if isinstance(child, Node) else child for child in self.children]
        return re.sub(r"\s+", " ", "".join(parts)).strip()

    def walk(self, tag=None):
        for child in self.children:
            if isinstance(child, Node):
                if tag is None or child.tag == tag:
                    yield child
                yield from child.walk(tag)

    def find_all(self, *, tag=None, klass=None):
        for node in self.walk(tag):
            if klass is None or klass in node.classes():
                yield node


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.current = self.root
        self.void = {"meta", "link", "img", "br", "hr", "input", "source", "area", "wbr", "base", "col", "embed", "param", "track"}

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in self.void:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)

    def handle_data(self, data):
        self.current.children.append(data)

    def handle_endtag(self, tag):
        node = self.current
        while node is not self.root:
            if node.tag == tag:
                self.current = node.parent
                return
            node = node.parent


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(UA)
    return s


def get(s: requests.Session, url: str, *, tries: int = 3) -> str:
    for attempt in range(tries):
        try:
            r = s.get(url, timeout=30)
            if r.status_code == 200:
                r.encoding = "utf-8"
                return r.text
            if r.status_code == 404:
                raise LookupError(f"404 {url}")
        except (requests.RequestException, LookupError):
            if attempt == tries - 1:
                raise
        time.sleep(1.5 * (attempt + 1))
    raise LookupError(url)


def discover(s: requests.Session, categories: list[str]) -> dict[str, list[str]]:
    """Return category -> product URLs, only where the official /specs/ page exists."""
    xml = get(s, SITEMAP)
    locs = set(re.findall(r"<loc>(.*?)</loc>", xml))
    found: dict[str, list[str]] = {}
    for slug in categories:
        pattern = re.compile(rf"^https://consumer\.huawei\.com/cn/{re.escape(slug)}/([a-z0-9\-]+)/$")
        urls = []
        for url in locs:
            m = pattern.match(url)
            if m and url + "specs/" in locs:
                urls.append(url)
        found[slug] = sorted(urls)
    return found


def _variant_fields(item: Node) -> list[tuple[str, list[str], list[str]]]:
    """Read the ``multi-watchGt`` layout: one block per version (42 mm, 46 mm …).

    Each version becomes a ``型号名：`` marker line, which the fact-card parser reads
    as the variant that the following labelled values belong to.
    """
    variants = [node for node in item.find_all(klass="multi-watchGt-item")]
    fields: list[tuple[str, list[str], list[str]]] = []
    for node in variants:
        title = next(node.find_all(klass="multi-watchGt-title"), None)
        variant = title.text() if title else ""
        if variant:
            fields.append(("", [variant + "："], []))
        groups = list(node.find_all(klass="multi-watchGt-list")) or [node]
        for group in groups:
            subtitle = next(group.find_all(klass="multi-watchGt-subtitle"), None)
            name = subtitle.text() if subtitle else ""
            values, notes = [], []
            for paragraph in group.find_all(tag="p"):
                text = paragraph.text()
                if not text:
                    continue
                decorated = any("subtext" in klass for klass in paragraph.classes())
                (notes if decorated else values).append(text)
            if values or notes:
                fields.append((name, values, notes))
    return fields


def _is_caveat(paragraph: Node, text: str) -> bool:
    """Footnotes must travel with the value they qualify, so they are never values."""
    return (text.startswith("*")
            or any("subtext" in klass for klass in paragraph.classes()))


def _merge_trailing_notes(fields: list[tuple[str, list[str], list[str]]]) -> list[tuple[str, list[str], list[str]]]:
    """Attach column-level footnotes to the last field that actually carries values."""
    merged: list[tuple[str, list[str], list[str]]] = []
    for name, values, notes in fields:
        if not values and notes and merged and merged[-1][1]:
            previous = merged[-1]
            merged[-1] = (previous[0], previous[1], previous[2] + notes)
        else:
            merged.append((name, values, notes))
    return merged


def parse_specs(html: str) -> list[tuple[str, list[tuple[str, list[str], list[str]]]]]:
    """Parse the specification accordion into sections of (field, values, qualifiers).

    Three layouts are in use and all three are read here, otherwise whole sections
    silently become empty: values directly under ``large-accordion__inner``, values
    wrapped per field in ``large-accordion__wrap`` (sizes and weights), and the
    ``multi-watchGt`` per-version blocks used by wearables.
    """
    tree = Tree()
    tree.feed(html)
    sections = []
    for item in tree.root.find_all(tag="li"):
        if "large-accordion__item" not in item.classes():
            continue
        title_node = next(item.find_all(klass="large-accordion__title"), None)
        section = title_node.text() if title_node else ""
        fields = _variant_fields(item)
        for inner in item.find_all(klass="large-accordion__inner"):
            units = list(inner.find_all(klass="large-accordion__wrap")) or [inner]
            for unit in units:
                subtitle = next(unit.find_all(klass="large-accordion-subtitle"), None)
                name = subtitle.text() if subtitle else ""
                values, notes = [], []
                for paragraph in unit.find_all(tag="p"):
                    text = paragraph.text()
                    if not text:
                        continue
                    (notes if _is_caveat(paragraph, text) else values).append(text)
                if values or notes:
                    fields.append((name, values, notes))
        fields = _merge_trailing_notes(fields)
        if fields:
            sections.append((section, fields))
    return sections


def parse_product(html: str) -> dict:
    tree = Tree()
    tree.feed(html)
    h1 = next(tree.root.find_all(tag="h1"), None)
    title = h1.text() if h1 else ""
    if not title:
        m = re.search(r"<title>(.*?)</title>", html, re.S)
        title = re.sub(r"\s*-\s*华为官网\s*$", "", m.group(1).strip()) if m else ""
    meta = re.search(r'<meta name="description" content="([^"]*)"', html, re.S)
    headings = []
    for h2 in tree.root.find_all(tag="h2"):
        text = re.sub(r"\s+", "", h2.text())
        if 2 <= len(text) <= 30 and text not in headings:
            headings.append(text)
    images, seen = [], set()
    for img in tree.root.find_all(tag="img"):
        src = img.attrs.get("data-src") or img.attrs.get("src") or ""
        if not src or src.startswith("//") or not _IMG_OK.search(src):
            continue
        if _IMG_SKIP.search(src):
            continue
        if src.startswith("/"):
            src = BASE + src
        if not src.startswith("https://consumer.huawei.com/") or src in seen:
            continue
        seen.add(src)
        images.append({"url": src, "alt": re.sub(r"\s+", " ", img.attrs.get("alt") or "").strip()})
    return {"title": title.strip(), "description": (meta.group(1).strip() if meta else ""),
            "highlights": headings[:8], "images": images}


def render_facts(name: str, product: dict, sections, page_url: str, spec_url: str, fetched: str) -> str:
    lines = [f"# {name} - 产品事实", "",
             "> 来源：华为官网公开产品页与规格页。抓取日期：" + fetched +
             "。配置可能因销售版本而异，生成内容时必须保留限定条件并以实际销售版本为准。", ""]
    if product["description"]:
        lines += ["## 官网定位", "", product["description"], ""]
    if product["highlights"]:
        lines += ["## 官方页面卖点标题", ""] + [f"- {h}" for h in product["highlights"]] + [""]
    lines += ["## 官方规格摘录", ""]
    for section, fields in sections:
        if section:
            lines += [f"## {section}", ""]
        for field, values, notes in fields:
            if field:
                lines += [field, ""]
            lines += values + [""]
            lines += [f"*{note.lstrip('*').strip()}" for note in notes] + ([""] if notes else [])
    lines += ["## 来源", "", f"- 产品页：{page_url}", f"- 规格页：{spec_url}", ""]
    return "\n".join(lines)


def safe_name(value: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "-", value).strip() or "未命名"


def download_image(s: requests.Session, url: str, target: Path, *, max_bytes: int = 1_500_000) -> bool:
    # The CDN occasionally stalls for tens of seconds; a short timeout keeps the run
    # moving and the model simply ends up with the images that did arrive.
    try:
        r = s.get(url, timeout=12, stream=True)
        if r.status_code != 200:
            return False
        chunks, size = [], 0
        for chunk in r.iter_content(65536):
            size += len(chunk)
            if size > max_bytes:
                return False
            chunks.append(chunk)
        data = b"".join(chunks)
        if len(data) < 8000:  # sprites, icons and error pages
            return False
        target.write_bytes(data)
        return True
    except requests.RequestException:
        return False


def write_readme(out: Path, fetched: str, report: dict) -> None:
    models = sum(report["categories"].values())
    lines = [
        "# 华为官方产品库 · 建库说明", "",
        f"- 抓取日期：{fetched}",
        f"- 收录型号：{models} 个，覆盖：{'、'.join(sorted(report['categories']))}",
        "- 逐型号资料来自华为官网（consumer.huawei.com）**产品页 + 规格页**，均为公开静态页面。",
        "- 每个型号目录包含：`产品事实.md`（定位、官方卖点标题、规格摘录）、`来源清单.csv`（URL 与抓取日期）、"
        "`images/`（官网产品图与场景图）与 `images/图片清单.csv`（文件名、官方图片说明、原图 URL）。", "",
        "## 使用边界", "",
        "- 只收事实与官方表达，**不收价格、补贴、库存、赠品**；这些内容不进入文案。",
        "- 规格中带 `*` 的限定说明必须与数值一起使用，例如“峰值亮度”需要注明测试条件。",
        "- 图片仅用于本项目内的营销稿配图，版权归华为；对外发布前按平台规则使用。",
        "- 本库为抓取快照，不代表实时在售状态；型号与配置以官网和门店实际销售版本为准。", "",
        "## 范围说明", "",
        "- 当前只保留手机、穿戴、电脑三类；其余已抓取的品类移到了同级目录 `_暂缓-非重点/`，"
        "不进入 P1，也不参与知识库快照。需要时把它们移回 `P1-产品参数库/` 即可。",
        "- 规格页存在三种排版（普通字段、`large-accordion__wrap` 包裹的尺寸重量、穿戴的按款式分块），"
        "抓取脚本都可解析；官方页面没有列出的字段（如部分手机的芯片型号）不会补写。", "",
        "## 与华为商城（vmall）的关系", "",
        "vmall 商品页由前端渲染（服务端不返回正文），直接抓取只能拿到空壳页面，"
        "且抓取行为需要尊重站点限制，因此本库不使用 vmall 页面作为事实来源。"
        "需要商城购买链接时，由运营人员按型号人工补充，不自动猜测商品编号。",
    ]
    (out / "00-建库说明.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(categories: list[str], out: Path, *, limit: int | None, images_per_model: int,
          delay: float, resume: bool, workers: int = 6, pages: int = 4,
          refresh: bool = False) -> dict:
    s = session()
    discovered = discover(s, categories)
    fetched = time.strftime("%Y-%m-%d")
    report = {"fetched_at": fetched, "categories": {}, "failures": [], "models": []}
    index_rows = [("分类", "产品名称", "产品页", "规格页", "规格章节数", "图片数", "抓取日期")]
    pending_images = []  # (image dir, target, url, alt)
    tasks = []
    for slug, urls in discovered.items():
        folder, label = CATEGORIES[slug]
        for url in (urls[:limit] if limit else urls):
            tasks.append((folder, label, url))
    print(f"discovered {len(tasks)} models in {len(categories)} categories", flush=True)
    started = time.time()

    def crawl(task):
        folder, label, url = task
        spec_url = url + "specs/"
        try:
            product = parse_product(get(s, url))
            sections = parse_specs(get(s, spec_url))
        except (LookupError, requests.RequestException) as exc:
            return task, None, str(exc)
        time.sleep(delay)
        return task, (product, sections), ""

    with ThreadPoolExecutor(max_workers=pages) as pool:
        crawled = list(pool.map(crawl, tasks))
    print(f"crawled {len(tasks)} models in {time.time() - started:.0f}s", flush=True)

    for task, result, failure in crawled:
        folder, label, url = task
        spec_url = url + "specs/"
        if result is None:
            report["failures"].append({"url": url, "reason": failure})
            continue
        product, sections = result
        name = product["title"] or url.rstrip("/").rsplit("/", 1)[-1]
        folder_path = out / "P1-产品参数库" / folder / safe_name(name)
        record = {"category": label, "name": name, "url": url, "spec_url": spec_url,
                  "sections": len(sections), "images": [], "dir": str(folder_path)}
        if refresh or not (resume and (folder_path / "产品事实.md").is_file()
                           and (folder_path / "产品事实.md").stat().st_size > 200):
            folder_path.mkdir(parents=True, exist_ok=True)
            (folder_path / "产品事实.md").write_text(
                render_facts(name, product, sections, url, spec_url, fetched), encoding="utf-8")
            with (folder_path / "来源清单.csv").open("w", encoding="utf-8-sig", newline="") as fh:
                fh.write("资料类型,标题,URL,来源机构,抓取日期\n")
                fh.write(f"产品页,{name},{url},华为官网,{fetched}\n")
                fh.write(f"规格页,{name} 规格参数,{spec_url},华为官网,{fetched}\n")
        image_dir = folder_path / "images"
        stem = re.sub(r"[^a-z0-9\-]+", "-", url.rstrip("/").rsplit("/", 1)[-1])
        for index, image in enumerate(product["images"][:images_per_model], start=1):
            ext = Path(re.sub(r"\?.*$", "", image["url"])).suffix.lower() or ".jpg"
            digest = hashlib.sha256(image["url"].encode()).hexdigest()[:8]
            target = image_dir / f"{stem}_{index:02d}_{digest}{ext}"
            record["images"].append({"target": str(target), "url": image["url"],
                                    "alt": image["alt"] or "官网产品图"})
            pending_images.append((image_dir, target, image["url"], image["alt"] or "官网产品图"))
        report["models"].append(record)
        report["categories"].setdefault(label, 0)
        report["categories"][label] += 1
    print(f"wrote {len(report['models'])} model folders; fetching {len(pending_images)} images",
          flush=True)

    # Images are the slow part (CDN can stall); fetch them concurrently and politely.
    def fetch(job):
        image_dir, target, url, _ = job
        if target.is_file() and target.stat().st_size >= 8000:
            return job, True  # already downloaded by an earlier run
        image_dir.mkdir(parents=True, exist_ok=True)
        return job, download_image(s, url, target)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for job, ok in pool.map(fetch, pending_images):
            if not ok:
                report["failures"].append({"url": job[2], "reason": "image"})

    for record in report["models"]:
        saved = [image for image in record["images"] if Path(image["target"]).is_file()]
        image_dir = Path(record["dir"]) / "images"
        if saved:
            with (image_dir / "图片清单.csv").open("w", encoding="utf-8-sig", newline="") as fh:
                for row in [("文件名", "说明", "来源URL")] + [
                        (Path(image["target"]).name, image["alt"], image["url"]) for image in saved]:
                    fh.write(",".join('"' + str(cell).replace('"', '""') + '"' for cell in row) + "\n")
        index_rows.append((record["category"], record["name"], record["url"], record["spec_url"],
                           str(record["sections"]), str(len(saved)), fetched))
        record.pop("images"), record.pop("dir")
    out.mkdir(parents=True, exist_ok=True)
    write_readme(out, fetched, report)
    with (out / "产品索引.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        for row in index_rows:
            fh.write(",".join('"' + str(cell).replace('"', '""') + '"' for cell in row) + "\n")
    (out / "抓取报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the official Huawei product database")
    parser.add_argument("--categories", default=",".join(CATEGORIES))
    parser.add_argument("--out", default=str(ROOT / "华为官方产品库_v1"))
    parser.add_argument("--limit", type=int, default=None, help="models per category, for a smoke run")
    parser.add_argument("--images", type=int, default=4, help="images per model")
    parser.add_argument("--delay", type=float, default=0.6, help="seconds between models")
    parser.add_argument("--resume", action="store_true", help="skip models that already have facts")
    parser.add_argument("--workers", type=int, default=6, help="parallel image downloads")
    parser.add_argument("--pages", type=int, default=4, help="parallel page crawlers")
    parser.add_argument("--refresh", action="store_true",
                        help="rewrite facts even when they exist (parser changes); images are reused")
    args = parser.parse_args(argv)
    categories = [c.strip() for c in args.categories.split(",") if c.strip() in CATEGORIES]
    unknown = [c.strip() for c in args.categories.split(",") if c.strip() and c.strip() not in CATEGORIES]
    if unknown:
        print("unknown categories:", unknown, file=sys.stderr)
        return 2
    report = build(categories, Path(args.out), limit=args.limit, images_per_model=args.images,
                   delay=args.delay, resume=args.resume, workers=args.workers, pages=args.pages,
                   refresh=args.refresh)
    total = sum(report["categories"].values())
    print(json.dumps({"models": total, "by_category": report["categories"],
                      "failures": len(report["failures"])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
