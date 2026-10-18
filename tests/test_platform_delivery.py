"""Four fast local-only checks for layout, packaging and publication format."""
from __future__ import annotations

import copy
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image

from platform_delivery import export_delivery
from preview import build_preview


class PlatformDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="zhiheng-platform-tests-")
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.no_network = patch("socket.create_connection", side_effect=AssertionError("No network allowed"))
        self.no_network.start()
        self.addCleanup(self.no_network.stop)
        self.task = {"platform": "门店朋友圈", "product": "Synthetic Model", "requirements": "PRIVATE-TASK"}
        self.images = []
        for index, (color, slot) in enumerate([((230, 10, 10), 2), ((10, 230, 10), 0), ((10, 10, 230), 2)], 1):
            path = self.root / f"private-original-{index}.jpg"
            picture = Image.new("RGB", (80, 40), color)
            exif = picture.getexif()
            exif[270] = "PRIVATE-EXIF"
            picture.save(path, exif=exif)
            self.images.append({"id": f"I{index}", "path": str(path), "slot": slot,
                                "model": "Synthetic Model", "origin": "offline_archive",
                                "title": f"配图{index}", "caption": f"资料图{index} [S9]",
                                "source_title": "PRIVATE-SOURCE", "quote": "PRIVATE-FULL-QUOTE",
                                "headers": {"Authorization": "PRIVATE-TOKEN"}})
        self.units = [{"id": "title", "text": "带着清单选电脑", "fact_ids": []},
                      {"id": "intro", "text": "先明确日常使用任务。", "fact_ids": []},
                      {"id": "section_1", "heading": "核对常用任务", "text": "带上常用资料到店确认具体版本。" * 6 + " [F1] [S2]", "fact_ids": ["F1"]},
                      {"id": "cta", "text": "私信使用需求，预约到店确认。", "fact_ids": []}]

    def export(self, units=None, images=None, task=None):
        return export_delivery(units if units is not None else self.units,
                               images if images is not None else self.images,
                               task if task is not None else self.task,
                               "主办方 ZIP 缓存 + 华为官方商城本次读取", self.root / "delivery", "备用文案 [F1]")

    def test_four_previews_are_distinct_escaped_and_self_contained(self):
        units = copy.deepcopy(self.units)
        units[0]["text"] = '<script>alert("synthetic")</script>'
        previews = []
        for platform, count in [("小红书", 3), ("微信公众号", 3), ("门店朋友圈", 3), ("门店海报", 1)]:
            with self.subTest(platform=platform):
                preview = build_preview(units, self.images, {**self.task, "platform": platform}, "混合资料模式")
                previews.append(preview)
                self.assertEqual(preview.count('<img src="data:image/jpeg;base64,'), count)
                self.assertNotIn("<script>", preview)
                self.assertIn("&lt;script&gt;", preview)
                self.assertIn("height:auto", preview)
                self.assertIn("主办方 ZIP 缓存（非实时 ima）", preview)
                self.assertNotIn("华为官方商城本次读取", preview)
        self.assertEqual(len(set(previews)), 4)
        self.assertIn("max-width:677px", previews[1])
        self.assertIn("grid-template-columns", previews[2])
        self.assertIn("<ul", previews[3])

    def test_publish_bundle_contains_only_clean_text_ordered_reencoded_images(self):
        result = self.export()
        standalone = Path(result["export_html"]).read_text(encoding="utf-8")
        self.assertIn("data:image/jpeg;base64,", standalone)
        self.assertNotIn("[F1]", result["publish_copy"])
        with ZipFile(result["export_bundle"]) as bundle:
            self.assertEqual(bundle.namelist(), ["排版.html", "发布文案.txt", "平台使用说明.txt",
                                                 "images/01.jpg", "images/02.jpg", "images/03.jpg"])
            public = "\n".join(bundle.read(name).decode("utf-8") for name in bundle.namelist() if not name.endswith(".jpg"))
            for private in ("[F1]", "[S2]", "[S9]", "PRIVATE-SOURCE", "PRIVATE-FULL-QUOTE", "PRIVATE-TOKEN", "PRIVATE-TASK", str(self.root), "offline_archive"):
                self.assertNotIn(private, public)
            # Slots sort first; equal-slot images preserve their original selection order.
            for name, dominant in [("images/01.jpg", 1), ("images/02.jpg", 0), ("images/03.jpg", 2)]:
                raw = bundle.read(name)
                self.assertNotIn(b"PRIVATE-EXIF", raw)
                with Image.open(BytesIO(raw)) as image:
                    self.assertEqual(image.format, "JPEG")
                    self.assertEqual(image.size, (80, 40))
                    self.assertFalse(image.getexif())
                    color = image.getpixel((20, 20))
                    self.assertGreater(color[dominant], 200)
        with Image.open(self.images[0]["path"]) as original:
            self.assertIn("PRIVATE-EXIF", str(original.getexif()))

    def test_wechat_layout_and_ready_checks_match_policy(self):
        units = copy.deepcopy(self.units)
        units[2]["text"] = "携带常用资料到店确认具体版本和软件适配情况。" * 30
        result = self.export(units=units, images=self.images[:2], task={**self.task, "platform": "微信公众号"})
        checks = result["platform_checks"]
        self.assertTrue(checks["ready"], checks["issues"])
        self.assertEqual(checks["title"]["max"], 45)
        self.assertGreaterEqual(checks["body"]["chinese_characters"], 650)
        html = Path(result["export_html"]).read_text(encoding="utf-8")
        for marker in ("max-width:677px", "<h1", "<h2", "<figcaption", "预约到店确认"):
            self.assertIn(marker, html)
        self.assertIn("需先在公众号后台", result["delivery_notes"])
        self.assertIn("不能保证", result["delivery_notes"])
        self.assertNotIn("PRIVATE-SOURCE", html)

    def test_format_checks_report_actionable_title_length_images_headings_and_tags(self):
        task = {**self.task, "platform": "微信公众号"}
        units = copy.deepcopy(self.units)
        units[0]["text"] = "题" * 46
        units[2]["heading"] = ""
        result = self.export(units=units, images=[{**self.images[0], "path": "https://example.test/image.jpg"}], task=task)
        checks = result["platform_checks"]
        self.assertFalse(checks["ready"])
        for key in ("title", "body", "images", "headings"):
            self.assertFalse(checks[key]["ok"], key)
        self.assertGreaterEqual(len(checks["issues"]), 4)
        xhs = self.export(task={**self.task, "platform": "小红书"})["platform_checks"]
        self.assertFalse(xhs["tags"]["ok"])
        self.assertTrue(any("#" in issue for issue in xhs["issues"]))


if __name__ == "__main__":
    unittest.main()
