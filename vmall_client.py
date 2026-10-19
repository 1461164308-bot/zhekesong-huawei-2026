"""Read explicit public VMall product pages; never search, log in or guess IDs."""
from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import re
import unicodedata
from urllib.parse import parse_qsl, urljoin, urlsplit
import tempfile
from pathlib import Path

import requests


class VmallError(Exception):
    """Display-safe public-page retrieval error."""


_MAX_BYTES = 2 * 1024 * 1024
_URL = re.compile(r"https?://[^\s<>\"'`\[\](){}（）【】，。；！？、]+", re.I)
_SKIP = {"script", "style", "nav", "footer", "header", "aside", "form", "button", "noscript", "template"}
_RECOMMEND = re.compile(r"recommend|related|sidebar|猜你喜欢|推荐|热销|导航", re.I)


def _validate_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname not in {"www.vmall.com", "vmall.com"}
                or parsed.username is not None or parsed.password is not None or parsed.port is not None
                or parsed.query or parsed.fragment or "\\" in url):
            raise ValueError
        if not re.fullmatch(r"/product/\d{1,30}\.html", parsed.path):
            raise VmallError("请提供华为商城具体商品页链接（https://www.vmall.com/product/数字.html），首页不能确认型号。")
        return "https://www.vmall.com" + parsed.path
    except ValueError:
        raise VmallError("商城链接须为无参数、无认证信息的 HTTPS 官方商品页；不接受相似域名或签名链接。") from None


class _Node:
    def __init__(self, tag="", attrs=(), parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []

    def text(self):
        ancestor = self
        while ancestor is not None:
            if ancestor.tag in _SKIP or _RECOMMEND.search(ancestor.attrs.get("id", "") + " " + ancestor.attrs.get("class", "")):
                return ""
            if "hidden" in ancestor.attrs or ancestor.attrs.get("aria-hidden") == "true" or re.search(r"display\s*:\s*none", ancestor.attrs.get("style", ""), re.I):
                return ""
            ancestor = ancestor.parent
        return " ".join(child.text() if isinstance(child, _Node) else child for child in self.children).strip()

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, _Node):
                yield from child.walk()


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node()
        self.current = self.root
        self.jsonld = []
        self.script = None

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in {"meta", "link", "img", "br", "hr", "input", "source", "area", "wbr"}:
            self.current = node
        if tag == "script" and node.attrs.get("type", "").lower() == "application/ld+json":
            self.script = node

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "script" and self.script is not None:
            self.jsonld.append("".join(x for x in self.script.children if isinstance(x, str)))
            self.script = None
        node = self.current
        while node is not self.root:
            if node.tag == tag:
                self.current = node.parent
                return
            node = node.parent

    def handle_data(self, data):
        self.current.children.append(data)


def _plain(value) -> str:
    if not isinstance(value, (str, int, float)):
        return ""
    parser = _Page()
    parser.feed(str(value))
    return re.sub(r"\s+", " ", parser.root.text()).strip()


def _normal(value: str) -> str:
    return re.sub(r"[\s()（）_·-]", "", unicodedata.normalize("NFKC", value).casefold()).replace("huawei", "").replace("华为", "")


def _identity(product: str, title: str, model: str = "") -> bool:
    requested, actual = _normal(product), _normal(title + " " + model)
    # Ecosystem models (phone/tablet/wearable) and multi-device combos are matched
    # by requiring every requested device token to appear in the page identity.
    if not re.search(r"matebook|擎云", requested, re.I):
        parts = [part for part in re.split(r"[+＋、/,，]|套装|组合|生态", requested) if part.strip()]
        return bool(parts) and all(part in actual for part in parts)
    core = re.compile(r"matebook(?:xpro|gt14|d16se版?|d16|d14|pros|pro|fold|14|16)")
    want, found = core.search(requested), list(core.finditer(actual))
    if not want or not found or any(match.group() != want.group() for match in found):
        return False
    # A generic title is insufficient for a year, edition or operating-system SKU.
    if not re.search(re.escape(requested) + r"(?![a-z])", actual):
        return False
    wanted_years, actual_years = set(re.findall(r"20\d{2}", requested)), set(re.findall(r"20\d{2}", actual))
    if wanted_years != actual_years:
        return False
    def system(text):
        systems = set()
        if "鸿蒙" in text or "harmonyos" in text:
            systems.add("harmony")
        if "windows" in text:
            systems.add("windows")
        return systems
    wanted_system, actual_system = system(requested), system(actual)
    return len(actual_system) <= 1 and wanted_system == actual_system


def _products(value):
    """Walk only top-level/graph/mainEntity products, never recommendation lists."""
    values = value if isinstance(value, list) else [value]
    for obj in values:
        if not isinstance(obj, dict):
            continue
        types = obj.get("@type", [])
        if "Product" in ([types] if isinstance(types, str) else types):
            yield obj
        for key in ("@graph", "mainEntity"):
            if key in obj:
                yield from _products(obj[key])


def _extract(page: str, product: str, url: str) -> tuple[str, str, list[str]]:
    parser = _Page()
    try:
        parser.feed(page)
    except (ValueError, RecursionError):
        raise VmallError("商城页面结构无法可靠解析，请在浏览器核对具体商品。") from None
    structured = []
    for raw in parser.jsonld:
        try:
            structured.extend(_products(json.loads(raw)))
        except (ValueError, TypeError, RecursionError):
            continue
    if structured:
        linked = []
        for item in structured:
            try:
                if item.get("url") and _validate_url(urljoin(url, str(item["url"]))) == url:
                    linked.append(item)
            except VmallError:
                continue
        candidates = linked if linked else structured if len(structured) == 1 and not structured[0].get("url") else []
        if len(candidates) != 1:
            raise VmallError("商城页面包含多个商品，无法确认当前商品身份；未使用推荐商品资料。")
        item = candidates[0]
        title, model = _plain(item.get("name", "")), _plain(item.get("model", ""))
        main_titles = [node.text() for scope in parser.root.walk() if scope.tag == "main"
                       for node in scope.walk() if node.tag == "h1" and node.text()]
        if any(not _identity(product, heading) for heading in main_titles):
            raise VmallError("商城主标题与结构化商品身份冲突，未使用推荐商品资料。")
        if not _identity(product, title, model):
            raise VmallError("商城当前商品的型号、年份、系统或款式与所选型号不完全一致，已停止补充。")
        details = [_plain(item.get("description", ""))]
        properties = item.get("additionalProperty", [])
        if isinstance(properties, dict):
            properties = [properties]
        for prop in properties if isinstance(properties, list) else []:
            if isinstance(prop, dict):
                details.append(_plain(prop.get("name", "")) + "：" + _plain(prop.get("value", "")))
    else:
        scopes = [node for node in parser.root.walk() if node.tag == "main" or "schema.org/Product" in node.attrs.get("itemtype", "")]
        if len(scopes) != 1:
            raise VmallError("商城页面未提供可核验的主商品结构，可能仅有 JavaScript 页面；请提供可读取的具体商品页。")
        scope = scopes[0]
        headings = [node for node in scope.walk() if node.tag == "h1" and node.text()]
        if len(headings) != 1 or not _identity(product, headings[0].text()):
            raise VmallError("商城主商品标题无法确认所选精确型号；推荐区或全页提及不能作为商品身份依据。")
        title = headings[0].text()
        details = [node.text() for node in scope.walk() if node.tag in {"p", "dl", "table"} and node.text()]
    details = list(dict.fromkeys(text for text in details if text))
    if len("".join(details)) < 20:
        raise VmallError("商城商品详情不可读取或内容不足，未用标题、搜索摘要或模型常识补造事实。")
    return title[:300], (title + "\n" + "\n".join(details))[:26000], _image_urls(parser, structured)


_IMG_HOSTS = ("vmall.com", "alicdn.com", "huawei.com", "dbankcdn.com")
_MAX_IMAGE = 4 * 1024 * 1024


def _image_url(value) -> str:
    if not isinstance(value, str) or not value.startswith("https://"):
        return ""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return ""
    host = parsed.hostname or ""
    if parsed.username or parsed.password:
        return ""
    if not any(host == name or host.endswith("." + name) for name in _IMG_HOSTS):
        return ""
    if any(re.search(r"sign|token|secret|credential", key, re.I) for key, _ in parse_qsl(parsed.query)):
        return ""
    return value


def _image_urls(parser: _Page, structured: list) -> list[str]:
    found: list[str] = []
    for item in structured:
        raw = item.get("image") if isinstance(item, dict) else None
        values = raw if isinstance(raw, list) else [raw]
        for value in values:
            if isinstance(value, dict):
                value = value.get("url") or value.get("contentUrl")
            found.append(value if isinstance(value, str) else "")
    for node in parser.root.walk():
        if node.tag == "meta":
            prop = (node.attrs.get("property") or node.attrs.get("name") or "").lower()
            if prop in {"og:image", "og:image:secure_url", "twitter:image"}:
                found.append(node.attrs.get("content", ""))
        elif node.tag == "img":
            found.append(node.attrs.get("src") or node.attrs.get("data-src") or "")
    seen, urls = set(), []
    for value in (x for x in (_image_url(v) for v in found) if x):
        if value not in seen:
            seen.add(value)
            urls.append(value)
    return urls


def _download_image(session, url: str, timeout: float) -> bytes:
    try:
        response = session.get(url, timeout=(min(6, timeout), timeout), allow_redirects=False, stream=True,
                               headers={"Accept": "image/*", "User-Agent": "ZhiHeng-PublicSource/1.0"})
        with response:
            if response.status_code != 200:
                raise VmallError("商城图片暂时无法读取。")
            if "image" not in response.headers.get("Content-Type", "").lower():
                raise VmallError("商城返回的不是图片内容。")
            data = bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data) > _MAX_IMAGE:
                    raise VmallError("商城图片超过读取上限。")
            if not data:
                raise VmallError("商城图片为空。")
            return bytes(data)
    except requests.RequestException:
        raise VmallError("商城图片下载失败。") from None


def _download(session, url: str, timeout: float) -> tuple[str, str]:
    for attempt in range(3):
        try:
            response = session.get(url, timeout=(min(6, timeout), timeout), allow_redirects=False, stream=True,
                                   headers={"Accept": "text/html,application/xhtml+xml", "User-Agent": "ZhiHeng-PublicSource/1.0"})
            with response:
                if response.status_code in (301, 302, 303, 307, 308):
                    target = _validate_url(urljoin(url, response.headers.get("Location", "")))
                    if target == url or attempt == 2:
                        raise VmallError("商城商品页重定向无法确认，已停止读取；请提供最终官方商品链接。")
                    url = target
                    continue
                if response.status_code != 200:
                    raise VmallError("商城商品页当前不可公开读取（HTTP 状态异常），请在浏览器核对；未绕过访问限制。")
                if response.url and _validate_url(response.url) != url:
                    raise VmallError("商城返回的页面地址与请求不一致，已停止读取。")
                content_type = response.headers.get("Content-Type", "").lower()
                if not any(kind in content_type for kind in ("text/html", "application/xhtml+xml")):
                    raise VmallError("商城返回的内容不是可核验的 HTML 商品页。")
                length = response.headers.get("Content-Length", "")
                if length.isdigit() and int(length) > _MAX_BYTES:
                    raise VmallError("商城页面超过读取大小上限，已停止。")
                data = bytearray()
                for chunk in response.iter_content(65536):
                    data.extend(chunk)
                    if len(data) > _MAX_BYTES:
                        raise VmallError("商城页面超过读取大小上限，已停止。")
                return bytes(data).decode("utf-8-sig", errors="replace"), url
        except requests.RequestException:
            raise VmallError("商城商品页连接失败或超时，请在浏览器确认可访问性；本次未取得商城依据。") from None
    raise VmallError("商城重定向次数超过上限，未取得依据。")


def _product_urls(text: str, limit: int) -> list[str]:
    urls = []
    for match in _URL.finditer(str(text or "")):
        raw = match.group().rstrip(".,;:!?")
        if "vmall" not in raw.casefold():
            continue
        canonical = _validate_url(raw)
        if canonical not in urls:
            urls.append(canonical)
    return urls[:limit]


def _save_image(raw: bytes, index: int) -> str:
    folder = Path(tempfile.mkdtemp(prefix="zhiheng-vmall-"))
    if raw[:3] == b"\xff\xd8\xff":
        suffix = ".jpg"
    elif raw[:8] == b"\x89PNG\r\n\x1a\n":
        suffix = ".png"
    else:
        suffix = ".webp"
    path = folder / f"vmall-{index:02d}{suffix}"
    path.write_bytes(raw)
    return str(path)


def fetch_vmall_assets(product: str, text: str, *, timeout=12, max_sources=3,
                       max_images=6) -> dict:
    """Read explicit official product pages, returning facts and product images.

    Only the pages the user pasted are read; nothing is searched for. Images are
    the page's own product media (JSON-LD/og:image/markup) and are tagged with the
    requested model so the agent can keep image provenance separate from the
    knowledge base.
    """
    limit = max(0, min(int(max_sources), 3))
    urls = _product_urls(text, limit)
    if not urls or not limit:
        return {"sources": [], "images": []}
    timeout = max(1.0, min(float(timeout), 30.0))
    want_images = max(0, min(int(max_images), 8))
    sources, images = [], []
    with requests.Session() as session:
        session.trust_env = False
        session.auth = None
        for url in urls:
            session.cookies.clear()
            content, final_url = _download(session, url, timeout)
            title, body, image_urls = _extract(content, str(product), final_url)
            sources.append({"title": title, "text": body, "kind": "facts", "official_url": final_url,
                            "retrieved_at": datetime.now(timezone.utc).isoformat(), "origin": "official_vmall"})
            for image_url in image_urls:
                if len(images) >= want_images:
                    break
                try:
                    raw = _download_image(session, image_url, timeout)
                    path = _save_image(raw, len(images) + 1)
                except (VmallError, OSError):
                    continue
                images.append({"title": title, "caption": "官方商城商品图，画面内容未逐像素核验。",
                               "model": str(product), "path": path, "url": image_url,
                               "source_title": title, "origin": "official_vmall",
                               "retrieved_at": datetime.now(timezone.utc).isoformat()})
    return {"sources": sources, "images": images}


def fetch_vmall_sources(product: str, text: str, *, timeout=12, max_sources=2) -> list[dict]:
    """Fetch only explicit canonical product URLs in user requirements/revisions."""
    limit = max(0, min(int(max_sources), 2))
    if not limit or not _product_urls(text, limit):
        return []
    timeout = max(1.0, min(float(timeout), 30.0))
    sources = []
    # A fresh isolated session neither reads netrc/proxy credentials nor reuses app
    # auth/cookies. Requests are fixed to validated public hosts and manual redirects.
    with requests.Session() as session:
        session.trust_env = False
        session.auth = None
        for url in _product_urls(text, limit):
            session.cookies.clear()
            content, final_url = _download(session, url, timeout)
            title, body, _ = _extract(content, str(product), final_url)
            sources.append({"title": title, "text": body, "kind": "facts", "official_url": final_url,
                            "retrieved_at": datetime.now(timezone.utc).isoformat(), "origin": "official_vmall"})
    return sources
