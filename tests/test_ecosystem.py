"""Semi-final scope: phone / tablet / ecosystem promotion.

Facts and images for non-PC families must come from an explicitly supplied
official Huawei Mall product page; nothing is invented or borrowed from other
models, and the PC knowledge base is not consulted for them.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import agent
import ecosystem
import policy
from test_agent import MockIMA, MockModel, QUOTE, SYNTHETIC_LLM_KEY


PHONE = "HUAWEI Mate 70 Pro"
TABLET = "HUAWEI MatePad Pro 13.2"
COMBO = "HUAWEI Mate 70 Pro + HUAWEI MatePad Pro 13.2"


class EcosystemUnitTests(unittest.TestCase):
    def test_families_are_detected_from_product_names(self):
        cases = {
            "HUAWEI MateBook Pro S": "pc",
            PHONE: "phone",
            TABLET: "tablet",
            "HUAWEI WATCH 5": "wearable",
            COMBO: "ecosystem",
            "Mate 70 Pro + MatePad Pro 13.2": "ecosystem",
        }
        for product, expected in cases.items():
            with self.subTest(product=product):
                self.assertEqual(ecosystem.product_family(product), expected)

    def test_only_pc_uses_the_authorised_knowledge_base(self):
        self.assertFalse(ecosystem.needs_mall_evidence("pc"))
        for family in ("phone", "tablet", "wearable", "ecosystem"):
            self.assertTrue(ecosystem.needs_mall_evidence(family))

    def test_combination_matches_each_device_against_the_catalogue(self):
        catalogue = ["HUAWEI Mate 70 Pro", "HUAWEI MatePad Pro 13.2"]
        self.assertEqual(policy.exact_product(COMBO, catalogue),
                         "HUAWEI Mate 70 Pro + HUAWEI MatePad Pro 13.2")
        self.assertIsNone(policy.exact_product("HUAWEI Mate 70 Pro + HUAWEI MateBook Q9", catalogue))

    def test_ecosystem_guidance_is_only_injected_for_non_pc(self):
        self.assertEqual(ecosystem.ecosystem_guidance("pc"), "")
        self.assertIn("协同", ecosystem.ecosystem_guidance("ecosystem"))
        self.assertIn("手机", ecosystem.ecosystem_guidance("phone"))


class EcosystemFlowTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="zhiheng-eco-tests-")
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.picture = self.root / "mall.png"
        Image.new("RGB", (18, 12), (18, 90, 200)).save(self.picture)
        self.ima, self.model = MockIMA(self.picture), MockModel()
        self.env = patch.dict(os.environ, {"LLM_API_KEY": SYNTHETIC_LLM_KEY,
                                           "LLM_BASE_URL": "https://synthetic-model.example/v1"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.ima_patch = patch("agent._ima", return_value=self.ima)
        self.ima_patch.start()
        self.addCleanup(self.ima_patch.stop)
        self.model_patch = patch("agent.LLMClient", return_value=self.model)
        self.model_factory = self.model_patch.start()
        self.addCleanup(self.model_patch.stop)
        self.no_network = patch("requests.sessions.Session.request",
                                side_effect=AssertionError("External network is forbidden in this suite"))
        self.no_network.start()
        self.addCleanup(self.no_network.stop)

    def run_task(self, product, requirements="", **extra):
        values = {"product": product, "audience": "经常出差的职场人", "scenario": "职场办公",
                  "platform": "门店朋友圈", "goal": "到店体验", "requirements": requirements}
        values.update(extra)
        return agent.run_task(**values)

    def assets(self):
        return {
            "sources": [{"title": PHONE + " 官方商城", "text": QUOTE, "kind": "facts",
                         "official_url": "https://www.vmall.com/product/88888.html",
                         "retrieved_at": "2026-10-19T02:00:00+00:00", "origin": "official_vmall"}],
            "images": [{"title": PHONE, "caption": "官方商城商品图，画面内容未逐像素核验。", "model": PHONE,
                        "path": str(self.picture), "url": "https://img.vmall.com/p/88888.jpg",
                        "source_title": PHONE + " 官方商城", "origin": "official_vmall",
                        "retrieved_at": "2026-10-19T02:00:00+00:00"}],
        }

    def test_phone_without_official_page_asks_for_the_link(self):
        with patch("agent.fetch_vmall_assets", return_value={"sources": [], "images": []}):
            result = self.run_task(PHONE)
        self.assertEqual(result["status"], "needs_clarification", result.get("report"))
        self.assertIn("官方商城", result["report"])
        self.assertEqual(self.ima.retrieve_calls, [])
        self.model_factory.assert_not_called()

    def test_phone_page_supplies_facts_and_images_without_the_pc_knowledge_base(self):
        with patch("agent.fetch_vmall_assets", return_value=self.assets()):
            result = self.run_task(PHONE, requirements="https://www.vmall.com/product/88888.html")
        self.assertEqual(result["status"], "ready", result.get("report"))
        self.assertEqual(result["checks"]["retrieval_mode"], "official_vmall")
        self.assertEqual(result["checks"]["official_vmall_sources"], 1)
        self.assertEqual(set(result["checks"]["source_origins"]), {"official_vmall"})
        self.assertEqual(result["images"][0]["origin"], "official_vmall")
        self.assertEqual(self.ima.retrieve_calls, [])

    def test_ecosystem_combination_keeps_one_copy_for_multiple_devices(self):
        with patch("agent.fetch_vmall_assets", return_value=self.assets()):
            result = self.run_task(COMBO, requirements="https://www.vmall.com/product/88888.html")
        self.assertEqual(result["status"], "ready", result.get("report"))
        import json
        artifact = json.loads(Path(result["export_json"]).read_text(encoding="utf-8"))
        self.assertEqual(artifact["task"]["product_family"], "ecosystem")
        compose = next(payload for phase, payload in self.model.calls if phase == "compose")
        self.assertIn("生态组合", compose["ecosystem"])


if __name__ == "__main__":
    unittest.main()
