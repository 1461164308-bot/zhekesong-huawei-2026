"""Deterministic policy regression tests using synthetic evidence only."""
from __future__ import annotations

import unittest

from policy import (PLATFORM_RULES, SCENE_RULES, draft_units, evidence_facts,
                    exact_product, normalized_quote, resolve_product, strategy_for,
                    text_violations, validate_inputs)


PRODUCT = "HUAWEI MateBook Pro S"
YEAR_PRODUCT = "HUAWEI MateBook D 14 2024"
HARMONY_PRODUCT = "HUAWEI MateBook 14（鸿蒙版）"
QUOTE = "屏幕尺寸为14.2英寸，刷新率为120 Hz。实际效果取决于内容与设置。"


def source(kind="facts", text=QUOTE):
    return {"id": "S1", "title": "Synthetic product evidence", "kind": kind, "text": text}


def candidate(statement="屏幕尺寸为14.2英寸，刷新率为120 Hz。", quote=QUOTE, source_id="S1"):
    return {"statement": statement, "quote": quote, "source_id": source_id,
            "conditions": ["以具体版本和设置为准"], "category": "spec"}


class InputPolicyTests(unittest.TestCase):
    def test_exact_model_may_omit_brand_but_not_model_details(self):
        products = [PRODUCT, YEAR_PRODUCT, HARMONY_PRODUCT]
        self.assertEqual(exact_product("MateBook Pro S", products), PRODUCT)
        self.assertEqual(exact_product(PRODUCT.lower(), products), PRODUCT)
        self.assertIsNone(exact_product("MateBook", products))
        self.assertIsNone(exact_product("华为轻薄本", products))
        self.assertIsNone(exact_product("MateBook Pro", products))

    def test_model_year_and_operating_system_cannot_be_substituted(self):
        products = [YEAR_PRODUCT, HARMONY_PRODUCT]
        self.assertIsNone(exact_product("HUAWEI MateBook D 14 2025", products))
        self.assertIsNone(exact_product("HUAWEI MateBook D 14", products))
        self.assertIsNone(exact_product("HUAWEI MateBook 14（Windows版）", products))
        self.assertIsNone(exact_product("HUAWEI MateBook 14", products))

    def test_free_text_model_resolves_only_when_unambiguous(self):
        products = [YEAR_PRODUCT, "HUAWEI MateBook D 14 2024 13 代酷睿版", HARMONY_PRODUCT]
        matched = resolve_product("matebook d 14 2024", products)
        self.assertEqual(matched["status"], "matched")
        self.assertEqual(matched["product"], YEAR_PRODUCT)
        # 带品牌前缀/全角括号的中文写法也能落到目录原写法
        self.assertEqual(resolve_product("华为 MateBook 14（鸿蒙版）", products)["product"], HARMONY_PRODUCT)
        # 目录里有两个 D14 时，缺年份的简写必须当成歧义，不能替用户挑
        ambiguous = resolve_product("matebook d 14", products)
        self.assertEqual(ambiguous["status"], "ambiguous")
        self.assertGreaterEqual(len(ambiguous["candidates"]), 2)
        self.assertIsNone(ambiguous["product"])
        # 年份决定资料归属：即便目录里只有一个 D14，缺年份也要先问
        unique = resolve_product("matebook d 14", [YEAR_PRODUCT])
        self.assertEqual(unique["status"], "ambiguous")
        self.assertIsNone(unique["product"])
        # 泛称/不存在型号 → unknown，并给出补全提示
        unknown = resolve_product("轻薄本", products)
        self.assertEqual(unknown["status"], "unknown")
        self.assertIsNone(unknown["product"])
        self.assertIn("型号", unknown["message"])

    def test_fact_card_name_maps_back_to_catalog_title(self):
        """事实卡叫「HUAWEI MateBook D 14 2024」，知识库目录叫「MateBook D 14」：
        用事实卡名手输也能命中，并折算回目录标题供检索使用。"""
        import facts

        model = next((name for name in facts.catalogue()
                      if "D 14 2024" in name and "13" not in name), None)
        if not model:
            self.skipTest("事实卡里没有 D 14 2024，跳过别名折算检查")
        folder = facts.load_card(model)["folder"]
        products = [folder, "HUAWEI MateBook 14"]
        for query in (model, model.lower(), "matebook d 14 2024"):
            with self.subTest(query=query):
                result = resolve_product(query, products)
                self.assertEqual(result["status"], "matched", result)
                self.assertEqual(result["product"], folder)
                self.assertIn(folder, result["message"])

    def test_free_text_match_keeps_os_and_year_guards(self):
        products = [YEAR_PRODUCT, HARMONY_PRODUCT]
        cross_os = resolve_product("HUAWEI MateBook 14（Windows版）", products)
        self.assertNotEqual(cross_os["status"], "matched")
        future = resolve_product("HUAWEI MateBook D 14 2025", products)
        self.assertEqual(future["status"], "unknown")

    def test_missing_fields_produce_specific_questions(self):
        canonical, questions = validate_inputs("", "", "", "", [PRODUCT])
        self.assertIsNone(canonical)
        self.assertEqual(len(questions), 4)

    def test_complete_valid_task_does_not_need_clarification(self):
        canonical, questions = validate_inputs(PRODUCT, "大学新生", "开学季", "小红书", [PRODUCT])
        self.assertEqual(canonical, PRODUCT)
        self.assertEqual(questions, [])

    def test_platform_and_scene_rules_have_distinct_operating_constraints(self):
        poster = strategy_for("门店顾客", "门店到访", "门店海报", "预约到访")
        moments = strategy_for("门店顾客", "职场办公", "门店朋友圈", "预约到访")
        red = strategy_for("大学新生", "开学季", "小红书", "种草了解")
        self.assertEqual(poster["image_max"], 1)
        self.assertEqual(moments["sections"], 1)
        self.assertTrue(red["tags"])
        self.assertFalse(poster["tags"])
        self.assertNotEqual(red["pain"], moments["pain"])
        self.assertEqual(set(PLATFORM_RULES), {"小红书", "微信公众号", "门店朋友圈", "门店海报"})
        self.assertIn("企业采购", SCENE_RULES)


class EvidencePolicyTests(unittest.TestCase):
    def test_valid_quote_is_located_and_preserves_conditions(self):
        facts, rejected = evidence_facts({"facts": [candidate()]}, [source()])
        self.assertEqual(rejected, [])
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["id"], "F1")
        self.assertEqual(facts[0]["source_id"], "S1")
        self.assertEqual(facts[0]["conditions"], ["以具体版本和设置为准"])

    def test_whitespace_and_fullwidth_typography_are_normalized_not_meaning(self):
        self.assertEqual(normalized_quote("１２０ Hz\n"), "120Hz")
        for typography in ("120\nHz", "１２０\nHz"):
            with self.subTest(typography=typography):
                facts, _ = evidence_facts({"facts": [candidate(quote=QUOTE.replace("120 Hz", typography))]}, [source()])
                self.assertEqual(len(facts), 1)

    def test_paraphrase_cannot_masquerade_as_exact_quote(self):
        facts, rejected = evidence_facts({"facts": [candidate(quote="这块屏幕为14.2英寸且支持120 Hz刷新率。") ]}, [source()])
        self.assertEqual(facts, [])
        self.assertTrue(any("逐字" in reason for reason in rejected))

    def test_missing_source_and_tiny_quote_fail_closed(self):
        for entry in (candidate(source_id="S999"), candidate(quote="屏幕")):
            with self.subTest(entry=entry):
                facts, rejected = evidence_facts({"facts": [entry]}, [source()])
                self.assertEqual(facts, [])
                self.assertTrue(rejected)

    def test_statement_cannot_invent_numbers_absent_from_its_quote(self):
        facts, rejected = evidence_facts({"facts": [candidate(statement="屏幕刷新率为240 Hz。") ]}, [source()])
        self.assertEqual(facts, [])
        self.assertTrue(any("数值" in reason for reason in rejected))

    def test_price_source_is_not_accepted_as_product_fact(self):
        facts, rejected = evidence_facts({"facts": [candidate()]}, [source(kind="price")])
        self.assertEqual(facts, [])
        self.assertTrue(rejected)

    def test_marketing_source_is_not_accepted_as_product_fact(self):
        facts, rejected = evidence_facts({"facts": [candidate()]}, [source(kind="marketing")])
        self.assertEqual(facts, [])
        self.assertTrue(rejected)

    def test_dynamic_price_and_subsidy_are_not_evidence_facts(self):
        for statement in ("售价5999元。", "售价五千元。", "现在八折。", "可享国补。", "支持补贴。", "赠品充足。"):
            with self.subTest(statement=statement):
                facts, rejected = evidence_facts({"facts": [candidate(statement=statement)]}, [source()])
                self.assertEqual(facts, [])
                self.assertTrue(rejected)

    def test_exact_quote_is_necessary_but_not_a_semantic_entailment_proof(self):
        # This deterministic layer intentionally cannot prove entailment. Agent tests
        # require a separate fact-review call before unsupported claims reach compose.
        unsupported = candidate(statement="屏幕支持十点触控。")
        facts, _ = evidence_facts({"facts": [unsupported]}, [source()])
        self.assertEqual(len(facts), 1)


class PublicationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.facts, _ = evidence_facts({"facts": [candidate()]}, [source()])

    def test_supported_screen_values_are_not_invented_numbers(self):
        self.assertEqual(text_violations("屏幕为14.2英寸，刷新率为120 Hz。", self.facts, PRODUCT), [])

    def test_unverified_numeric_value_is_rejected(self):
        self.assertTrue(any("数值" in x for x in text_violations("续航达到99小时。", self.facts, PRODUCT)))

    def test_prices_subsidies_first_person_and_absolute_claims_are_rejected(self):
        statements = ["到手价5999元。", "售价五千元。", "现在八折。", "可享国补。", "买赠品。", "我亲测非常流畅。",
                      "我用了三天。", "全网最低。", "闭眼入。", "绝对安全。", "永不卡顿。"]
        for statement in statements:
            with self.subTest(statement=statement):
                self.assertTrue(text_violations(statement, self.facts, PRODUCT))

    def test_plain_sku_confirmation_advice_is_allowed(self):
        self.assertEqual(text_violations("建议携带常用软件清单，到店确认具体版本。", self.facts, PRODUCT), [])

    def test_draft_units_enforce_platform_section_limit(self):
        strategy = strategy_for("顾客", "门店到访", "门店朋友圈", "预约")
        draft = {"title": "任务清单", "title_fact_ids": ["F1"], "intro": "先确认任务。", "intro_fact_ids": ["F1"], "sections": [
            {"heading": "A", "text": "第一段", "fact_ids": ["F1"]},
            {"heading": "B", "text": "第二段", "fact_ids": ["F1"]}], "cta": "到店咨询。", "cta_fact_ids": ["F1"], "tags": ["#选购"]}
        units = draft_units(draft, strategy)
        self.assertEqual(next(x for x in units if x["id"] == "title")["fact_ids"], ["F1"])
        self.assertEqual(next(x for x in units if x["id"] == "intro")["fact_ids"], ["F1"])
        self.assertEqual(next(x for x in units if x["id"] == "cta")["fact_ids"], ["F1"])
        self.assertEqual(len([x for x in units if x["id"].startswith("section_")]), 1)
        self.assertFalse(any(x["id"] == "tags" for x in units))


class MeasurementPolicyTests(unittest.TestCase):
    def check(self, text, quote):
        return text_violations(text, [{"id": "F1", "quote": quote}], PRODUCT)

    def test_equal_number_in_different_unit_is_not_support(self):
        quote = "重量约798 g到825 g，刷新率120 Hz。"
        for text in ("续航120小时。", "内存120 GB。", "重量约120 g。"):
            with self.subTest(text=text):
                self.assertTrue(any("单位组合" in x for x in self.check(text, quote)))

    def test_product_model_number_is_not_measurement_evidence(self):
        self.assertEqual(text_violations(YEAR_PRODUCT + "选购参考", [], YEAR_PRODUCT), [])
        self.assertTrue(text_violations("续航14小时。", [], YEAR_PRODUCT))

    def test_approximate_range_qualifier_applies_to_both_endpoints(self):
        quote = "重量约798 g到825 g，刷新率120 Hz。"
        for text in ("重量798 g。", "重量825 g。", "重量798 g至825 g。"):
            with self.subTest(text=text):
                self.assertTrue(any("约数" in x for x in self.check(text, quote)))
        for text in ("重量约798 g至825 g。", "重量约825克。", "重量798克左右。"):
            with self.subTest(text=text):
                self.assertEqual(self.check(text, quote), [])

    def test_reversed_or_invented_range_is_rejected(self):
        quote = "重量约798 g到825 g，刷新率120 Hz。"
        self.assertTrue(any("范围及方向" in x for x in self.check("重量约825 g到798 g。", quote)))
        self.assertTrue(self.check("重量约798 kg到825 g。", quote))
        # Separate configurations do not authorize inventing a continuous interval.
        self.assertTrue(self.check("重量约798 g至825 g。", "型号甲约798 g，型号乙约825 g。"))

    def test_upper_bound_cannot_be_dropped_or_borrowed_from_previous_clause(self):
        quote = "视频输出最高支持4K，刷新率120 Hz。"
        for text in ("视频支持4K。", "最高支持120 Hz，视频支持4K。", "最高支持120 Hz。视频支持4K。"):
            with self.subTest(text=text):
                self.assertTrue(any("上限" in x for x in self.check(text, quote)))
        for text in ("视频输出最高支持4K。", "视频输出至多支持4K。", "视频输出不超过4K。", "视频输出4K以内。"):
            with self.subTest(text=text):
                self.assertEqual(self.check(text, quote), [])

    def test_unit_aliases_case_and_fullwidth_text_keep_supported_values(self):
        quote = "屏幕尺寸14.2英寸，刷新率120 Hz，重量约798 g。"
        self.assertEqual(self.check("屏幕为１４．２英寸，刷新率１２０Ｈｚ，重量约７９８克。", quote), [])
        self.assertEqual(self.check("刷新率120赫兹。", quote), [])
        self.assertEqual(self.check("尺寸14.2英寸，刷新率120 Hz。", quote), [])

    def test_exact_measurement_does_not_acquire_unrelated_approximate_qualifier(self):
        quote = "重量约798 g，厚度16 mm，刷新率120 Hz。"
        self.assertEqual(self.check("厚度16毫米，刷新率120 Hz。", quote), [])
        self.assertEqual(self.check("重量约798g和厚度16mm。", quote), [])

    def test_unit_scale_conversion_is_not_inferred(self):
        self.assertTrue(self.check("重量约798 kg。", "重量约798 g。"))
        self.assertTrue(self.check("刷新率120 GHz。", "刷新率120 Hz。"))

    def test_upper_and_approximate_conditions_must_both_survive(self):
        quote = "实验条件下续航最高约12小时。"
        for text in ("续航12小时。", "续航约12小时。", "续航最高12小时。"):
            with self.subTest(text=text):
                self.assertTrue(self.check(text, quote))
        self.assertEqual(self.check("续航最高约12小时。", quote), [])

    def test_exact_support_can_be_used_without_borrowing_another_quote_qualifier(self):
        facts = [{"id": "F1", "quote": "指定配置重量约798 g。"},
                 {"id": "F2", "quote": "另一个已复核的配置重量798 g。"}]
        self.assertEqual(text_violations("重量798 g。", facts, PRODUCT), [])


class StoreDemoUnitTests(unittest.TestCase):
    def setUp(self):
        self.strategy = strategy_for("门店顾客", "门店到访", "门店朋友圈", "预约")
        self.demo = {"action": "请顾客打开自带资料页。", "speech": "按常用任务核对具体版本。",
                     "observe": "请顾客确认阅读是否清楚。", "fact_ids": ["F1"]}

    def test_demo_action_speech_observe_and_references_share_one_auditable_unit(self):
        units = draft_units({"demo_steps": [self.demo]}, self.strategy)
        demo = next(unit for unit in units if unit["id"] == "demo_1")
        self.assertEqual(demo["fact_ids"], ["F1"])
        for field in ("action", "speech", "observe"):
            self.assertEqual(demo[field], self.demo[field])
            self.assertIn(self.demo[field], demo["text"])
        self.assertFalse(any(unit["id"].startswith("section_") for unit in units))

    def test_demo_script_is_bounded_to_three_steps(self):
        units = draft_units({"demo_steps": [self.demo] * 5}, self.strategy)
        self.assertEqual([unit["id"] for unit in units if unit["id"].startswith("demo_")],
                         ["demo_1", "demo_2", "demo_3"])

    def test_demo_without_action_or_speech_is_not_sent_as_complete_script(self):
        incomplete = [{**self.demo, "action": ""}, {**self.demo, "speech": ""}, "invalid"]
        units = draft_units({"demo_steps": incomplete}, self.strategy)
        self.assertFalse(any(unit["id"].startswith("demo_") for unit in units))


if __name__ == "__main__":
    unittest.main()
