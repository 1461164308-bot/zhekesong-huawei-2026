"""Small OpenAI-compatible client. Keys stay in server environment variables."""
from __future__ import annotations

import json
import os
import re
import threading
import time

import requests


DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_FALLBACK = ""


class ModelError(RuntimeError):
    """A safe, user-readable model error (never includes headers or raw replies)."""


def resolve_api_config(raw: dict | None) -> dict | None:
    """Validate an optional user-supplied API override.

    The returned dict is kept in the caller's session state only: it is never
    written to disk, exported, logged or echoed back to the page.
    """
    if not isinstance(raw, dict):
        return None
    base = str(raw.get("base_url", "") or "").strip().rstrip("/")
    key = str(raw.get("api_key", "") or "").strip()
    model = str(raw.get("model", "") or "").strip()
    if not base and not key and not model:
        return None
    if not base or not key:
        raise ModelError("自定义 API 需要同时填写服务地址和 API 密钥。")
    if not base.startswith("https://"):
        raise ModelError("自定义 API 地址必须使用 HTTPS。")
    if len(key) < 8:
        raise ModelError("API 密钥长度异常，请检查后重试。")
    if len(base) > 300 or len(key) > 400 or len(model) > 120:
        raise ModelError("自定义 API 配置过长，请检查后重试。")
    return {"base_url": base, "api_key": key, "model": model or DEFAULT_MODEL}


class LLMClient:
    _lock = threading.Lock()
    _calls: dict[str, int] = {}

    def __init__(self, api_config: dict | None = None):
        override = resolve_api_config(api_config)
        if override:
            self.key = override["api_key"]
            self.base = override["base_url"]
            self.model = override["model"]
            self.custom = True
        else:
            self.key = os.environ.get("LLM_API_KEY", "").strip()
            self.base = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
            self.model = os.environ.get("LLM_MODEL", DEFAULT_MODEL).strip()
            self.custom = False
        self.fallback_models = [m.strip() for m in os.environ.get(
            "LLM_FALLBACK_MODELS", DEFAULT_FALLBACK).split(",") if m.strip()]
        if self.custom:
            # A user-supplied endpoint must not silently fall back to other models.
            self.fallback_models = []
        self.max_calls = int(os.environ.get("LLM_MAX_DAILY_CALLS", "240"))
        if not self.key or not self.base:
            raise ModelError("模型服务未配置。可在页面「模型 API 设置」中填写自己的服务地址与密钥，或由部署者配置服务端环境变量。")
        if not self.base.startswith("https://"):
            raise ModelError("模型服务地址必须使用 HTTPS。")

    @staticmethod
    def _parse(text: str) -> dict:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
        try:
            obj = json.loads(text)
        except (ValueError, TypeError):
            start, end = text.find("{"), text.rfind("}")
            try:
                obj = json.loads(text[start:end + 1]) if start >= 0 else None
            except (ValueError, TypeError):
                obj = None
        if not isinstance(obj, dict):
            raise ModelError("模型未返回有效结构化结果，本次没有发布文案。请重试。")
        return obj

    def json(self, system: str, payload: dict, max_tokens: int = 5000) -> dict:
        day = time.strftime("%Y-%m-%d", time.gmtime())
        with self._lock:
            count = self._calls.get(day, 0)
            if count >= self.max_calls:
                raise ModelError("今日演示调用额度已用完，请联系部署者调整额度。")
            self._calls[day] = count + 1
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "temperature": 0.3,
            "max_tokens": max_tokens,
        }
        attempts = [(self.model, 3)] + [(name, 2) for name in self.fallback_models]
        last_status = 0
        for model_name, tries in attempts:
            body["model"] = model_name
            for attempt in range(tries):
                try:
                    response = requests.post(
                        self.base + "/chat/completions",
                        headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json"},
                        json=body,
                        timeout=(12, 120),
                    )
                except requests.RequestException:
                    if attempt < tries - 1:
                        continue
                    break
                if response.status_code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                if not response.ok:
                    last_status = response.status_code
                    break
                try:
                    message = response.json()["choices"][0]["message"]
                    msg = message.get("content")
                    if isinstance(msg, list):
                        msg = "".join(x.get("text", "") for x in msg if isinstance(x, dict))
                    if not msg and message.get("reasoning_content"):
                        # Reasoning-only replies carry no deliverable JSON (seen on some
                        # free tier models). Move on to the next configured model instead
                        # of failing the whole task on the first attempt.
                        break
                except (ValueError, KeyError, IndexError, TypeError):
                    if attempt < tries - 1:
                        continue
                    raise ModelError("模型响应格式异常，本次生成已停止。") from None
                self.model = model_name
                return self._parse(msg)
        if last_status:
            raise ModelError(f"模型服务返回 HTTP {last_status}，本次生成已停止。")
        raise ModelError("模型服务连接超时或暂时不可用；本次没有生成可发布文案。")
