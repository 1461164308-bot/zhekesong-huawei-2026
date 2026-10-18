"""Public-output regression tests: synthetic credentials, no network or files."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from public_payload import REDACTED, sanitize_public


class PublicPayloadTests(unittest.TestCase):
    def setUp(self):
        # Never depend on or emit credentials from the test runner's environment.
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_recursive_public_boundaries_preserve_source_and_local_image_path(self):
        signed = "https://bucket.myqcloud.com/image?sign=synthetic-private"
        payload = {
            "task": {"requirements": "请强调便携 api_key=sk-syntheticsecretmarker"},
            "accepted": ({"text": "配图 " + signed, "fact_ids": ["F1"]},),
            "facts": [{"id": "F1", "quote": "屏幕为14.2英寸，支持120 Hz。"}],
            "checks": {"trace": "服务返回 Bearer synthetic-trace-token"},
            "strategy": {"extra": "password='synthetic spaced password'"},
            "preview": {"images": [{"path": r"C:\cache\image.png", "caption": "产品侧面图"}]},
            "rawmodel": json.dumps({"url": signed, "user": "access_token=synthetic-user-token"}),
        }
        before = copy.deepcopy(payload)
        public = sanitize_public(payload)
        serialized = json.dumps(public, ensure_ascii=False)
        for secret in ("synthetic-private", "bucket.myqcloud.com", "sk-syntheticsecretmarker",
                       "synthetic-trace-token", "synthetic spaced password", "synthetic-user-token"):
            self.assertNotIn(secret, serialized)
        self.assertEqual(payload, before)
        self.assertIsInstance(public["accepted"], list)
        self.assertEqual(public["facts"], payload["facts"])
        self.assertEqual(public["preview"], payload["preview"])
        public["facts"][0]["id"] = "changed"
        self.assertEqual(payload["facts"][0]["id"], "F1")

    def test_whole_headers_and_sensitive_dict_values_are_hidden(self):
        fields = ["headers", "request_headers", "Response-Headers", "httpHeaders",
                  "API_KEY", "token", "secret", "password", "clientSecret", "authToken",
                  "Authorization", "refresh_token", "IMA_OPENAPI_CLIENTID", "MY_SECRET"]
        source = {field: {"nested": "synthetic-hidden-value"} for field in fields}
        self.assertEqual(sanitize_public(source), {field: REDACTED for field in fields})
        self.assertEqual(sanitize_public({"token_count": 12, "max_tokens": 2048}),
                         {"token_count": 12, "max_tokens": 2048})

    def test_environment_secret_names_and_exact_matching(self):
        names = ["IMA_OPENAPI_CLIENTID", "IMA_OPENAPI_APIKEY", "LLM_API_KEY", "IMA_ARCHIVE_TOKEN",
                 "CUSTOM_TOKEN", "CUSTOM_SECRET", "CUSTOM_APIKEY", "CUSTOM_API_KEY"]
        values = {name: f"synthetic-exact-value-{index}" for index, name in enumerate(names)}
        values.update({"LLM_BASE_URL": "https://api.example.test/v1", "IMA_KB_NAME": "普通知识库名称",
                       "PRODUCT_MODEL": "HUAWEI MateBook D 16", "SHORT_TOKEN": "abcde"})
        with patch.dict(os.environ, values):
            for name in names:
                self.assertEqual(sanitize_public("开头 " + values[name] + " 结尾"), "开头 " + REDACTED + " 结尾")
            for name in ("LLM_BASE_URL", "IMA_KB_NAME", "PRODUCT_MODEL", "SHORT_TOKEN"):
                self.assertEqual(sanitize_public(values[name]), values[name])
            self.assertEqual(sanitize_public("SYNTHETIC-EXACT-VALUE-0"), "SYNTHETIC-EXACT-VALUE-0")

    def test_environment_changes_apply_after_import_and_between_calls(self):
        with patch.dict(os.environ, {"LLM_API_KEY": "synthetic-first-key"}):
            self.assertEqual(sanitize_public("synthetic-first-key synthetic-second-key"), REDACTED + " synthetic-second-key")
        with patch.dict(os.environ, {"LLM_API_KEY": "synthetic-second-key"}):
            self.assertEqual(sanitize_public("synthetic-first-key synthetic-second-key"), "synthetic-first-key " + REDACTED)
        self.assertEqual(sanitize_public("synthetic-second-key"), "synthetic-second-key")

    def test_environment_values_are_literal_and_longest_match_wins(self):
        with patch.dict(os.environ, {"A_TOKEN": "synthetic.*+?[]", "B_SECRET": "synthetic.*+?[]-long"}):
            self.assertEqual(sanitize_public("synthetic.*+?[]-long"), REDACTED)
            self.assertEqual(sanitize_public("synthetic-not-a-regex-match"), "synthetic-not-a-regex-match")

    def test_signed_urls_are_removed_wholesale_case_insensitively(self):
        names = ["sign", "SIGNATURE", "Token", "x-amz-signature", "X-Amz-Credential",
                 "OSSAccessKeyId", "policy", "AWSAccessKeyId", "X-Goog-Signature",
                 "Q-Sign-Algorithm", "sig", "access_token", "api_key", "Authorization"]
        for name in names:
            with self.subTest(name=name):
                url = "https://bucket.example.test/private/image?width=800&" + name + "=synthetic-url-secret#image"
                self.assertEqual(sanitize_public("图源（" + url + "），F1。"), "图源（" + REDACTED + "），F1。")
                self.assertEqual(sanitize_public(url), REDACTED)

    def test_encoded_query_names_escaped_urls_and_raw_json_traces(self):
        urls = [
            "https://bucket.example.test/image?%73%69%67%6e=synthetic-secret",
            "https://bucket.example.test/image?w=1&amp;SIGN=synthetic-secret",
            "https://bucket.example.test/image?w=1;signature=synthetic-secret",
            r"https:\/\/bucket.example.test\/image?w=1\u0026token\u003dsynthetic-secret",
            "https://synthetic-user:synthetic-password@bucket.example.test/image",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(sanitize_public(url), REDACTED)
                self.assertNotIn("bucket.example.test", sanitize_public('trace: {"url":"' + url + '"}'))
        self.assertEqual(sanitize_public("链接 https://bucket.example.test/image?sign=x, 引用F1"),
                         "链接 " + REDACTED + ", 引用F1")

    def test_inline_credentials_cover_quoted_values_bearer_and_short_sk_keys(self):
        samples = [
            "api_key=sk-syntheticsecretmarker", "API-KEY: synthetic-secret",
            '"access_token": "synthetic-secret"', "password='synthetic secret with spaces'",
            "client_secret=synthetic-secret", "CUSTOM_TOKEN=synthetic-secret",
            "authorization=Bearer synthetic-secret", "authorization: Basic c3ludGhldGlj",
            "Bearer synthetic-secret", "鉴权Bearer synthetic-secret", "bearer synthetic.secret-_=+/", "sk-abcd",
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                result = sanitize_public(sample)
                self.assertIn(REDACTED, result)
                for raw in ("synthetic", "c3ludGhldGlj", "sk-abcd"):
                    self.assertNotIn(raw, result)

    def test_dict_keys_are_sanitized_too(self):
        with patch.dict(os.environ, {"CUSTOM_SECRET": "synthetic-key-marker"}):
            self.assertEqual(sanitize_public({"synthetic-key-marker": "正常事实"}), {REDACTED: "正常事实"})

    def test_normal_models_facts_links_captions_and_markup_are_unchanged(self):
        data = {
            "product": "HUAWEI MateBook D 16 / MateBook 14（鸿蒙版） / Pro S",
            "id": "F12", "source_id": "S3", "quote": "厚度 < 20 mm，事实 A&B；引用『原文』。",
            "caption": "产品正面图 <示意>，查看实际型号。",
            "url": "https://consumer.huawei.com/cn/laptops/?model=matebook-d-16&lang=zh#specs",
            "html_text": '<b>原文 & 引用</b>',
            "LLM_BASE_URL": "https://api.example.test/v1", "IMA_KB_NAME": "电脑产品知识库",
            "none": None, "bool": True, "integer": 16, "float": 14.2,
        }
        self.assertEqual(sanitize_public(data), data)
        self.assertEqual(sanitize_public(Path("cache") / "image.png"), str(Path("cache") / "image.png"))

    def test_sanitizing_public_result_again_is_idempotent(self):
        value = {"password": "synthetic-secret", "requirements": 'api_key="synthetic-secret"',
                 "trace": "Bearer synthetic-token; https://bucket.test/image?sign=synthetic-secret"}
        once = sanitize_public(value)
        self.assertEqual(sanitize_public(once), once)


if __name__ == "__main__":
    unittest.main()
