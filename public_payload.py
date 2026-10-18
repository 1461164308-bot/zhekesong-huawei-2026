"""Build public JSON-shaped payloads without mutating their source values.

This is a content sanitizer, not HTML escaping or a URL allowlist. Call it at
public output boundaries; image paths and ordinary source links are preserved.
No files, network services, or logging are used. Sensitive environment values
are snapshotted once per call so later configuration changes take effect.
"""
from __future__ import annotations

import html
import os
import re
from typing import Any
from urllib.parse import parse_qsl, urlsplit

__all__ = ["REDACTED", "sanitize_public"]

REDACTED = "[已隐藏]"
_ENV_NAMES = {"IMA_OPENAPI_CLIENTID", "IMA_OPENAPI_APIKEY", "LLM_API_KEY", "IMA_ARCHIVE_TOKEN"}
_ENV_SUFFIXES = ("_TOKEN", "_SECRET", "_APIKEY", "_API_KEY")
_SECRET_NAMES = {
    "apikey", "token", "accesstoken", "refreshtoken", "idtoken", "secret",
    "password", "passwd", "pwd", "clientsecret", "authorization",
    "proxyauthorization", "cookie", "setcookie", "credential", "credentials",
    "accesskey", "accesskeyid", "secretaccesskey", "securitytoken",
    "imaopenapiclientid",
}
_SIGNED_QUERY_NAMES = _SECRET_NAMES | {
    "sign", "sig", "signature", "auth", "policy", "ossaccesskeyid",
    "awsaccesskeyid", "googleaccessid", "xamzsignature", "xamzcredential",
    "xamzsecuritytoken", "xgoogsignature", "xgoogcredential", "qsignalgorithm",
    "qsignak", "qsignkeytime", "qsignature",
}
# A backslash before each slash also accepts URLs inside JSON-encoded traces.
_URL = re.compile(r"https?:(?:\\?/){2}[^\s<>\"'`\[\](){}（）【】，。；！？、“”‘’]+", re.IGNORECASE)
_KEY = (
    r"(?:[a-z][a-z0-9]*[_-])*"
    r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|"
    r"client[_-]?secret|secret[_-]?access[_-]?key|access[_-]?key(?:[_-]?id)?|"
    r"token|secret|password|passwd|pwd|authorization|credentials?|cookie|"
    r"ima[_-]openapi[_-]clientid)"
)
_ASSIGNMENT = re.compile(
    r"(?P<prefix>(?<![a-z0-9_])" + _KEY + r"[\"']?\s*[:=]\s*)"
    r"(?P<value>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|"
    r"(?:Bearer|Basic)\s+[a-z0-9._~+/=-]+|[^\s,;&<>\"'`{}\[\]()，。；！？]+)",
    re.IGNORECASE,
)
_BEARER = re.compile(r"(?<![a-z0-9_])Bearer\s+[a-z0-9._~+/=-]+", re.IGNORECASE)
_SK_KEY = re.compile(r"(?<![a-zA-Z0-9_])sk-[a-zA-Z0-9_-]+")


def _normalized_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def _is_secret_key(key: str) -> bool:
    normalized = _normalized_key(key)
    return (
        normalized in _SECRET_NAMES
        or normalized.endswith(("apikey", "token", "secret", "password"))
        or key.upper() in _ENV_NAMES
        or key.upper().endswith(_ENV_SUFFIXES)
    )


def _is_header_key(key: str) -> bool:
    return _normalized_key(key).endswith("headers")


def _known_secret_pattern() -> re.Pattern[str] | None:
    values = set()
    # Enumerate names first, then read only explicitly classified secret values.
    for name in list(os.environ):
        if name.upper() in _ENV_NAMES or name.upper().endswith(_ENV_SUFFIXES):
            value = os.environ.get(name, "")
            if len(value) >= 6:
                values.add(value)
    if not values:
        return None
    return re.compile("|".join(re.escape(value) for value in sorted(values, key=lambda value: (-len(value), value))))


def _public_url(match: re.Match[str]) -> str:
    original = match.group(0)
    # Punctuation belongs to the surrounding sentence, not the URL credential.
    candidate = original.rstrip(".,;:!?")
    suffix = original[len(candidate):]
    detection = html.unescape(candidate.replace("\\/", "/"))
    detection = re.sub(r"\\u0026", "&", detection, flags=re.IGNORECASE)
    detection = re.sub(r"\\u003d", "=", detection, flags=re.IGNORECASE)
    try:
        parts = urlsplit(detection)
        query = parts.query
        has_userinfo = parts.username is not None or parts.password is not None
    except ValueError:
        # A malformed URL must still not expose an otherwise recognizable query.
        query = detection.partition("?")[2].partition("#")[0]
        has_userinfo = "@" in detection.split("/", 3)[2]
    names = (name for name, _ in parse_qsl(query.replace(";", "&"), keep_blank_values=True))
    if has_userinfo or any(_normalized_key(name) in _SIGNED_QUERY_NAMES or _is_secret_key(name) for name in names):
        return REDACTED + suffix
    return original


def _public_assignment(match: re.Match[str]) -> str:
    value = match.group("value")
    quote = value[0] if value[0] in "\"'" else ""
    return match.group("prefix") + quote + REDACTED + quote


def sanitize_public(value: Any) -> Any:
    """Return a sanitized copy of nested public data, using ``[已隐藏]``.

    Dicts and lists are copied, tuples become lists, and scalar JSON values are
    preserved. Credential/header values are hidden wholesale; strings and dict
    keys also lose signed URLs, credential assignments, Bearer/sk keys, and
    exact known environment secrets of at least six characters. Other objects
    (including pathlib paths) are converted to sanitized text. Text stays raw
    Unicode: the preview renderer remains responsible for HTML escaping.
    """
    known_secrets = _known_secret_pattern()

    def text(raw: str) -> str:
        clean = _URL.sub(_public_url, raw)
        clean = _ASSIGNMENT.sub(_public_assignment, clean)
        clean = _BEARER.sub("Bearer " + REDACTED, clean)
        clean = _SK_KEY.sub(REDACTED, clean)
        return known_secrets.sub(lambda _: REDACTED, clean) if known_secrets else clean

    def visit(item: Any) -> Any:
        if isinstance(item, dict):
            return {
                text(str(key)): REDACTED if _is_header_key(str(key)) or _is_secret_key(str(key)) else visit(child)
                for key, child in item.items()
            }
        if isinstance(item, (list, tuple)):
            return [visit(child) for child in item]
        if item is None or isinstance(item, (bool, int, float)):
            return item
        return text(item if isinstance(item, str) else str(item))

    return visit(value)
