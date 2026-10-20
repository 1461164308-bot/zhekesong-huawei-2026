"""快发模式的组合、去重与安全闸测试；不依赖模型、网络或真实知识库。"""
from __future__ import annotations

import unittest
from pathlib import Path

import quick_flow
from quick_flow import PLATFORMS, check_visit, generate, generate_all, limits, similarity

VISIT_A = "上午有位老师来问，上网课能不能一边记笔记一边投到教室大屏。"
VISIT_B = "下班前有对夫妻来看电脑，说孩子的旧机器开个大表格要等很久。"
VISIT_C = "刚给一位做短视频的顾客演示完，他最在意剪素材时屏幕颜色准不准。"


def card(*, missing: tuple[str, ...] = ()) -> dict:
    """A small fact card shaped exactly like ``facts.parse_card`` output."""
    rows = {
        "尺寸与重量": [("重量", "约 1.33 kg", "圆键盘含电池", "实际机身重量根据配置不同可能有所差异。")],
        "屏幕": [("尺寸", "14.2 英寸", "", "显示屏采用圆角设计，实际可视区域略小。"),
                 ("类型", "OLED", "", "")],
        "电池": [("容量", "70 Wh", "额定容量", "")],
        "处理器": [("", "麒麟 X90", "", "")],
        "存储": [("", "512 GB / 1 TB", "", "")],
        "内存": [("", "24 GB / 32 GB", "", "")],
    }
    fields = []
    for section, entries in rows.items():
        for name, text, inline, condition in entries:
            if name == "尺寸" and "重量" in missing:
                continue
            if name == "重量" and "重量" in missing:
                continue
            fields.append({
                "section": section,
                "name": name,
                "values": [{"text": text, "variant": "", "label": "", "inline": inline,
                            "conditions": [condition] if condition else []}],
                "conditions": [condition] if condition else [],
                "quote": f"{name or section}\n{text}" + (f"\n*{condition}" if condition else ""),
            })
    return {"version": 1, "model": "HUAWEI 测试本", "folder": "测试本", "category": "01-鸿蒙电脑",
            "library": "测试库", "captured": "2026-10-20", "urls": ["https://consumer.huawei.com/cn/"],
            "positioning": "", "selling_titles": [], "source_note": "", "fields": fields}


class LimitsTest(unittest.TestCase):
    def test_reads_policy_targets(self) -> None:
        self.assertEqual(limits("门店朋友圈"), (80, 180))
        self.assertEqual(limits("小红书"), (350, 650))
        self.assertEqual(limits("微信公众号"), (650, 1000))


class VisitGateTest(unittest.TestCase):
    def test_blocks_price_and_superlative(self) -> None:
        self.assertTrue(check_visit("今天全网最低价，到手价 3999 元"))
        self.assertTrue(check_visit("这台我用了三天，亲测很好"))

    def test_allows_plain_shop_moment(self) -> None:
        self.assertEqual(check_visit(VISIT_A), [])


class GenerateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.card = card()

    def test_three_platforms_ready_without_model(self) -> None:
        for platform in PLATFORMS:
            result = generate(self.card, audience="教师", platform=platform, visit=VISIT_A, seed=7)
            self.assertEqual(result["status"], "ready", f"{platform} 应通过安全闸：{result['checks']}")
            self.assertTrue(result["text"].strip(), f"{platform} 成稿不能为空")
            self.assertNotIn("{", result["text"], f"{platform} 有余留槽位")
            self.assertNotIn("}", result["text"], f"{platform} 有余留槽位")

    def test_every_number_comes_from_a_fact(self) -> None:
        result = generate(self.card, audience="教师", platform="小红书", visit=VISIT_A, seed=11)
        known = {value["text"] for field in self.card["fields"] for value in field["values"]}
        self.assertTrue(result["facts"], "成稿必须记录用到的事实")
        for fact in result["facts"]:
            self.assertIn(fact["text"].split("（")[0], known, "成稿里的值必须来自事实卡")
        self.assertEqual(result["checks"]["violations"], [], f"安全闸不应报错：{result['checks']}")

    def test_conditions_travel_with_the_value(self) -> None:
        result = generate(self.card, audience="商务差旅", platform="门店朋友圈", visit=VISIT_B, seed=3)
        weight = next((fact for fact in result["facts"] if fact["slot"] == "重量"), None)
        if weight:
            self.assertIn("实际机身重量", " ".join(weight["conditions"]) + weight["source"],
                          "带限定条件的值必须能追溯到条件")

    def test_three_stores_get_clearly_different_drafts(self) -> None:
        stores = [
            {"name": "中山路体验店", "city": "杭州"},
            {"name": "高新店", "city": "西安"},
            {"name": "万象城店", "city": "成都"},
        ]
        visits = [VISIT_A, VISIT_B, VISIT_C]
        drafts = [generate(self.card, audience="教师", platform="小红书", visit=visit,
                           store=store, seed=100 + index)
                  for index, (store, visit) in enumerate(zip(stores, visits))]
        for draft in drafts:
            self.assertEqual(draft["status"], "ready", draft["checks"])
        for left in range(len(drafts)):
            for right in range(left + 1, len(drafts)):
                score = similarity(drafts[left]["text"], drafts[right]["text"])
                self.assertLess(score, 0.7, f"两家门店的稿子太像（{score}）")

    def test_missing_fact_drops_the_sentence_instead_of_leaving_a_hole(self) -> None:
        thin = card(missing=("重量",))
        result = generate(thin, audience="教师", platform="门店朋友圈", visit=VISIT_A, seed=5)
        self.assertNotIn("{重量}", result["text"])
        self.assertNotIn("约 1.33 kg", result["text"])
        self.assertNotIn("None", result["text"])

    def test_banned_visit_is_blocked_before_composing(self) -> None:
        result = generate(self.card, audience="教师", platform="小红书", visit="今天全网最低，闭眼入", seed=2)
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["checks"]["violations"])

    def test_generate_all_returns_every_platform(self) -> None:
        results = generate_all(self.card, audience="学生", visit=VISIT_A, store={"name": "测试店", "city": "南京"}, seed=9)
        self.assertEqual(set(results), set(PLATFORMS))


class DedupTest(unittest.TestCase):
    def test_recent_fragments_are_penalised(self) -> None:
        current = card()
        first = generate(current, audience="教师", platform="小红书", visit=VISIT_A, seed=21)
        self.assertEqual(first["status"], "ready", first["checks"])
        record = {"fragments": first["fragments"], "drafts": [{"text": first["text"], "time": 0}]}
        second = generate(current, audience="教师", platform="小红书", visit=VISIT_A, seed=21, history=record)
        overlap = set(first["fragments"]) & set(second["fragments"])
        self.assertLess(len(overlap), len(first["fragments"]), "换一批后不应原样复用全部片段")
        self.assertLessEqual(second["checks"]["similarity"], quick_flow.SIMILARITY_LIMIT)


class ImageSelectionTest(unittest.TestCase):
    """配图：张数按平台规则走，图不够就少给，路径必须真实存在。"""

    def setUp(self) -> None:
        import facts

        self.facts = facts
        model = next((name for name in facts.catalogue() if facts.images(facts.load_card(name))), None)
        if not model:
            self.skipTest("本机没有授权知识库图片（源目录缺失），跳过配图测试")
        self.card = facts.load_card(model)
        self.available = facts.images(self.card)

    def test_each_platform_stays_within_its_image_limits(self) -> None:
        for platform in PLATFORMS:
            result = generate(self.card, audience="教师", platform=platform, visit=VISIT_A, seed=5)
            low, high = quick_flow.image_limits(platform)
            count = len(result["images"])
            self.assertLessEqual(count, high, f"{platform} 配图超过平台上限")
            self.assertGreaterEqual(count, min(low, len(self.available)),
                                    f"{platform} 配图少于平台下限（可用 {len(self.available)} 张）")
            for item in result["images"]:
                self.assertTrue(Path(item["path"]).is_file(), "配图路径必须真实存在")

    def test_generate_all_reports_image_targets(self) -> None:
        results = generate_all(self.card, audience="教师", visit=VISIT_A, seed=9)
        for platform, result in results.items():
            checks = result["checks"]
            self.assertEqual(checks["image_target"], quick_flow.image_limits(platform))
            self.assertEqual(checks["image_count"], len(result["images"]))


class VisitPresetTest(unittest.TestCase):
    """见闻预选卡：点一下就能用，文案本身不能违规、人群必须合法。"""

    def test_presets_cover_every_audience_and_pass_the_gate(self) -> None:
        import sentence_library

        presets = quick_flow.VISIT_PRESETS
        self.assertGreaterEqual(len(presets), 8, "常见门店场景至少给 8 个，店员才不用自己想")
        audiences = {preset["audience"] for preset in presets}
        self.assertLessEqual(audiences, set(sentence_library.AUDIENCES), "预选卡人群必须是句库支持的人群")
        self.assertGreaterEqual(len(audiences), 5, "人群覆盖要够，前三个平台人群都得能点到")
        for preset in presets:
            with self.subTest(label=preset["label"]):
                self.assertTrue(preset["visit"].strip(), "预选卡不能是空话术")
                self.assertLessEqual(len(preset["label"]), 7, "手机上按钮标签要短")
                self.assertEqual(check_visit(preset["visit"]), [],
                                 f"预选卡「{preset['label']}」自己就过不了安全闸")

    def test_preset_labels_are_unique(self) -> None:
        labels = [preset["label"] for preset in quick_flow.VISIT_PRESETS]
        self.assertEqual(len(labels), len(set(labels)), "预选卡标签不要重复")

    def test_preset_visit_generates_a_ready_draft(self) -> None:
        preset = quick_flow.VISIT_PRESETS[0]
        result = generate(card(), audience=preset["audience"], platform="小红书",
                          visit=preset["visit"], seed=3)
        self.assertEqual(result["status"], "ready", result["checks"])


if __name__ == "__main__":
    unittest.main()
