"""Small OpenAI-compatible client. Keys stay in server environment variables."""
from __future__ import annotations

import json
import os
import re
import threading
import time

import requests


class ModelError(RuntimeError):
    """A safe, user-readable model error (never includes headers or raw replies)."""


class LLMClient:
    _lock = threading.Lock()
    _calls: dict[str, int] = {}

    def __init__(self):
        self.key = os.environ.get("LLM_API_KEY", "").strip()
        self.base = os.environ.get("LLM_BASE_URL", "https://api.openai-next.com/v1").rstrip("/")
        self.model = os.environ.get("LLM_MODEL", "gpt-5.4").strip()
        self.fallback_models = [m.strip() for m in os.environ.get(
            "LLM_FALLBACK_MODELS", "claude-fable-5,gpt-5.4-mini").split(",") if m.strip()]
        self.max_calls = int(os.environ.get("LLM_MAX_DAILY_CALLS", "400"))
        if not self.key:
            raise ModelError("模型服务未配置。请由部署者配置 LLM_API_KEY 服务端密钥。")
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
                    msg = response.json()["choices"][0]["message"]["content"]
                    if isinstance(msg, list):
                        msg = "".join(x.get("text", "") for x in msg if isinstance(x, dict))
                except (ValueError, KeyError, IndexError, TypeError):
                    if attempt < tries - 1:
                        continue
                    raise ModelError("模型响应格式异常，本次生成已停止。") from None
                self.model = model_name
                return self._parse(msg)
        if last_status:
            raise ModelError(f"模型服务返回 HTTP {last_status}，本次生成已停止。")
        raise ModelError("模型服务连接超时或暂时不可用；本次没有生成可发布文案。")
