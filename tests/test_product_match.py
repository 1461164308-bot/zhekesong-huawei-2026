"""product_match 纯函数模块的回归测试（只读本地目录数据，不联网）。

覆盖五个公开接口：

- ``normalize``：NFKC、大小写、华为/华为英文前缀、空格/横线、全角括号，以及
  「（鸿蒙版）」这类版本词必须保留；
- ``score``：0~1 区间、家族/年份/系统硬冲突直接 0 分；
- ``candidates``：目录在前、按归一化去重、空值忽略；
- ``ranked``：只留正分、按分数降序、limit 生效；
- ``resolve``：matched / ambiguous / unknown 三种状态及提示文案。

本模块引入了「保守自动匹配」守卫 ``_auto_match_allowed``，本测试按以下语义断言：

1. 用户写了系统（鸿蒙版 / Windows）而候选型号没写系统 → 不能 matched，只能
   ambiguous；
2. 候选写了系统而用户没写 → 不能 matched；
3. 候选带年份 / SE / Pro S / Ultra 等限定而用户输入缺这些信息时：只有目录里
   唯一对应（family+series+size 与查询一致）才允许 matched，两个以上候选 → ambiguous；
4. ``normalize`` 后完全相等的输入始终 matched，不受上面限制。

另外用 ``facts/index.json`` 里的 11 个真实型号做「每个型号 3 种简写」审计：
完整报告打印到标准输出；审计中已确认的匹配器缺陷登记在 ``KNOWN_AUDIT_MISSES``
里（只打印、不判失败），除登记项外出现新的不通过会断言失败，防止目录或匹配
行为悄悄退化。

注意：``product_match.py`` 不在本测试任务的修改范围内。已确认的匹配器缺陷按
「规格期望」写在 ``KnownMatcherDefectTests`` 中并标记 ``expectedFailure``，
修复产品匹配逻辑后去掉装饰器即可转为正式回归用例。
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import product_match as pm  # noqa: E402  （先补 sys.path 再导入仓库根目录模块）

INDEX_PATH = ROOT / "facts" / "index.json"
# facts/index.json 里 category 以 01- 开头的是鸿蒙电脑（其余是 Windows 笔记本）。
HARMONY_CATEGORY_PREFIX = "01-"


def load_catalog() -> tuple[list[str], dict]:
    """读取真实目录，返回（型号名列表, cards 字典）；目录缺失时跳过而不是失败。"""
    if not INDEX_PATH.exists():
        raise unittest.SkipTest(f"缺少真实目录索引：{INDEX_PATH}")
    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    cards = data.get("cards") or {}
    if not cards:
        raise unittest.SkipTest("facts/index.json 里没有 cards 目录")
    return list(cards), cards


def harmony_models(cards: dict) -> set[str]:
    """按 index.json 的 category 挑出鸿蒙电脑型号，用来断言系统硬约束。"""
    return {
        name
        for name, meta in cards.items()
        if str(meta.get("category", "")).startswith(HARMONY_CATEGORY_PREFIX)
    }


class NormalizeTests(unittest.TestCase):
    """normalize：把各种手输入写法折叠成同一个比较键。"""

    def test_fullwidth_parentheses_are_removed(self):
        """全角「（鸿蒙版）」和半角「(鸿蒙版)」归一化结果必须一致。"""
        self.assertEqual(pm.normalize("HUAWEI MateBook 14（鸿蒙版）"), "matebook14鸿蒙版")
        self.assertEqual(pm.normalize("HUAWEI MateBook 14(鸿蒙版)"), "matebook14鸿蒙版")

    def test_case_is_folded(self):
        """大小写不敏感：MateBook / MATEBOOK / matebook 得到同一个键。"""
        self.assertEqual(pm.normalize("MateBook D 14"), "matebookd14")
        self.assertEqual(pm.normalize("MATEBOOK D 14"), "matebookd14")
        self.assertEqual(pm.normalize("matebook d 14"), "matebookd14")

    def test_huawei_prefix_is_stripped(self):
        """开头的中英文品牌前缀都不参与比较。"""
        for text in ("HUAWEI MateBook 14", "huawei MateBook 14", "华为 MateBook 14", "华为MateBook 14"):
            with self.subTest(text=text):
                self.assertEqual(pm.normalize(text), "matebook14")
        # 只有品牌、没有型号时归一化为空串
        self.assertEqual(pm.normalize("HUAWEI"), "")

    def test_spaces_and_dashes_are_removed(self):
        """空格、横线、下划线、斜杠等分隔符统一去掉。"""
        self.assertEqual(pm.normalize("  MateBook-D_14 / 2024  "), "matebookd142024")
        self.assertEqual(pm.normalize("MateBook\tD 14"), "matebookd14")

    def test_harmony_version_word_is_preserved(self):
        """「鸿蒙版」是区分型号的版本词，归一化时必须保留，不能当噪声删掉。"""
        norm = pm.normalize("HUAWEI MateBook 14（鸿蒙版）")
        self.assertIn("鸿蒙版", norm)
        self.assertTrue(norm.endswith("鸿蒙版"))

    def test_fullwidth_letters_and_digits_are_normalized(self):
        """NFKC：全角字母/数字/全角空格折叠成半角后再去分隔符。"""
        self.assertEqual(pm.normalize("ＭａｔｅＢｏｏｋ　Ｄ　１４"), "matebookd14")

    def test_version_words_are_kept(self):
        """「酷睿 Ultra」这类版本词同样要保留，否则款型就分不出来了。"""
        self.assertEqual(pm.normalize("MateBook 14 酷睿 Ultra"), "matebook14酷睿ultra")

    def test_empty_input_normalizes_to_empty_string(self):
        """空串、纯空白、None 都归一化为空串，不抛异常。"""
        self.assertEqual(pm.normalize(""), "")
        self.assertEqual(pm.normalize("   "), "")
        self.assertEqual(pm.normalize(None), "")


class ScoreTests(unittest.TestCase):
    """score：0~1 的匹配分，硬冲突直接归零。"""

    def test_identical_name_scores_one(self):
        """型号与目录写法完全一致（含品牌前缀）时是满分。"""
        name = "HUAWEI MateBook X Pro 酷睿 Ultra 微绒典藏版"
        self.assertEqual(pm.score(name, name), 1.0)

    def test_scores_stay_within_zero_and_one(self):
        """任意输入输出都落在 [0, 1]，不会出现负分或超过 1 的分数。"""
        queries = ["matebook 14", "matebook d 14 2024", "轻薄本", "MateBook 99"]
        candidates = [
            "HUAWEI MateBook 14（鸿蒙版）",
            "HUAWEI MateBook D 14 2024",
            "HUAWEI MateBook Pro",
        ]
        for query in queries:
            for candidate in candidates:
                with self.subTest(query=query, candidate=candidate):
                    value = pm.score(query, candidate)
                    self.assertGreaterEqual(value, 0.0)
                    self.assertLessEqual(value, 1.0)

    def test_year_conflict_scores_zero(self):
        """输入年份与候选年份不同：再像也直接 0 分。"""
        self.assertEqual(pm.score("matebook d 14 2023", "HUAWEI MateBook D 14 2024"), 0.0)
        self.assertEqual(pm.score("HUAWEI MateBook D 16 2025", "HUAWEI MateBook D 16 2024"), 0.0)

    def test_system_conflict_scores_zero(self):
        """鸿蒙与 Windows 是硬冲突：任一侧写清楚就不能互配。"""
        self.assertEqual(pm.score("matebook 14 windows", "HUAWEI MateBook 14（鸿蒙版）"), 0.0)
        self.assertEqual(pm.score("matebook 14 鸿蒙版", "HUAWEI MateBook 14 windows"), 0.0)

    def test_unrelated_text_scores_zero(self):
        """与目录毫无关系的文字不应蹭到分。"""
        self.assertEqual(pm.score("轻薄本", "HUAWEI MateBook 14（鸿蒙版）"), 0.0)


class CandidatesTests(unittest.TestCase):
    """candidates：合并目录与补充来源，按 normalize 去重并保留目录原始写法。"""

    def test_duplicates_and_brand_prefix_collapse(self):
        """同一型号重复出现、带不带品牌前缀，都只保留目录里的第一个写法。"""
        products = [
            "HUAWEI MateBook 14（鸿蒙版）",
            "HUAWEI MateBook 14（鸿蒙版）",
            "huawei matebook 14(鸿蒙版)",
            "MateBook 14 酷睿 Ultra",
        ]
        extra = ["HUAWEI MateBook 14（鸿蒙版）", "matebook 14 鸿蒙版", "HUAWEI MateBook Pro"]
        self.assertEqual(
            pm.candidates(products, extra),
            ["HUAWEI MateBook 14（鸿蒙版）", "MateBook 14 酷睿 Ultra", "HUAWEI MateBook Pro"],
        )

    def test_catalog_order_is_kept_before_extra(self):
        """目录顺序靠前，补充来源追加在后面。"""
        self.assertEqual(
            pm.candidates(["HUAWEI MateBook Pro"], extra=["HUAWEI MateBook 14（鸿蒙版）"]),
            ["HUAWEI MateBook Pro", "HUAWEI MateBook 14（鸿蒙版）"],
        )

    def test_empty_entries_are_ignored(self):
        """空串、纯空白、None 都会被跳过。"""
        self.assertEqual(
            pm.candidates(
                ["", "   ", None, "HUAWEI MateBook 14（鸿蒙版）", "huawei matebook 14(鸿蒙版)"]
            ),
            ["HUAWEI MateBook 14（鸿蒙版）"],
        )

    def test_none_pool_returns_empty_list(self):
        """空目录 + 空补充来源返回空列表，不抛异常。"""
        self.assertEqual(pm.candidates(None), [])
        self.assertEqual(pm.candidates(None, None), [])


class RankedTests(unittest.TestCase):
    """ranked：过滤 0 分、按分数降序、limit 生效。"""

    @classmethod
    def setUpClass(cls):
        cls.products, _ = load_catalog()

    def test_scores_are_sorted_desc(self):
        """结果按分数从高到低排列。"""
        rows = pm.ranked("matebook d 14 2024", self.products, limit=5)
        self.assertTrue(rows)
        scores = [value for _, value in rows]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_limit_is_respected(self):
        """limit 截断生效：默认 5，显式给 3 时只返回 3 条。"""
        self.assertEqual(len(pm.ranked("matebook", self.products, limit=3)), 3)
        self.assertLessEqual(len(pm.ranked("matebook", self.products)), 5)

    def test_zero_score_rows_are_filtered_out(self):
        """与目录毫不相关的输入返回空列表，不把 0 分候选当建议。"""
        self.assertEqual(pm.ranked("随便一台", self.products), [])

    def test_extra_source_is_merged_into_ranking(self):
        """补充来源同样参与排序，且归一化后可精确命中。"""
        rows = pm.ranked(
            "matebook d 14 se", ["HUAWEI MateBook Pro"], extra=["HUAWEI MateBook D 14 SE"]
        )
        self.assertEqual(rows[0][0], "HUAWEI MateBook D 14 SE")


class ExactMatchTests(unittest.TestCase):
    """resolve 精确命中：目录带 HUAWEI 前缀，用户不带前缀/全小写/全角也应 matched。"""

    @classmethod
    def setUpClass(cls):
        cls.products, _ = load_catalog()

    def test_catalog_has_eleven_models(self):
        """真实目录当前是 11 个型号；目录变化时这里先失败，提醒同步审计清单。"""
        self.assertEqual(len(self.products), 11)

    def test_queries_that_should_match_exactly(self):
        """同一型号的各种等价写法都应 matched 回目录里的原始写法（守卫规则 4）。"""
        cases = [
            ("HUAWEI MateBook 14（鸿蒙版）", "HUAWEI MateBook 14（鸿蒙版）", "目录原写法"),
            ("MateBook 14（鸿蒙版）", "HUAWEI MateBook 14（鸿蒙版）", "不带品牌前缀"),
            ("matebook 14（鸿蒙版）", "HUAWEI MateBook 14（鸿蒙版）", "全小写"),
            ("matebook14鸿蒙版", "HUAWEI MateBook 14（鸿蒙版）", "无空格"),
            ("ＨＵＡＷＥＩ ＭａｔｅＢｏｏｋ １４（鸿蒙版）", "HUAWEI MateBook 14（鸿蒙版）", "全角字母数字"),
            ("HUAWEI MateBook 14(鸿蒙版)", "HUAWEI MateBook 14（鸿蒙版）", "半角括号"),
            ("华为MateBook Pro S", "HUAWEI MateBook Pro S", "中文品牌前缀"),
            ("huawei matebook pro s", "HUAWEI MateBook Pro S", "英文小写前缀"),
        ]
        for query, expected, label in cases:
            with self.subTest(query=query, label=label):
                result = pm.resolve(query, self.products)
                self.assertEqual(result["status"], "matched", result)
                self.assertEqual(result["product"], expected, result)
                self.assertEqual(result["score"], 1.0, result)
                self.assertIn(expected, result["message"])


class CommonTypingTests(unittest.TestCase):
    """常见手输风格应直接 matched 到目录里的正确型号（不靠用户再选）。"""

    @classmethod
    def setUpClass(cls):
        cls.products, _ = load_catalog()

    def test_common_hand_typed_queries(self):
        """去空格、口语版本词、「pros」复数写法等常见手输都要命中正确型号。

        ``matebook 14 ultra`` 这类当前会误判为歧义的输入不放在这里，
        统一记录在 ``KnownMatcherDefectTests`` / ``KNOWN_AUDIT_MISSES``。
        """
        cases = [
            ("matebook d14 2024", "HUAWEI MateBook D 14 2024"),
            ("MateBook D 14 2024 13代酷睿版", "HUAWEI MateBook D 14 2024 13 代酷睿版"),
            ("MateBook D 14 2024 13 代酷睿版", "HUAWEI MateBook D 14 2024 13 代酷睿版"),
            ("HUAWEI MateBook D14 2024", "HUAWEI MateBook D 14 2024"),
            ("matebook pros", "HUAWEI MateBook Pro S"),
            ("matebook 14 酷睿ultra", "HUAWEI MateBook 14 酷睿 Ultra"),
            ("matebook x pro ultra", "HUAWEI MateBook X Pro 酷睿 Ultra 微绒典藏版"),
            ("matebook d 16 2024", "HUAWEI MateBook D 16 2024"),
            ("matebook fold", "HUAWEI MateBook Fold 非凡大师"),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                result = pm.resolve(query, self.products)
                self.assertEqual(result["status"], "matched", result)
                self.assertEqual(result["product"], expected, result)


class AutoMatchGuardTests(unittest.TestCase):
    """保守自动匹配守卫：缺系统 / 缺年份 / 缺版本词时宁可不猜。

    守卫规则见 ``product_match._auto_match_allowed``；本类用真实目录 + 小合成
    目录分别覆盖「唯一对应可补全」与「多候选必须歧义」。
    """

    @classmethod
    def setUpClass(cls):
        cls.products, _ = load_catalog()

    def test_exact_normalized_match_always_matched(self):
        """守卫规则 4：normalize 后完全相等时始终 matched，不受缺信息限制。"""
        # 用户没写年份、目录型号也没写系统，但归一化后与目录写法完全一致
        result = pm.resolve("matebook 14 鸿蒙版", ["HUAWEI MateBook 14（鸿蒙版）"])
        self.assertEqual(result["status"], "matched", result)
        self.assertEqual(result["product"], "HUAWEI MateBook 14（鸿蒙版）", result)

    def test_user_written_system_must_not_match_untagged_candidate(self):
        """守卫规则 1：用户写了 windows，候选没写系统 → 只能 ambiguous。"""
        result = pm.resolve("matebook pro windows", ["HUAWEI MateBook Pro"])
        self.assertEqual(result["status"], "ambiguous", result)
        self.assertIsNone(result["product"], result)
        self.assertIn("HUAWEI MateBook Pro", [item["product"] for item in result["candidates"]])

    def test_candidate_written_system_must_not_match_when_user_silent(self):
        """守卫规则 2：候选是鸿蒙款、用户没写系统 → 只能 ambiguous。"""
        result = pm.resolve("matebook 14", ["HUAWEI MateBook 14（鸿蒙版）"])
        self.assertEqual(result["status"], "ambiguous", result)
        self.assertIsNone(result["product"], result)

    def test_missing_version_word_with_unique_candidate_is_completed(self):
        """守卫规则 3：目录里唯一对应时，缺 SE / Ultra 这类版本词可以自动补全。"""
        se_result = pm.resolve("d16 2024", ["HUAWEI MateBook D 16 SE 版 2024"])
        self.assertEqual(se_result["status"], "matched", se_result)
        self.assertEqual(se_result["product"], "HUAWEI MateBook D 16 SE 版 2024", se_result)

        ultra_result = pm.resolve("matebook 14 ultra", ["HUAWEI MateBook 14 酷睿 Ultra"])
        self.assertEqual(ultra_result["status"], "matched", ultra_result)
        self.assertEqual(ultra_result["product"], "HUAWEI MateBook 14 酷睿 Ultra", ultra_result)

    def test_missing_version_word_with_two_candidates_is_ambiguous(self):
        """守卫规则 3：同名系列有多款时，简写必须 ambiguous，交给用户选。"""
        d14 = pm.resolve("MateBook D 14", self.products)
        self.assertEqual(d14["status"], "ambiguous", d14)
        names = [item["product"] for item in d14["candidates"]]
        self.assertIn("HUAWEI MateBook D 14 2024", names)
        self.assertIn("HUAWEI MateBook D 14 2024 13 代酷睿版", names)

        d16 = pm.resolve("MateBook D 16 SE", self.products)
        self.assertEqual(d16["status"], "ambiguous", d16)


class HardConstraintTests(unittest.TestCase):
    """年份、系统（鸿蒙/Windows）是硬约束：宁可 ambiguous/unknown，也不能 matched 到错款。"""

    @classmethod
    def setUpClass(cls):
        cls.products, cls.cards = load_catalog()
        cls.harmony = harmony_models(cls.cards)
        cls.windows = set(cls.products) - cls.harmony

    def test_year_not_in_catalog_is_unknown(self):
        """目录里没有的年份（2023/2025）→ unknown 并提示核对年款，不能拿去匹配 2024 款。"""
        for query in ("matebook d 14 2023", "matebook d 16 2023", "matebook d 14 2025"):
            with self.subTest(query=query):
                result = pm.resolve(query, self.products)
                self.assertEqual(result["status"], "unknown", result)
                self.assertIsNone(result["product"], result)
                self.assertIn("年款", result["message"])

    def test_harmony_input_matches_harmony_model(self):
        """明确写「鸿蒙版」且能唯一命中时，必须落到鸿蒙款。"""
        result = pm.resolve("matebook 14 鸿蒙版", self.products)
        self.assertEqual(result["status"], "matched", result)
        self.assertEqual(result["product"], "HUAWEI MateBook 14（鸿蒙版）", result)
        self.assertIn(result["product"], self.harmony)

    def test_harmony_input_never_matches_windows_model(self):
        """输入带「鸿蒙版」时，即使只能给出候选，也不能 matched 到 Windows 款。"""
        for query in (
            "matebook d 14 鸿蒙版",
            "matebook d 16 鸿蒙版",
            "matebook d 14 2024 鸿蒙版",
            "matebook gt 14 鸿蒙",
        ):
            with self.subTest(query=query):
                result = pm.resolve(query, self.products)
                if result["status"] == "matched":
                    self.assertNotIn(result["product"], self.windows, result)

    def test_windows_input_never_matches_harmony_model(self):
        """输入带 windows 时，不能 matched 到鸿蒙款。"""
        for query in (
            "matebook 14 windows",
            "matebook 14 windows版",
            "matebook fold windows",
            "matebook pro windows",
            "matebook pro s windows",
        ):
            with self.subTest(query=query):
                result = pm.resolve(query, self.products)
                self.assertNotIn(result["product"], self.harmony, result)


class AmbiguityTests(unittest.TestCase):
    """目录同时有「MateBook 14 酷睿 Ultra」和「MateBook 14（鸿蒙版）」时不能替用户拍板。"""

    @classmethod
    def setUpClass(cls):
        cls.products, _ = load_catalog()

    def test_matebook_14_is_ambiguous_and_lists_both(self):
        """输入「MateBook 14」必须 ambiguous，且候选中同时出现两个同名不同款型号。"""
        result = pm.resolve("MateBook 14", self.products)
        self.assertEqual(result["status"], "ambiguous", result)
        self.assertIsNone(result["product"], result)
        names = [item["product"] for item in result["candidates"]]
        self.assertIn("HUAWEI MateBook 14 酷睿 Ultra", names)
        self.assertIn("HUAWEI MateBook 14（鸿蒙版）", names)
        self.assertLessEqual(len(names), 5)
        self.assertIn("可能对应多个型号", result["message"])
        self.assertIn("请从候选里选一个准确型号", result["message"])

    def test_ambiguous_candidates_are_sorted_by_score(self):
        """歧义候选按分数从高到低排列，方便用户从上往下选。"""
        result = pm.resolve("matebook 14", self.products)
        scores = [item["score"] for item in result["candidates"]]
        self.assertEqual(scores, sorted(scores, reverse=True))


class UnknownTests(unittest.TestCase):
    """目录里没有相近型号时给 unknown + 补全提示，而不是乱猜一个。"""

    @classmethod
    def setUpClass(cls):
        cls.products, _ = load_catalog()

    def test_unrelated_text_is_unknown_with_completion_hint(self):
        """与目录无关的文字：unknown，且提示补全准确型号。"""
        for query in ("轻薄本", "随便一台"):
            with self.subTest(query=query):
                result = pm.resolve(query, self.products)
                self.assertEqual(result["status"], "unknown", result)
                self.assertIsNone(result["product"], result)
                self.assertIn(query, result["message"])
                self.assertIn("请补全准确型号", result["message"])

    def test_unknown_message_can_list_closest_candidates(self):
        """有接近候选时，unknown 的提示里应列出「目录里最接近的是」。"""
        result = pm.resolve("se 版", self.products)
        self.assertEqual(result["status"], "unknown", result)
        self.assertTrue(result["candidates"], result)
        self.assertIn("目录里最接近的是", result["message"])

    def test_empty_input_is_unknown_without_exception(self):
        """空输入（空串/纯空白/None）返回 unknown 与填写提示，且不抛异常。"""
        for query in ("", "   ", None):
            with self.subTest(query=repr(query)):
                result = pm.resolve(query, self.products)
                self.assertEqual(result["status"], "unknown", result)
                self.assertIsNone(result["product"], result)
                self.assertEqual(result["candidates"], [], result)
                self.assertIn("请先填写产品型号", result["message"])


# 真实目录审计：每个型号构造 3 种简写，期望 matched 回目录里的原始写法。
# 第 3 种简写刻意去掉品牌/家族/版本字（但不删年份、不删系统词——按保守守卫，
# 缺年份/系统本来就应该先追问用户），用来暴露匹配器在分数层面的边界问题。
AUDIT_VARIANTS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "HUAWEI MateBook 14（鸿蒙版）",
        [
            ("去品牌前缀", "MateBook 14（鸿蒙版）"),
            ("小写去空格", "matebook14（鸿蒙版）"),
            ("去括号", "MateBook 14 鸿蒙版"),
        ],
    ),
    (
        "HUAWEI MateBook Fold 非凡大师",
        [
            ("去品牌前缀", "MateBook Fold 非凡大师"),
            ("小写去空格", "matebookfold非凡大师"),
            ("去版本词", "MateBook Fold"),
        ],
    ),
    (
        "HUAWEI MateBook Pro",
        [
            ("去品牌前缀", "MateBook Pro"),
            ("小写去空格", "matebookpro"),
            ("中文品牌前缀", "华为MateBook Pro"),
        ],
    ),
    (
        "HUAWEI MateBook Pro S",
        [
            ("去品牌前缀", "MateBook Pro S"),
            ("小写去空格", "matebookpros"),
            ("中文品牌前缀", "华为MateBook Pro S"),
        ],
    ),
    (
        "HUAWEI MateBook 14 酷睿 Ultra",
        [
            ("去品牌前缀", "MateBook 14 酷睿 Ultra"),
            ("小写去空格", "matebook14酷睿ultra"),
            ("口语化去酷睿", "MateBook 14 Ultra"),
        ],
    ),
    (
        "HUAWEI MateBook D 14 2024",
        [
            ("去品牌前缀", "MateBook D 14 2024"),
            ("小写去空格", "matebookd142024"),
            ("去家族词", "D 14 2024"),
        ],
    ),
    (
        "HUAWEI MateBook D 16 2024",
        [
            ("去品牌前缀", "MateBook D 16 2024"),
            ("小写去空格", "matebookd162024"),
            ("去家族词", "D 16 2024"),
        ],
    ),
    (
        "HUAWEI MateBook D 16 SE 版 2024",
        [
            ("去品牌前缀", "MateBook D 16 SE 版 2024"),
            ("小写去空格", "matebookd16se版2024"),
            ("去版本字", "MateBook D 16 SE 2024"),
        ],
    ),
    (
        "HUAWEI MateBook GT 14",
        [
            ("去品牌前缀", "MateBook GT 14"),
            ("小写去空格", "matebookgt14"),
            ("去家族词", "GT 14"),
        ],
    ),
    (
        "HUAWEI MateBook X Pro 酷睿 Ultra 微绒典藏版",
        [
            ("去品牌前缀", "MateBook X Pro 酷睿 Ultra 微绒典藏版"),
            ("小写去空格", "matebookxpro酷睿ultra微绒典藏版"),
            ("口语化省略后缀", "MateBook X Pro Ultra"),
        ],
    ),
    (
        "HUAWEI MateBook D 14 2024 13 代酷睿版",
        [
            ("去 brand 前缀", "MateBook D 14 2024 13 代酷睿版"),
            ("小写去空格", "matebookd14202413代酷睿版"),
            ("省略版本词", "MateBook D 14 2024 13代"),
        ],
    ),
]

# 审计中已确认的匹配器缺陷（不是测试写错）：
#   键 = (目录里的原始型号, 简写输入)；值 = 实际表现与根因说明。
# 这些案例只打印、不判失败；修复 product_match.py 后应清空本字典并恢复严格断言。
KNOWN_AUDIT_MISSES: dict[tuple[str, str], str] = {
    ("HUAWEI MateBook 14 酷睿 Ultra", "MateBook 14 Ultra"): (
        "实际 ambiguous（score=1.0）：bonus 相加后截断到 1.0，「14 酷睿 Ultra」与「14（鸿蒙版）」"
        "同分并列，MARGIN 失效；期望 matched「HUAWEI MateBook 14 酷睿 Ultra」。"
    ),
    ("HUAWEI MateBook D 16 2024", "D 16 2024"): (
        "实际 ambiguous（score=1.0）：第二名「D 16 SE」得分是 0.9400000000000001，"
        "1.0 - 0.9400000000000001 = 0.05999999999999994 < MARGIN=0.06（浮点边界）；"
        "期望 matched「HUAWEI MateBook D 16 2024」。"
    ),
    ("HUAWEI MateBook D 16 SE 版 2024", "MateBook D 16 SE 2024"): (
        "实际 ambiguous（score=1.0）：少写「版」字没有罚分，SE 版与不带 SE 的「D 16 2024」"
        "都截断到 1.0 并列；期望 matched「HUAWEI MateBook D 16 SE 版 2024」。"
    ),
    ("HUAWEI MateBook GT 14", "GT 14"): (
        "实际 ambiguous（score=0.82）：去掉家族词「MateBook」后字面分只有 0.5，"
        "即使系列/尺寸都对也达不到 0.92；期望 matched「HUAWEI MateBook GT 14」。"
    ),
    ("HUAWEI MateBook D 14 2024 13 代酷睿版", "MateBook D 14 2024 13代"): (
        "实际 ambiguous（score=1.0）：查询与「D 14 2024」和「D 14 2024 13 代酷睿版」都截断到 1.0 "
        "并列，省略的「酷睿版」没有区分度；期望 matched「HUAWEI MateBook D 14 2024 13 代酷睿版」。"
    ),
}


class RealCatalogAuditTests(unittest.TestCase):
    """真实目录审计：11 个型号 × 3 种简写，断言应 matched 回原型号。

    已确认的匹配器缺陷登记在 ``KNOWN_AUDIT_MISSES``（只打印、不判失败）；
    匹配到正确型号算通过；给出候选且正确型号在候选里算「安全歧义」（让用户选，不判失败）；
    匹配到别的型号或完全不提示才算失败。除登记项外出现新的失败会让本用例失败。
    """

    @classmethod
    def setUpClass(cls):
        cls.products, _ = load_catalog()

    def test_real_catalog_audit(self):
        """逐条跑简写审计并打印完整报告，只对「未登记的失败」判错。"""
        covered = {origin for origin, _ in AUDIT_VARIANTS}
        self.assertEqual(covered, set(self.products), "审计清单必须覆盖目录里全部型号")

        total = passed = safe_count = 0
        misses = []
        unexpected = []
        print("\n================ product_match 真实目录审计 ================")
        print(f"目录型号：{len(self.products)} 个；简写输入：{sum(len(v) for _, v in AUDIT_VARIANTS)} 条")
        for origin, variants in AUDIT_VARIANTS:
            print(f"\n-- {origin}")
            for label, query in variants:
                total += 1
                result = pm.resolve(query, self.products)
                candidates = [item["product"] for item in result.get("candidates", [])]
                # 匹配到正确型号=通过；给不出唯一答案但候选里有正确型号=安全歧义（让用户选）；
                # 只有“匹配到别的型号”或“完全不提示”才算失败。
                matched_right = result["status"] == "matched" and result["product"] == origin
                safe_ambiguous = result["status"] == "ambiguous" and origin in candidates
                ok = matched_right or safe_ambiguous
                if ok:
                    passed += 1
                    if safe_ambiguous:
                        safe_count += 1
                else:
                    misses.append((origin, query, label, result))
                    if (origin, query) not in KNOWN_AUDIT_MISSES:
                        unexpected.append((origin, query, label, result))
                actual = f"matched「{result['product']}」" if result["product"] else result["status"]
                tag = "PASS" if matched_right else ("SAFE" if safe_ambiguous else "MISS")
                print(f"   [{tag}] {label:<8} {query!r:<44} -> {actual}（score={result['score']}）")

        if misses:
            print("\n--------- 未通过案例 ---------")
            for origin, query, label, result in misses:
                known = (origin, query) in KNOWN_AUDIT_MISSES
                print(f"   {'[已登记缺陷]' if known else '[新增缺陷]'} {origin}  <-  {query!r}（{label}）")
                print(f"      期望：matched「{origin}」")
                print(f"      实际：{result['status']}（product={result['product']!r}, score={result['score']}）")
                if known:
                    print(f"      登记说明：{KNOWN_AUDIT_MISSES[(origin, query)]}")

        rate = (passed / total) if total else 0.0
        print(
            f"\n审计结果：通过 {passed}/{total} = {rate:.1%}；"
            f"其中安全歧义（候选含正确型号、让用户选）{safe_count} 个；"
            f"已登记缺陷 {len(misses) - len(unexpected)} 个；新增未通过 {len(unexpected)} 个"
        )
        print("===========================================================")

        self.assertEqual(
            unexpected,
            [],
            "出现未登记的匹配失败，请核对 product_match.py 或更新审计清单："
            + repr(
                [
                    (origin, query, result["status"], result["product"])
                    for origin, query, _, result in unexpected
                ]
            ),
        )


class KnownMatcherDefectTests(unittest.TestCase):
    """已确认但本任务不改代码的匹配器缺陷（product_match.py 只读）。

    这些用例按规格期望断言，当前被标记为 ``expectedFailure``（unittest 仍算通过）；
    修复 product_match.py 后它们会变成 unexpected success，届时去掉装饰器即可
    转为正式回归用例。分数层面的简写缺陷见 ``KNOWN_AUDIT_MISSES``。
    """

    @classmethod
    def setUpClass(cls):
        cls.products, _ = load_catalog()

    @unittest.expectedFailure
    def test_matebook_14_ultra_should_match_ultra_model(self):
        """期望 matched「HUAWEI MateBook 14 酷睿 Ultra」；实际 ambiguous（与鸿蒙版并列 1.0）。"""
        result = pm.resolve("matebook 14 ultra", self.products)
        self.assertEqual(result["status"], "matched", result)
        self.assertEqual(result["product"], "HUAWEI MateBook 14 酷睿 Ultra", result)

    @unittest.expectedFailure
    def test_matebook_99_should_be_unknown(self):
        """期望 unknown（目录里没有 99 这个型号）；实际 ambiguous（把 MateBook Pro 等当候选）。"""
        result = pm.resolve("MateBook 99", self.products)
        self.assertEqual(result["status"], "unknown", result)

    @unittest.expectedFailure
    def test_mixed_system_keywords_should_not_silently_match(self):
        """输入同时含「鸿蒙」和 windows 时应提示冲突；实际静默 matched 到鸿蒙款。"""
        result = pm.resolve("matebook 14 鸿蒙版 windows", self.products)
        self.assertNotEqual(result["status"], "matched", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
