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
  <li class="large-accordion__item">
    <button><span class="large-accordion__title large-accordion-title">尺寸与重量</span></button>
    <div class="large-accordion__content"><div class="large-accordion__inner large-accordion__inner--short">
      <div class="large-accordion__wrap">
        <div class="large-accordion-subtitle size-height-name">长度</div>
        <p>160.9 mm</p>
      </div>
      <div class="large-accordion__wrap">
        <div class="large-accordion-subtitle">重量</div>
        <p>约 203 g（含电池）</p>
        <p class="large-accordion-subtext">*实际重量依配置与制造工艺有所差异。</p>
      </div>
    </div></div>
  </li>
  <li class="large-accordion__item">
    <button><span class="large-accordion__title large-accordion-title">理论工作时间</span></button>
    <div class="large-accordion__content"><div class="large-accordion__inner">
      <p>常规使用 3 天；AOD 使用 2 天</p>
      <p class="large-accordion-subtext">*实际续航依使用习惯有所差异。</p>
    </div></div>
  </li>
  <li class="large-accordion__item">
    <button><span class="large-accordion__title large-accordion-title">重量</span></button>
    <div class="large-accordion__content"><div class="large-accordion-columns multi-watchGt">
      <div class="multi-watchGt-item">
        <div class="multi-watchGt-title">HUAWEI 合成机型 42 mm</div>
        <div class="multi-watchGt-cnt"><div class="multi-watchGt-list part0">
          <div class="multi-watchGt-subtitle"></div>
          <div class="multi-watchGt-text"><p>约 38 g（不含表带）</p></div>
          <p class="multi-watchGt-subtext"></p>
        </div></div>
      </div>
      <div class="multi-watchGt-item">
        <div class="multi-watchGt-title">HUAWEI 合成机型 46 mm</div>
        <div class="multi-watchGt-cnt"><div class="multi-watchGt-list part0">
          <div class="multi-watchGt-subtitle">表壳材质</div>
          <div class="multi-watchGt-text"><p>约 60 g（不含表带）</p></div>
        </div></div>
      </div>
      <div class="large-accordion__inner">
        <p class="large-accordion-text">*实际重量依配置与制造工艺有所差异。</p>
      </div>
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
        self.assertEqual([name for name, _ in self.sections],
                         ["屏幕", "电池", "尺寸与重量", "理论工作时间", "重量"])

    def test_scalar_section_keeps_its_value_without_a_field_label(self):
        section, fields = self.sections[3]
        self.assertEqual(section, "理论工作时间")
        self.assertEqual(fields, [("", ["常规使用 3 天；AOD 使用 2 天"],
                                  ["*实际续航依使用习惯有所差异。"])])

    def test_per_version_layout_keeps_every_version_and_its_caveat(self):
        section, fields = self.sections[4]
        self.assertEqual(section, "重量")
        self.assertEqual(fields[0], ("", ["HUAWEI 合成机型 42 mm："], []))
        self.assertEqual(fields[1], ("", ["约 38 g（不含表带）"], []))
        self.assertEqual(fields[2], ("", ["HUAWEI 合成机型 46 mm："], []))
        self.assertEqual(fields[3][0], "表壳材质")
        self.assertEqual(fields[3][1], ["约 60 g（不含表带）"])
        self.assertIn("实际重量", fields[3][2][0])

    def test_wrapped_fields_are_not_dropped(self):
        sizes = dict((field, (values, notes)) for field, values, notes in self.sections[2][1])
        self.assertEqual(sizes["长度"][0], ["160.9 mm"])
        self.assertEqual(sizes["重量"][0], ["约 203 g（含电池）"])
        self.assertIn("实际重量", sizes["重量"][1][0])

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
