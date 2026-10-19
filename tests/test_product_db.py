"""Offline tests for the official product database builder; no network is used."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import build_product_db as builder  # noqa: E402

SPEC_HTML = """
<ul>
  <li class="large-accordion__item">
    <button><span class="large-accordion__title large-accordion-title">屏幕</span></button>
    <div class="large-accordion__content"><div class="large-accordion-columns"><div class="large-accordion__inner ">
      <div class="large-accordion-subtitle">尺寸 </div>
      <p>6.75 英寸</p>
      <p class="large-accordion-subtext">*显示屏采用圆角设计，实际可视区域略小。</p>
    </div><div class="large-accordion__inner ">
      <div class="large-accordion-subtitle">分辨率</div>
      <p>1600 × 720 像素</p>
    </div></div></div>
  </li>
  <li class="large-accordion__item">
    <button><span class="large-accordion__title large-accordion-title">电池</span></button>
    <div class="large-accordion__content"><div class="large-accordion__inner ">
      <div class="large-accordion-subtitle">容量</div>
      <p>5000 mAh（典型值）</p>
    </div></div>
  </li>
</ul>
"""

PRODUCT_HTML = """
<html><head><meta name="description" content="合成产品介绍文案。"></head><body>
<h1>HUAWEI 合成机型</h1>
<h2>踏 光 向 前</h2><h2>新面貌</h2>
<img data-src="/etc/designs/common/images/logo.svg" alt="logo">
<img data-src="/content/dam/huawei-cbg-site/cn/mkt/pdp/phones/syn/kv.jpg" alt="合成机型 KV">
<img data-src="/content/dam/huawei-cbg-site/cn/mkt/pdp/phones/syn/detail.png" alt="">
<img data-src="/content/dam/huawei-cbg-site/cn/mkt/pdp/phones/syn/kv.jpg" alt="重复图">
<img data-src="https://example.com/other.jpg" alt="站外图">
<img data-src="/content/dam/huawei-cbg-site/cn/mkt/pdp/phones/syn/icon-arrow.png" alt="箭头">
</body></html>
"""


class SpecParserTests(unittest.TestCase):
    def setUp(self):
        self.sections = builder.parse_specs(SPEC_HTML)

    def test_sections_keep_official_order_and_titles(self):
        self.assertEqual([name for name, _ in self.sections], ["屏幕", "电池"])

    def test_fields_values_and_qualifiers_are_separated(self):
        screen = dict((field, (values, notes)) for field, values, notes in self.sections[0][1])
        self.assertEqual(screen["尺寸"][0], ["6.75 英寸"])
        self.assertIn("圆角设计", screen["尺寸"][1][0])
        self.assertEqual(screen["分辨率"][0], ["1600 × 720 像素"])
        self.assertEqual(screen["分辨率"][1], [])

    def test_qualifier_text_is_not_mixed_into_values(self):
        for _, fields, in self.sections:  # noqa: B007
            for _, values, notes in fields:
                self.assertFalse(any(value.startswith("*") for value in values))
                self.assertTrue(all(note.startswith("*") for note in notes))

    def test_empty_html_yields_no_sections(self):
        self.assertEqual(builder.parse_specs("<div>无规格</div>"), [])


class ProductParserTests(unittest.TestCase):
    def setUp(self):
        self.product = builder.parse_product(PRODUCT_HTML)

    def test_title_and_description(self):
        self.assertEqual(self.product["title"], "HUAWEI 合成机型")
        self.assertEqual(self.product["description"], "合成产品介绍文案。")

    def test_highlights_strip_spacing_and_dedupe(self):
        self.assertEqual(self.product["highlights"], ["踏光向前", "新面貌"])

    def test_only_same_site_product_images_survive(self):
        urls = [image["url"] for image in self.product["images"]]
        self.assertEqual(urls, [
            "https://consumer.huawei.com/content/dam/huawei-cbg-site/cn/mkt/pdp/phones/syn/kv.jpg",
            "https://consumer.huawei.com/content/dam/huawei-cbg-site/cn/mkt/pdp/phones/syn/detail.png",
        ])
        self.assertEqual(self.product["images"][0]["alt"], "合成机型 KV")


class RenderTests(unittest.TestCase):
    def test_facts_keep_source_links_and_qualifiers(self):
        product = builder.parse_product(PRODUCT_HTML)
        text = builder.render_facts("HUAWEI 合成机型", product, builder.parse_specs(SPEC_HTML),
                                    "https://consumer.huawei.com/cn/phones/syn/",
                                    "https://consumer.huawei.com/cn/phones/syn/specs/", "2026-10-19")
        self.assertIn("# HUAWEI 合成机型 - 产品事实", text)
        self.assertIn("## 屏幕", text)
        self.assertIn("6.75 英寸", text)
        self.assertIn("*显示屏采用圆角设计", text)
        self.assertIn("https://consumer.huawei.com/cn/phones/syn/specs/", text)
        self.assertIn("抓取日期：2026-10-19", text)

    def test_unsafe_path_characters_are_replaced(self):
        self.assertEqual(builder.safe_name('HUAWEI A/B:C*?'), "HUAWEI A-B-C--")
        self.assertEqual(builder.safe_name("   "), "未命名")

    def test_unknown_category_is_rejected_by_cli(self):
        self.assertEqual(builder.main(["--categories", "not-a-category"]), 2)


if __name__ == "__main__":
    unittest.main()
