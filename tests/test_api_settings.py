"""Session-scoped custom API settings: validation, isolation and no leakage."""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from llm_client import LLMClient, ModelError, resolve_api_config


class ApiConfigTests(unittest.TestCase):
    def test_blank_input_means_use_server_configuration(self):
        for raw in (None, {}, {"base_url": "", "api_key": "", "model": ""}):
            with self.subTest(raw=raw):
                self.assertIsNone(resolve_api_config(raw))

    def test_partial_or_insecure_config_is_rejected_with_safe_message(self):
        cases = [
            {"base_url": "https://api.example.com/v1"},
            {"base_url": "http://api.example.com/v1", "api_key": "synthetic-key-value"},
            {"base_url": "https://api.example.com/v1", "api_key": "short"},
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                with self.assertRaises(ModelError) as caught:
                    resolve_api_config(raw)
                message = str(caught.exception)
                self.assertNotIn("synthetic-key-value", message)

    def test_valid_config_is_normalized_and_kept_off_the_environment(self):
        raw = {"base_url": "https://api.example.com/v1/", "api_key": "synthetic-key-value",
               "model": "custom-model"}
        config = resolve_api_config(raw)
        self.assertEqual(config["base_url"], "https://api.example.com/v1")
        self.assertEqual(config["model"], "custom-model")
        self.assertNotIn("synthetic-key-value", json.dumps(dict(os.environ), ensure_ascii=False))

    def test_custom_endpoint_does_not_inherit_environment_or_fallbacks(self):
        env = {"LLM_API_KEY": "server-key-value", "LLM_BASE_URL": "https://server.example.com/v1",
               "LLM_MODEL": "server-model"}
        with patch.dict(os.environ, env, clear=False):
            client = LLMClient({"base_url": "https://api.example.com/v1",
                                "api_key": "synthetic-key-value", "model": "custom-model"})
        self.assertTrue(client.custom)
        self.assertEqual(client.base, "https://api.example.com/v1")
        self.assertEqual(client.key, "synthetic-key-value")
        self.assertEqual(client.model, "custom-model")
        self.assertEqual(client.fallback_models, [])

    def test_server_configuration_still_used_without_override(self):
        env = {"LLM_API_KEY": "server-key-value", "LLM_BASE_URL": "https://server.example.com/v1",
               "LLM_MODEL": "server-model"}
        with patch.dict(os.environ, env, clear=False):
            client = LLMClient()
        self.assertFalse(client.custom)
        self.assertEqual(client.model, "server-model")


if __name__ == "__main__":
    unittest.main()
