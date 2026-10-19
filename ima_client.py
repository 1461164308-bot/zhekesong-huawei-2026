"""Read-only IMA knowledge retrieval. Restricted assets stay in system temp storage."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time
import zipfile
import unicodedata
from datetime import datetime, timezone
from urllib.parse import parse_qsl, unquote, urlsplit

import requests


class IMAError(Exception):
    """A display-safe IMA failure; never contains credentials or resource URLs."""


_API = "https://ima.qq.com/openapi/wiki/v1/"
# The shared knowledge base name is deployment configuration, never a code default.
_DEFAULT_KB = ""
_URL_RE = re.compile(r"https?://[^\s<>\]\)\"']+", re.I)
_FORBIDDEN = re.compile(r"竞品|对比|历史归档|待审核|MacBook|ThinkPad|联想|惠普|戴尔", re.I)
_SIGNED = re.compile(r"sign|signature|token|credential|authorization|expires|secret|api.?key", re.I)
_MODEL = re.compile(
    r"(?:HUAWEI\s+)?MateBook\b|(?:华为)?擎云\s*[A-Za-z]\d"
    r"|^(?:HUAWEI|华为|畅享|nova\b|WATCH\b|FreeBuds|FreeArc|FreeClip|MatePad\b|智慧屏|Vision\b"
    r"|MateView\b|Smart\b|Sound\b|PixLab\b|Eyewear\b|Band\s*\d|手环|路由|Router\b|门锁)",
    re.I)
# P1 subfolders that index material instead of holding model folders.
_INDEX_CATEGORY = re.compile(r"型号检索卡|扩展产品目录|官方公开价格快照|全库横向索引")


def _normal(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value)).casefold()
    value = re.sub(r"^(?:huawei|华为)\s*", "", value)
    return re.sub(r"[\s_\-]+", "", value)


def _folder(entry: dict) -> bool:
    return str(entry.get("media_type")) == "99" or str(entry.get("media_id", "")).startswith("folder_") or bool(entry.get("folder_id"))


def _title_model(title: str) -> str:
    title = re.sub(r"^\d+[\-_.\s]+", "", title.strip())
    title = re.sub(r"\.(?:md|txt|csv)$", "", title, flags=re.I)
    if not _MODEL.search(title) or "系列" in title or len(title) > 85:
        return ""
    if re.match(r"MateBook\b", title, re.I):
        title = "HUAWEI " + title
    return title


def _is_cos(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme == "https" and bool(parsed.hostname) and parsed.hostname.endswith(".myqcloud.com") and not parsed.username and parsed.port in (None, 443)


def _public_url(url: str) -> str:
    try:
        p = urlsplit(url)
        host = p.hostname or ""
        official = any(host == domain or host.endswith("." + domain) for domain in ("huawei.com", "vmall.com", "huaweicloud.com"))
        if p.scheme != "https" or not official or p.username or p.port not in (None, 443):
            return ""
        if any(_SIGNED.search(key) for key, _ in parse_qsl(p.query, keep_blank_values=True)):
            return ""
        return url
    except ValueError:
        return ""


def _clean_text(text: str) -> str:
    return _URL_RE.sub(lambda m: m.group(0) if _public_url(m.group(0)) else "[资源地址已隐藏]", text)


class IMAClient:
    """Environment-authenticated IMA adapter with system-temp resource caches.

    Credentials: IMA_OPENAPI_CLIENTID, IMA_OPENAPI_APIKEY; optional IMA_KB_NAME.
    This class deliberately does not load private configuration files itself.
    """

    _asset_lock = threading.RLock()

    def __init__(self, *, timeout: float = 25, cache_ttl: float = 300,
                 client_id: str | None = None, api_key: str | None = None, kb_name: str | None = None):
        # Explicit values come from a user's per-session settings; otherwise use server env.
        self._client_id = (os.environ.get("IMA_OPENAPI_CLIENTID", "") if client_id is None else client_id).strip()
        self._api_key = (os.environ.get("IMA_OPENAPI_APIKEY", "") if api_key is None else api_key).strip()
        self.kb_name = (os.environ.get("IMA_KB_NAME", "") if kb_name is None else kb_name).strip()
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._kb = None
        self._kb_time = 0.0
        self._lists: dict[str, tuple[float, list[dict]]] = {}
        self._nodes: dict[str, dict] = {}
        self._products: list[str] = []
        self._catalog_time = 0.0
        self._primary: list[dict] = []
        self._cards: list[dict] = []
        self._p1 = ""
        self._cache_dir: Path | None = None
        identity = hashlib.sha256((self._client_id + "\n" + self.kb_name).encode()).hexdigest()[:24]
        self._persistent_cache = Path(tempfile.gettempdir()) / "ima-huawei-pc-cache" / identity
        self._quota_message = ""
        self._offline_archive = False
        self._archive_path: Path | None = None
        self._archive_members: dict[str, str] = {}
        self._archive_lists: dict[str, list[dict]] = {}

    def _quota(self) -> str:
        if self._quota_message:
            return self._quota_message
        try:
            saved = json.loads((self._persistent_cache / "quota.json").read_text(encoding="utf-8"))
            if saved.get("date") == datetime.now().astimezone().date().isoformat():
                self._quota_message = str(saved.get("message", "ima 今日资料获取额度已耗尽。"))
        except (OSError, ValueError, TypeError):
            pass
        return self._quota_message

    def _api(self, endpoint: str, body: dict) -> dict:
        if endpoint == "get_media_info" and self._quota():
            raise IMAError(self._quota_message)
        if not self._client_id or not self._api_key:
            raise IMAError("未配置 IMA_OPENAPI_CLIENTID / IMA_OPENAPI_APIKEY，无法连接 ima。")
        # No session-level auth: these headers must never follow a resource URL.
        headers = {"ima-openapi-clientid": self._client_id, "ima-openapi-apikey": self._api_key,
                   "ima-openapi-ctx": "skill_version=1.1.10", "Content-Type": "application/json"}
        try:
            response = requests.post(_API + endpoint, headers=headers, json=body,
                                     timeout=self.timeout, allow_redirects=False)
            if response.status_code != 200:
                raise IMAError(f"ima 接口 HTTP {response.status_code}，请稍后重试。")
            payload = response.json()
        except (requests.RequestException, ValueError):
            raise IMAError("ima 请求失败，请检查网络与服务状态。") from None
        if not isinstance(payload, dict):
            raise IMAError("ima 返回了无法识别的响应。")
        if payload.get("code") != 0:
            msg = _clean_text(str(payload.get("msg", "未知业务错误")))
            for secret in (self._client_id, self._api_key):
                msg = msg.replace(secret, "[已隐藏]")
            error = f"ima 接口失败：{msg[:240]}"
            if endpoint == "get_media_info" and ("次数已达上限" in msg or "quota" in msg.lower()):
                self._quota_message = error
                try:
                    self._persistent_cache.mkdir(parents=True, exist_ok=True)
                    (self._persistent_cache / "quota.json").write_text(json.dumps({"date": datetime.now().astimezone().date().isoformat(), "message": error}, ensure_ascii=False), encoding="utf-8")
                except OSError:
                    pass
            raise IMAError(error)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise IMAError("ima 响应缺少有效数据。")
        return data

    def _pages(self, endpoint: str, body: dict, key: str, max_pages: int = 40) -> list[dict]:
        result, cursor, seen = [], "", set()
        for _ in range(max_pages):
            data = self._api(endpoint, {**body, "cursor": cursor})
            items = data.get(key, [])
            if isinstance(items, list):
                result.extend(item for item in items if isinstance(item, dict))
            nxt = str(data.get("next_cursor") or "")
            if data.get("is_end") or not nxt:
                return result
            if nxt in seen:
                raise IMAError("ima 分页游标重复，已停止以避免遗漏或循环。")
            seen.add(nxt)
            cursor = nxt
        raise IMAError("ima 目录分页超过安全上限，请缩小检索范围。")

    def _resolve_kb(self) -> dict:
        if self._kb is not None and time.monotonic() - self._kb_time < self.cache_ttl:
            return self._kb
        if not self.kb_name:
            raise IMAError("未配置共享知识库名称：请由部署者设置服务端环境变量 IMA_KB_NAME。")
        items = self._pages("search_knowledge_base", {"query": self.kb_name, "limit": 20}, "info_list")
        matches = [x for x in items if (x.get("kb_name") or x.get("name")) == self.kb_name]
        if len(matches) != 1:
            raise IMAError(f"未唯一找到共享知识库「{self.kb_name}」，请确认名称和访问权限。")
        kb = dict(matches[0])
        kb["id"] = kb.get("kb_id") or kb.get("id")
        if not kb["id"]:
            raise IMAError("ima 知识库缺少访问标识。")
        self._kb, self._kb_time = kb, time.monotonic()
        return kb

    def connection_status(self) -> dict:
        role = "未连接"
        tail = self._client_id[-4:] if self._client_id else "未配置"
        status = {"connected": False, "kb_name": self.kb_name, "account_label": f"ClientID …{tail} · {role}",
                  "role": role, "content_count": 0, "message": "", "retrieval_mode": "live_ima", "offline_archive": False}
        if self._offline_archive:
            status["workspace_authorized"] = getattr(self, "_workspace_authorized", False)
            status.update(role="本地只读归档", content_count=len(self._archive_members),
                          account_label=f"ClientID …{tail} · 本地只读归档", retrieval_mode="offline_archive", offline_archive=True,
                          message="已加载获授权的本地 ZIP 归档；非 ima 实时资料，日期与版本以原文为准。")
            if status["workspace_authorized"]:
                status.update(kb_name="工作区授权知识库", account_label="工作区授权知识库 · 本地只读",
                              message="工作区授权知识库已加载 · 本地只读 · 非实时 ima；日期与版本以原文为准。")
            return status
        try:
            kb = self._resolve_kb()
            self._api("get_knowledge_base", {"ids": [kb["id"]]})
            role = str(kb.get("role_type") or kb.get("role") or "已授权成员")
            try:
                count = int(kb.get("content_count") or 0)
            except (TypeError, ValueError):
                count = 0
            status.update(connected=True, role=role, content_count=count,
                          account_label=f"ClientID …{tail} · {role}", message="已连接 ima 共享知识库（只读检索）。")
            if self._quota():
                status["message"] = self._quota_message + "；知识库连接仍正常，可显式使用获授权的缓存。"
        except IMAError as exc:
            status["message"] = str(exc)
        return status

    def _list(self, folder_id: str = "", path: tuple[str, ...] = ()) -> list[dict]:
        cached = self._lists.get(folder_id)
        if cached and time.monotonic() - cached[0] < self.cache_ttl:
            return cached[1]
        if self._offline_archive:
            items = self._archive_lists.get(folder_id, [])
            for entry in items:
                entry["_path"] = path + (entry["title"],)
                self._nodes[entry["media_id"]] = entry
            self._lists[folder_id] = (time.monotonic(), items)
            return items
        body = {"knowledge_base_id": self._resolve_kb()["id"], "limit": 50}
        if folder_id:
            body["folder_id"] = folder_id
        items = self._pages("get_knowledge_list", body, "knowledge_list")
        for entry in items:
            entry["media_id"] = entry.get("media_id") or entry.get("folder_id", "")
            entry["title"] = entry.get("title") or entry.get("name", "")
            entry["_path"] = path + (entry["title"],)
            self._nodes[entry["media_id"]] = entry
        self._lists[folder_id] = (time.monotonic(), items)
        return items

    def _children(self, entry: dict) -> list[dict]:
        return self._list(entry["media_id"], tuple(entry.get("_path", (entry["title"],))))

    def _discover(self) -> None:
        if self._products and time.monotonic() - self._catalog_time < self.cache_ttl:
            return
        self._primary, self._cards, self._products = [], [], []
        queue = [("", (), 0)]
        p1 = None
        while queue:
            folder_id, path, depth = queue.pop(0)
            for entry in self._list(folder_id, path):
                if _folder(entry) and re.match(r"P1\s*[-－]", entry["title"], re.I):
                    p1 = entry
                    break
                if _folder(entry) and depth < 2 and not re.match(r"P[2-9]", entry["title"], re.I) and not _FORBIDDEN.search(entry["title"]):
                    queue.append((entry["media_id"], entry["_path"], depth + 1))
            if p1:
                break
        if not p1:
            raise IMAError("未找到 P1 产品参数目录，停止型号枚举以防误用营销资料。")
        self._p1 = p1["media_id"]
        categories = [x for x in self._children(p1) if _folder(x)]
        names: list[str] = []
        for category in categories:
            title = category["title"]
            if not _INDEX_CATEGORY.search(title):
                for entry in self._children(category):
                    if _folder(entry) and _MODEL.search(entry["title"]):
                        self._primary.append(entry)
            if "扩展产品目录" in title:
                for group in self._children(category):
                    if _folder(group) and "消费级" in group["title"]:
                        for entry in self._children(group):
                            model = _title_model(entry["title"])
                            if model and not _folder(entry):
                                self._cards.append(entry)
                                entry["_product"] = model
                                names.append(model)
            if "型号检索卡" in title:
                self._cards.extend(x for x in self._children(category) if _folder(x) and _MODEL.search(x["title"]))
        for entry in self._primary:
            model = _title_model(entry["title"])
            if not model and "系列" in entry["title"]:
                family = _normal(entry["title"].replace("系列", ""))
                family_matches = [x for x in names if _normal(x).startswith(family)]
                if len(family_matches) == 1:
                    entry["_candidate_product"] = family_matches[0]
            if not model:
                continue
            path = "/".join(entry["_path"])
            candidates = [x for x in names if self._same_alias(x, model)
                          and not ("Windows" in path and ("鸿蒙" in x or "HarmonyOS" in x))
                          and not ("鸿蒙电脑" in path and "Windows" in x)]
            if len(candidates) == 1:
                entry["_product"] = candidates[0]
            elif not candidates:
                if "鸿蒙电脑" in "/".join(entry["_path"]) and "鸿蒙" not in model and "Fold" not in model and "Pro S" not in model:
                    model += "（鸿蒙版）"
                entry["_product"] = model
                names.append(model)
        if not names:
            raise IMAError("P1 中未枚举到可验证的精确产品型号。")
        self._products = list(dict.fromkeys(names))
        self._catalog_time = time.monotonic()

    @staticmethod
    def _same_alias(left: str, right: str) -> bool:
        left, right = _normal(left), _normal(right)
        years = [re.findall(r"20\d{2}", text) for text in (left, right)]
        if years[0] and years[1] and years[0] != years[1]:
            return False
        def operating_system(text):
            if "鸿蒙" in text or "harmonyos" in text:
                return "harmony"
            if "windows" in text:
                return "windows"
            return ""
        systems = [operating_system(text) for text in (left, right)]
        if all(systems) and systems[0] != systems[1]:
            return False
        def stripped(text):
            text = re.sub(r"\((?:鸿蒙版|harmonyos|windows(?:版)?)\)", "", text)
            return re.sub(r"20\d{2}$", "", text)
        return left == right or stripped(left) == stripped(right)

    def catalog(self) -> list[str]:
        self._discover()
        return list(self._products)

    def _canonical(self, value: str) -> str:
        matches = [x for x in self.catalog() if _normal(x) == _normal(value)]
        if not matches:
            matches = [x for x in self._products if self._same_alias(x, value)]
        if len(matches) != 1:
            raise IMAError("请选择知识库目录中的精确型号，不能使用泛称或跨型号检索。")
        return matches[0]

    def _download(self, info: dict, *, limit: int = 25 * 1024 * 1024) -> tuple[bytes, str]:
        resource = info.get("url_info") or {}
        url = resource.get("url", "")
        try:
            allowed = _is_cos(url)
        except (ValueError, TypeError):
            allowed = False
        if not allowed:
            raise IMAError("原文资源不在受信任的 ima 云存储端，请使用 ima 客户端查看。")
        headers = {str(k): str(v) for k, v in (resource.get("headers") or {}).items()
                   if str(k).lower() not in {"ima-openapi-clientid", "ima-openapi-apikey", "ima-openapi-ctx", "host", "cookie", "proxy-authorization"}
                   and not any(secret and secret in str(v) for secret in (self._client_id, self._api_key))}
        try:
            with requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=False, stream=True) as response:
                if response.status_code != 200:
                    raise IMAError(f"ima 原文下载失败（HTTP {response.status_code}），请重新检索。")
                chunks, size = [], 0
                for chunk in response.iter_content(chunk_size=65536):
                    size += len(chunk)
                    if size > limit:
                        raise IMAError("ima 资源超过安全下载上限。")
                    chunks.append(chunk)
                return b"".join(chunks), response.headers.get("Content-Type", "")
        except requests.RequestException:
            raise IMAError("ima 资源下载失败，请检查网络后重新检索。") from None

    def load_archive(self, path: str | os.PathLike) -> dict:
        """Switch this instance to an authorized local ZIP; never a live-error fallback."""
        archive = Path(path).expanduser().resolve()
        lists: dict[str, list[dict]] = {"": []}
        members, nodes = {}, set()
        try:
            with zipfile.ZipFile(archive) as bundle:
                files = bundle.infolist()
                if len(files) > 12000 or sum(x.file_size for x in files) > 512 * 1024 * 1024:
                    raise IMAError("归档超过安全大小或条目数上限。")
                for info in files:
                    name = info.filename.replace("\\", "/")
                    parts = name.rstrip("/").split("/")
                    if name.startswith("/") or any(x in ("", ".", "..") or ":" in x for x in parts):
                        raise IMAError("归档包含不安全路径，已拒绝。")
                    if info.file_size > 25 * 1024 * 1024:
                        raise IMAError("归档单文件超过安全读取上限。")
                    parent = ""
                    for index, title in enumerate(parts):
                        folder = index < len(parts) - 1 or info.is_dir()
                        relative = "/".join(parts[:index + 1])
                        media_id = "archive:" + hashlib.sha256(relative.encode()).hexdigest()
                        if media_id not in nodes:
                            ext = Path(title).suffix.lower()
                            kind = 99 if folder else 9 if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif") else 5 if ext == ".csv" else 7
                            lists.setdefault(parent, []).append({"media_id": media_id, "title": title, "parent_folder_id": parent, "media_type": kind})
                            nodes.add(media_id)
                        if folder:
                            lists.setdefault(media_id, [])
                        else:
                            if media_id in members:
                                raise IMAError("归档包含重复路径，已拒绝。")
                            members[media_id] = info.filename
                        parent = media_id
        except (OSError, zipfile.BadZipFile, RuntimeError):
            raise IMAError("无法读取本地 ZIP 归档，请确认文件格式和读取权限。") from None
        self._archive_path, self._archive_lists, self._archive_members = archive, lists, members
        self._offline_archive = True
        self._lists, self._nodes, self._products = {}, {}, []
        self._primary, self._cards = [], []
        self._catalog_time = 0.0
        models = self.catalog()
        return {"loaded": True, "product_count": len(models), "message": "已加载获授权本地归档；非实时 ima 检索。"}

    def _asset(self, entry: dict) -> tuple[bytes, dict]:
        if _folder(entry):
            raise IMAError("文件夹不能当作原文读取。")
        if self._offline_archive:
            try:
                with zipfile.ZipFile(self._archive_path) as bundle:
                    content = bundle.read(self._archive_members[entry["media_id"]])
                return content, {"media_type": entry.get("media_type"), "_content_type": "", "_origin": "offline_archive",
                                 "_retrieved_at": datetime.now(timezone.utc).isoformat()}
            except (OSError, KeyError, zipfile.BadZipFile, RuntimeError):
                raise IMAError("本地归档原文读取失败，未回退到不匹配的资料。") from None
        key = hashlib.sha256(entry["media_id"].encode()).hexdigest()
        data_path = self._persistent_cache / (key + ".bin")
        meta_path = self._persistent_cache / (key + ".json")
        with self._asset_lock:
            cached = None
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if data_path.stat().st_size <= 25 * 1024 * 1024:
                    content = data_path.read_bytes()
                    if hashlib.sha256(content).hexdigest() == meta.get("sha256"):
                        cached = (content, {**meta, "_origin": "ima_cache"})
                        if time.time() - data_path.stat().st_mtime < self.cache_ttl or self._quota():
                            return cached
            except (OSError, ValueError, TypeError):
                pass
            try:
                info = self._api("get_media_info", {"media_id": entry["media_id"]})
                if str(info.get("media_type")) == "11":
                    raise IMAError("该资料是 ima 笔记，请使用 ima 客户端查看。")
                content, content_type = self._download(info)
            except IMAError:
                if cached and self._quota():
                    return cached
                raise
            meta = {"media_type": info.get("media_type"), "_content_type": content_type,
                    "_retrieved_at": datetime.now(timezone.utc).isoformat(), "sha256": hashlib.sha256(content).hexdigest()}
            try:
                self._persistent_cache.mkdir(parents=True, exist_ok=True)
                data_path.write_bytes(content)
                meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass
            return content, {**meta, "_origin": "live_ima"}

    def _read_entry(self, entry: dict) -> tuple[str, dict]:
        content, info = self._asset(entry)
        content_type = info.get("_content_type", "")
        title = entry["title"].lower()
        if not title.endswith((".md", ".txt", ".csv", ".html", ".htm")) and not content_type.startswith("text/"):
            raise IMAError("该资料暂不支持可靠全文解析，请使用 ima 客户端查看。")
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise IMAError("资料文本不是 UTF-8，未将乱码当作事实。") from None
        return text, info

    def _mentioned(self, text: str) -> set[str]:
        # Official URL slugs can be shared across versions; they are not model assertions.
        text = _normal(_URL_RE.sub("", text))
        found = set()
        candidates = []
        for model in self._products:
            candidates.append((_normal(model), model))
            candidates.append((re.sub(r"\(鸿蒙版\)|2024$|2025$|2026$", "", _normal(model)), model))
        for alias, model in sorted(set(candidates), key=lambda x: len(x[0]), reverse=True):
            if alias and alias in text:
                found.add(model)
                text = text.replace(alias, " ")
        return found

    def _model_entries(self, product: str) -> list[dict]:
        for candidate in self._primary:
            if candidate.get("_candidate_product") != product or candidate.get("_product") == product:
                continue
            facts = next((x for x in self._children(candidate) if x["title"] == "产品事实.md"), None)
            if facts:
                try:
                    text, _ = self._read_entry(facts)
                    heading = text.splitlines()[0].lstrip("# ").removesuffix(" - 产品事实").strip()
                    if _normal(heading) == _normal(product):
                        candidate["_product"] = product
                except IMAError:
                    pass
        roots = [x for x in self._primary if x.get("_product") == product]
        roots += [x for x in self._cards if _folder(x) and self._same_alias(x["title"], product)]
        result = [x for x in self._cards if not _folder(x) and x.get("_product") == product]
        seen = set()
        queue = [(x, 0) for x in roots]
        while queue:
            root, depth = queue.pop(0)
            if root["media_id"] in seen:
                continue
            seen.add(root["media_id"])
            for entry in self._children(root):
                entry["_product"] = product
                if _folder(entry):
                    if depth < 3:
                        queue.append((entry, depth + 1))
                else:
                    result.append(entry)
        return list({x["media_id"]: x for x in result}.values())

    @staticmethod
    def _rank(entry: dict, query: str) -> tuple[int, str]:
        title = entry["title"]
        score = 100 if title == "产品事实.md" else 80 if "型号身份卡" in title else 65 if "卖点与限制" in title else 60
        if "扩展产品目录" in "/".join(entry.get("_path", ())):
            score = 10
        if "来源清单" in title or "图片索引" in title:
            score = -10
        score += sum(8 for word in re.split(r"\W+", query) if word and word in title)
        return -score, title

    def retrieve(self, product: str, query: str = "", max_sources: int = 5, max_images: int = 6) -> dict:
        product = self._canonical(product)
        max_sources, max_images = max(0, min(int(max_sources), 20)), max(0, min(int(max_images), 20))
        entries = self._model_entries(product)
        warnings, sources, images = [], [], []
        # Search is supplementary: the API is fuzzy, so only already verified model folders qualify.
        try:
            if self._offline_archive:
                found = []
            else:
                body = {"knowledge_base_id": self._resolve_kb()["id"], "query": product + (" " + query[:120] if query else "")}
                found = self._pages("search_knowledge", body, "info_list", max_pages=4)
            verified_parents = {x.get("parent_folder_id") for x in entries
                                if "扩展产品目录" not in "/".join(x.get("_path", ()))}
            known = {x["media_id"] for x in entries}
            for item in found:
                title_model = _title_model(item.get("title", ""))
                title_matches = title_model and _normal(title_model) == _normal(product)
                if not _folder(item) and item.get("parent_folder_id") in verified_parents and item.get("media_id") not in known:
                    if title_model and not title_matches:
                        continue
                    item["_product"] = product
                    entries.append(item)
                    known.add(item["media_id"])
        except IMAError:
            warnings.append("实时搜索未完成，已回退到已验证的 P1 型号目录浏览。")
        timestamp = datetime.now(timezone.utc).isoformat()
        image_meta, rejected_images = {}, set()
        for entry in entries:
            if "图片索引" not in entry["title"] or not entry["title"].lower().endswith(".csv"):
                continue
            try:
                text, _ = self._read_entry(entry)
                for row in csv.DictReader(io.StringIO(text)):
                    model = row.get("产品型号", "").strip()
                    filename = row.get("文件名", "").strip()
                    if model and not self._same_alias(model, product):
                        rejected_images.add(filename)
                        continue
                    image_meta[filename] = row
            except IMAError:
                warnings.append("图片索引读取失败，图注仅使用库内文件名，不推测画面。")
        text_entries = [x for x in entries if str(x.get("media_type")) != "9" and x["title"].lower().endswith((".md", ".txt", ".html", ".htm"))
                        and not _FORBIDDEN.search("/".join(x.get("_path", (x["title"],))))]
        for entry in sorted(text_entries, key=lambda x: self._rank(x, query)):
            if len(sources) >= max_sources:
                break
            try:
                text, source_info = self._read_entry(entry)
            except IMAError as exc:
                warnings.append(self._quota_message or f"{entry['title']}：{exc}")
                continue
            if entry["title"] == "产品事实.md":
                heading = text.splitlines()[0].lstrip("# ").removesuffix(" - 产品事实").strip() if text.splitlines() else ""
                if _MODEL.search(heading) and not self._same_alias(heading, product):
                    warnings.append(f"已排除标题型号或年份不符的事实资料：{entry['title']}。")
                    continue
            if re.search(r"\b(?:MacBook|ThinkPad|ThinkBook|Surface|Dell|HP)\b|联想|惠普|戴尔", text, re.I):
                warnings.append(f"已排除含竞品内容的资料：{entry['title']}。")
                continue
            mentioned = self._mentioned(text)
            if mentioned - {product}:
                warnings.append(f"已排除跨型号资料：{entry['title']}。")
                continue
            path = "/".join(entry.get("_path", ()))
            discovery = "扩展产品目录" in path or "发现卡" in text[:1000]
            kind = "marketing" if discovery or "卖点" in entry["title"] else "facts"
            if "价格" in path or "价格快照" in entry["title"]:
                kind = "price"
            if discovery:
                warnings.append(f"{entry['title']} 为发现卡，不可当作完整规格依据。")
            official = next((safe for match in _URL_RE.finditer(text) if (safe := _public_url(match.group(0)))), "")
            sources.append({"id": f"S{len(sources) + 1}", "title": product + " / " + entry["title"],
                            "media_id": entry["media_id"], "text": _clean_text(text), "official_url": official,
                            "kind": kind, "retrieved_at": source_info.get("_retrieved_at", timestamp),
                            "origin": source_info.get("_origin", "live_ima")})
        image_refs = {}
        for source in sources:
            for match in re.finditer(r"!\[([^\]]*)\]\(([^\s)]+)", source["text"]):
                basename = unquote(urlsplit(match.group(2)).path).replace("\\", "/").rsplit("/", 1)[-1]
                image_refs.setdefault(basename, {"source_id": source["id"], "source_title": source["title"], "caption": match.group(1)})
        image_entries = [x for x in entries if str(x.get("media_type")) == "9" or x["title"].lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))]
        for entry in image_entries:
            if len(images) >= max_images:
                break
            if entry["title"] in rejected_images:
                warnings.append(f"已排除图片索引型号不符的配图：{entry['title']}。")
                continue
            try:
                content, image_info = self._asset(entry)
                ext = self._image_extension(content)
                if not ext:
                    raise IMAError("图片签名不受支持，未返回可能损坏的文件。")
                if self._cache_dir is None:
                    self._cache_dir = Path(tempfile.mkdtemp(prefix="ima-huawei-pc-"))
                digest = hashlib.sha256(content).hexdigest()
                target = self._cache_dir / (digest + ext)
                target.write_bytes(content)
            except (IMAError, OSError) as exc:
                warnings.append(self._quota_message or (f"{entry['title']}：图片获取失败。" if isinstance(exc, OSError) else f"{entry['title']}：{exc}"))
                continue
            meta = image_meta.get(entry["title"], {})
            image_id = f"I{len(images) + 1}"
            ref = image_refs.get(entry["title"], {})
            caption = meta.get("官网图片说明") or ref.get("caption") or meta.get("建议用途") or entry["title"]
            images.append({"id": image_id, "title": entry["title"], "path": str(target),
                           "url": _public_url(meta.get("原始图片URL", "")), "source_title": ref.get("source_title") or product + " / images / " + entry["title"],
                           "source_id": ref.get("source_id") or image_id, "media_id": entry["media_id"], "model": product,
                           "caption": _clean_text(caption), "origin": image_info.get("_origin", "live_ima")})
        if not any(x["kind"] == "facts" for x in sources):
            warnings.append("未获得可核实的 P1 型号事实全文，不能补写处理器、屏幕、重量或续航参数。")
        if not images and max_images:
            warnings.append("未获取到该精确型号的 ima 配图，未使用其他型号图片兜底。")
        if any(x["kind"] == "price" for x in sources):
            warnings.append("价格资料为历史快照，不代表当前售价、补贴或优惠，请人工核实。")
        origins = {x.get("origin", "live_ima") for x in sources + images}
        mode = "offline_archive" if self._offline_archive else next(iter(origins)) if len(origins) == 1 else "mixed" if origins else "live_ima"
        if self._offline_archive:
            label = "工作区授权知识库（本地只读）" if getattr(self, "_workspace_authorized", False) else "获授权的主办方本地 ZIP 归档缓存"
            warnings.append(f"本次使用{label}，非实时 ima 获取；retrieved_at 是本地读取时间，资料快照日期与配置边界以原文为准。")
        if "ima_cache" in origins:
            warnings.append("部分资料来自系统临时 ima 缓存；retrieved_at 保留首次真实获取时间，并非本次实时更新。")
        if self._quota_message:
            warnings.append(self._quota_message)
        warnings.append("资料和图片来自共享知识库，仅用于获授权的赛题工作流；不可对外传播原始资料。")
        return {"product": product, "sources": sources, "images": images, "warnings": list(dict.fromkeys(warnings)),
                "retrieval_mode": mode, "offline_archive": self._offline_archive}

    @staticmethod
    def _image_extension(content: bytes) -> str:
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if content.startswith(b"\xff\xd8\xff"):
            return ".jpg"
        if content[:6] in (b"GIF87a", b"GIF89a"):
            return ".gif"
        if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return ".webp"
        return ""
