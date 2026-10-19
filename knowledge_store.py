"""Read private configured archives or the fixed user-authorized workspace P1.

Local: IMA_ARCHIVE_PATH. Remote: IMA_ARCHIVE_URL, IMA_ARCHIVE_TOKEN and
IMA_ARCHIVE_SHA256. Automatic workspace snapshots are ignored local caches;
explicit source settings always take precedence. No uploads or config changes.
Configured archive failures return None without exposing request details.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
import re
import tempfile
import threading
import time
import unicodedata
from urllib.parse import urljoin, urlsplit
import zipfile

import requests

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_REDIRECTS = 5
MAX_DOWNLOAD_SECONDS = 150
_AUTH_HOSTS = frozenset({"modelscope.cn", "www.modelscope.cn", "api.modelscope.cn"})
# Official ModelScope storage endpoints; no arbitrary aliyuncs.com destinations.
_STORAGE_HOSTS = frozenset({
    "modelscope.oss-cn-beijing.aliyuncs.com",
    "modelscope.oss-cn-hangzhou.aliyuncs.com",
    "modelscope.oss-cn-shanghai.aliyuncs.com",
    "modelhub-cn-beijing.oss-cn-beijing.aliyuncs.com",
    "modelhub-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com",
    "modelhub-cn-shanghai.oss-cn-shanghai.aliyuncs.com",
})
_LOCK = threading.Lock()
WORKSPACE_ROOT = Path(__file__).resolve().parent
WORKSPACE_SOURCE = Path("任德耀新建华为PC知识库") / "华为PC全板块深度知识库_v7"
# Ordered: the authorized PC library wins any model-name collision, then the
# generated official product database widens coverage to phones, tablets,
# wearables and the rest of the consumer catalogue.
WORKSPACE_SOURCES = (
    WORKSPACE_SOURCE,
    Path("华为官方产品库_v1"),
)
_PRODUCT_KEY = re.compile(r"[\s_\-·（）()]+")


def _product_key(name: str) -> str:
    """Compare model folder names across sources without inventing aliases."""
    value = unicodedata.normalize("NFKC", name).casefold()
    value = re.sub(r"^(?:huawei|华为)\s*", "", value)
    return _PRODUCT_KEY.sub("", value)


def _authorized_sources() -> list[Path]:
    """Every configured workspace source that currently exists, in priority order."""
    sources = []
    for relative in WORKSPACE_SOURCES:
        source = WORKSPACE_ROOT / relative
        if source.exists():
            sources.append(source)
    return sources


def get_workspace_archive() -> str | None:
    """Snapshot only authorized P1 material, never the repository or secret files.

    Several workspace sources are merged into one P1 tree; a model folder that
    appears in more than one source is taken from the first source only, so the
    catalogue never contains two entries for the same model. Content-addressed
    snapshots preserve freshness across restarts and refreshes. The local
    uncompressed limits match IMAClient.load_archive, independently of the
    stricter remote download limit. No network or credential access occurs.
    """
    sources = _authorized_sources()
    if not sources:
        return None
    from ima_client import IMAError
    try:
        digest = hashlib.sha256()
        files = []
        total = 0
        seen = 0
        seen_products: set[str] = set()
        seen_paths: set[str] = set()
        excluded = re.compile(r"secret|credential|token|api.?key|password|private|内部|机密|待审核|历史归档", re.I)
        for source in sources:
            primary = source / "P1-产品参数库"
            for path in (source.parent, source, primary):
                if path.is_symlink() or (path.exists() and getattr(path.lstat(), "st_file_attributes", 0) & 0x400):
                    raise ValueError("linked source")
            if not primary.is_dir():
                raise ValueError("missing P1")
            for folder, dirs, names in os.walk(primary, followlinks=False):
                depth = len(Path(folder).relative_to(primary).parts)
                seen += len(dirs) + len(names)
                if seen > 12000:
                    raise ValueError("local entry limit")
                for name in dirs + names:
                    path = Path(folder) / name
                    if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
                        raise ValueError("linked entry")
                    if any(x in name for x in (":", "\\", "\0")) or name in {".", ".."}:
                        raise ValueError("unsafe path")
                keep = []
                for name in sorted(dirs):
                    if name.startswith(".") or excluded.search(name):
                        continue
                    if depth == 1:  # model folders: one entry per model across all sources
                        key = _product_key(name)
                        if key in seen_products:
                            continue
                        seen_products.add(key)
                    keep.append(name)
                dirs[:] = keep
                for name in sorted(names):
                    path = Path(folder) / name
                    if name.startswith(".") or excluded.search(name):
                        continue
                    if path.suffix.lower() not in {".md", ".txt", ".csv", ".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                        continue
                    size = path.stat().st_size
                    if not path.is_file() or size > 25 * 1024 * 1024 or total + size > 512 * 1024 * 1024:
                        raise ValueError("local size limit")
                    with path.open("rb") as stream:
                        content = stream.read(25 * 1024 * 1024 + 1)
                    relative = path.relative_to(source).as_posix()
                    if relative in seen_paths:
                        continue
                    seen_paths.add(relative)
                    total += len(content)
                    if len(content) > 25 * 1024 * 1024 or total > 512 * 1024 * 1024 or len(files) >= 12000:
                        raise ValueError("local limit")
                    files.append((relative, content))
        for name, content in sorted(files):
            digest.update(name.encode() + b"\0" + hashlib.sha256(content).digest())
        if not files:
            raise ValueError("empty P1")
        root = WORKSPACE_ROOT / ".local" / "knowledge-cache"
        for path in (root.parent, root):
            if path.is_symlink() or (path.exists() and getattr(path.lstat(), "st_file_attributes", 0) & 0x400):
                raise ValueError("linked cache")
        root.mkdir(parents=True, exist_ok=True)
        target = root / (digest.hexdigest() + ".zip")
        with _LOCK:
            if target.is_symlink() or (target.exists() and getattr(target.lstat(), "st_file_attributes", 0) & 0x400):
                raise ValueError("linked cache file")
            valid = False
            if target.is_file() and target.stat().st_size <= 512 * 1024 * 1024:
                try:
                    with zipfile.ZipFile(target) as bundle:
                        valid = (len(bundle.infolist()) == len(files)
                                 and {i.filename for i in bundle.infolist()} == {n for n, _ in files}
                                 and all(bundle.getinfo(n).file_size == len(c)
                                         and hashlib.sha256(bundle.read(n)).digest() == hashlib.sha256(c).digest()
                                         for n, c in files))
                except (OSError, ValueError, RuntimeError, zipfile.BadZipFile):
                    valid = False
            if not valid:
                with tempfile.NamedTemporaryFile(dir=root, suffix=".part", delete=False) as stream:
                    partial = Path(stream.name)
                try:
                    with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                        for name, content in sorted(files):
                            bundle.writestr(name, content)
                    os.replace(partial, target)
                finally:
                    partial.unlink(missing_ok=True)
        return str(target)
    except (OSError, ValueError):
        raise IMAError("工作区授权知识库无效：请检查 P1 结构、文件安全性与大小上限；未回退联网 ima。") from None


def _validated_url(url: str, *, initial: bool = False) -> str:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443) or parsed.fragment or not host):
        raise ValueError("Archive URL is not permitted")
    is_modelscope = host in _AUTH_HOSTS or host.endswith(".modelscope.cn")
    if initial and host not in _AUTH_HOSTS:
        raise ValueError("Archive origin is not permitted")
    if not is_modelscope and host not in _STORAGE_HOSTS:
        raise ValueError("Archive redirect is not permitted")
    if initial and not re.match(r"^/(?:api/v1/(?:models|datasets)/|(?:models|datasets)/)", parsed.path):
        raise ValueError("Archive resource path is not permitted")
    return host


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            if size > MAX_ARCHIVE_BYTES:
                raise ValueError("Archive size exceeds the limit")
            digest.update(chunk)
    return digest.hexdigest()


def _checked_archive(path: Path, expected: str = "") -> bool:
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_ARCHIVE_BYTES:
        return False
    if expected and not hmac.compare_digest(_sha256(path), expected):
        return False
    return zipfile.is_zipfile(path)


def _download(url: str, token: str, expected: str, target: Path) -> None:
    """Follow only trusted HTTPS redirects, rebuilding headers for each hop."""
    started = time.monotonic()
    partial: Path | None = None
    try:
        with requests.Session() as session:
            # Ignore netrc credentials and ambient authentication/proxy settings.
            session.trust_env = False
            for hop in range(MAX_REDIRECTS + 1):
                host = _validated_url(url, initial=(hop == 0))
                session.cookies.clear()
                headers = {"User-Agent": "ZhiHeng-PrivateArchive/1.0", "Accept-Encoding": "identity"}
                if host in _AUTH_HOSTS:
                    headers["Authorization"] = "Bearer " + token
                    # The legacy private dataset route requires ModelScope's token cookie.
                    headers["Cookie"] = "m_session_id=" + token
                # Never forward credentials to OSS or a redirected CDN host.
                with session.get(url, headers=headers, stream=True, allow_redirects=False, timeout=(10, 30)) as response:
                    if time.monotonic() - started > MAX_DOWNLOAD_SECONDS:
                        raise ValueError("Archive download timed out")
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("Location", "")
                        if not location or hop == MAX_REDIRECTS:
                            raise ValueError("Archive redirect limit reached")
                        url = urljoin(url, location)
                        _validated_url(url)
                        continue
                    if response.status_code != 200:
                        raise ValueError("Archive service is unavailable")
                    length = response.headers.get("Content-Length")
                    if length and not 0 < int(length) <= MAX_ARCHIVE_BYTES:
                        raise ValueError("Archive size exceeds the limit")
                    digest = hashlib.sha256()
                    size = 0
                    with tempfile.NamedTemporaryFile(prefix="download-", suffix=".part", dir=target.parent, delete=False) as stream:
                        partial = Path(stream.name)
                        try:
                            os.chmod(partial, 0o600)
                        except OSError:
                            pass
                        for chunk in response.iter_content(chunk_size=256 * 1024):
                            if not chunk:
                                continue
                            size += len(chunk)
                            if size > MAX_ARCHIVE_BYTES or time.monotonic() - started > MAX_DOWNLOAD_SECONDS:
                                raise ValueError("Archive download limit reached")
                            digest.update(chunk)
                            stream.write(chunk)
                    if not size or not hmac.compare_digest(digest.hexdigest(), expected):
                        raise ValueError("Archive integrity verification failed")
                    if not zipfile.is_zipfile(partial):
                        raise ValueError("Archive format is invalid")
                    os.replace(partial, target)
                    partial = None
                    return
            raise ValueError("Archive redirect limit reached")
    finally:
        if partial is not None:
            try:
                partial.unlink(missing_ok=True)
            except OSError:
                pass


def get_archive_path() -> str | None:
    """Return the validated ZIP path, or None; never expose secrets in errors.

    The remote SHA256 is mandatory and pins the exact approved archive. A local
    archive may omit SHA256; if supplied, the same digest is enforced locally.
    Cached files are hashed again before use. Imports perform no network calls.
    """
    try:
        expected = os.environ.get("IMA_ARCHIVE_SHA256", "").strip().lower()
        if expected and not re.fullmatch(r"[0-9a-f]{64}", expected):
            return None
        local = os.environ.get("IMA_ARCHIVE_PATH", "").strip()
        if local:
            path = Path(local).expanduser().resolve()
            return str(path) if _checked_archive(path, expected) else None
        url = os.environ.get("IMA_ARCHIVE_URL", "").strip()
        token = os.environ.get("IMA_ARCHIVE_TOKEN", "").strip()
        if not url or not token or not expected or "\r" in token or "\n" in token:
            return None
        _validated_url(url, initial=True)
        with _LOCK:
            root = Path(tempfile.gettempdir()) / "zhiheng-private-archive"
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            if root.is_symlink():
                return None
            target = root / (expected + ".zip")
            if target.is_symlink():
                return None
            if _checked_archive(target, expected):
                return str(target.resolve())
            _download(url, token, expected, target)
            return str(target.resolve()) if _checked_archive(target, expected) else None
    except Exception:
        # Deliberately omit remote error bodies, signed URLs, headers and tokens.
        return None
