"""事实卡解析回归测试：只用内联 markdown 夹具，不依赖外部知识库。

真实的 P1 知识库可能不在开发机上，所以解析用例全部自造原文；
只有最后的集成用例会读已生成的卡片，目录缺失时 ``skipTest`` 而不是失败。
"""
from __future__ import annotations

import unittest
from pathlib import Path

import facts

PROBE_DIR = Path(__file__).resolve().parent.parent / ".local" / "facts-probe"


def parse(markdown: str) -> dict:
    """按 build_facts 的调用方式解析一段原文。"""
    return facts.parse_card(markdown, folder="Demo", category="01-鸿蒙电脑", library="测试库")


def field(card: dict, section: str, name: str = "") -> dict:
    """按 <section|name> 取字段；取不到时把现有字段列进断言消息。"""
    for item in card.get("fields", []):
        if item["section"] == section and item["name"] == name:
            return item
    existing = [(item["section"], item["name"]) for item in card.get("fields", [])]
    raise AssertionError(f"未找到字段 <{section}|{name}>，卡片实际字段为：{existing}")


CARD = """# HUAWEI MateBook Demo - 产品事实

> 来源：华为官网规格页。抓取日期：2026-10-17。配置可能因销售版本而异，生成内容时必须保留限定条件。

## 来源

- 产品页：https://consumer.huawei.com/cn/demo/
- 规格页：https://consumer.huawei.com/cn/demo/specs/

## 官方规格摘录

这句摘录说明不应成为任何字段或值。

## 尺寸与重量

重量

约 1.33 kg（圆键盘含电池）

*实际机身重量根据配置、制造工艺、测量方法的不同可能有所差异。

## 屏幕

尺寸

14.2 英寸

*显示屏采用圆角设计，按照标准矩形测量时，屏幕的对角线长度是 14.2 英寸（实际可视区域略小）。

类型

OLED（抗反射屏）

对比度

1000000:1（典型值）

亮度

标准版：

典型亮度：450 nits

柔光版：

典型亮度：500 nits

## 电池

材料

容量

54 Wh（额定容量）

## 处理器

麒麟 X90

## 存储

1 TB / 512 GB

## 接口

USB-C × 1

USB-A 3.2 Gen 1 × 2（右侧）

HDMI × 1
"""


class ParseCardTests(unittest.TestCase):
    """``facts.parse_card``：标签与值配对、条件归属、变体归属。"""

    def setUp(self):
        self.card = parse(CARD)

    def test_card_metadata_is_kept(self):
        self.assertEqual(self.card["model"], "HUAWEI MateBook Demo", "H1 标题去掉「- 产品事实」后应作为型号")
        self.assertEqual(self.card["folder"], "Demo", "文件夹名应原样写进卡片")
        self.assertEqual(self.card["category"], "01-鸿蒙电脑", "分类名应原样写进卡片")
        self.assertEqual(self.card["library"], "测试库", "知识库名应原样写进卡片")
        self.assertEqual(self.card["captured"], "2026-10-17", "抓取日期应从引言块取到")
        self.assertEqual(self.card["urls"], ["https://consumer.huawei.com/cn/demo/",
                                             "https://consumer.huawei.com/cn/demo/specs/"],
                         "来源段的 URL 应按出现顺序去重后写入卡片")

    def test_fields_pair_labels_with_the_values_under_them(self):
        weight = field(self.card, "尺寸与重量", "重量")
        self.assertEqual([value["text"] for value in weight["values"]], ["约 1.33 kg"],
                         "重量字段应当只拿到自己那一行的值")
        screen_size = field(self.card, "屏幕", "尺寸")
        self.assertEqual([value["text"] for value in screen_size["values"]], ["14.2 英寸"],
                         "屏幕尺寸不应串入相邻字段的值")
        screen_type = field(self.card, "屏幕", "类型")
        self.assertEqual([value["text"] for value in screen_type["values"]], ["OLED"],
                         "类型字段的值应当是 OLED，而不是下一段的内容")

    def test_document_sections_never_become_fields(self):
        sections = {item["section"] for item in self.card["fields"]}
        self.assertEqual(sections & {"来源", "官方规格摘录"}, set(),
                         "来源与官方规格摘录是文档段，不应产生字段")
        texts = [value["text"] for item in self.card["fields"] for value in item["values"]]
        self.assertNotIn("这句摘录说明不应成为任何字段或值。", texts, "摘录段正文不应进入值列表")

    def test_star_caveats_land_in_conditions(self):
        weight = field(self.card, "尺寸与重量", "重量")
        self.assertEqual(len(weight["conditions"]), 1, "以 * 开头的限定说明应成为该字段的一条条件")
        self.assertIn("实际机身重量根据配置", weight["conditions"][0], "条件应保留官方原文的措辞")
        self.assertEqual(weight["values"][0]["conditions"], weight["conditions"],
                         "字段级条件必须随值一起下发，供快发模式连条件使用")
        self.assertNotIn("*", weight["values"][0]["text"], "限定说明不应混进值文本")

    def test_rounded_corner_caveat_stays_with_the_screen_size(self):
        screen_size = field(self.card, "屏幕", "尺寸")
        self.assertEqual(len(screen_size["conditions"]), 1, "屏幕尺寸必须保留圆角设计/标准矩形说明")
        self.assertIn("圆角设计", screen_size["conditions"][0], "圆角说明应完整进入条件")
        self.assertIn("标准矩形", screen_size["conditions"][0], "标准矩形说明应完整进入条件")
        self.assertTrue(screen_size["values"][0]["conditions"], "屏幕尺寸的值必须带上这条条件")

    def test_inline_parenthesised_condition_is_split_out_of_the_value(self):
        weight = field(self.card, "尺寸与重量", "重量")["values"][0]
        self.assertEqual(weight["text"], "约 1.33 kg", "行内括号条件应从值文本里剥离")
        self.assertEqual(weight["inline"], "圆键盘含电池", "括号里的条件应写进 inline 而不是丢弃")
        screen_type = field(self.card, "屏幕", "类型")["values"][0]
        self.assertEqual((screen_type["text"], screen_type["inline"]), ("OLED", "抗反射屏"),
                         "类型后面的括号说明同样应成为行内条件")

    def test_colon_number_is_a_value_not_a_field_name(self):
        contrast = field(self.card, "屏幕", "对比度")
        self.assertEqual([value["text"] for value in contrast["values"]], ["1000000:1"],
                         "1000000:1 这类带冒号的数值必须是值")
        self.assertEqual(contrast["values"][0]["inline"], "典型值", "（典型值）应成为行内条件")
        self.assertNotIn("1000000", [item["name"] for item in self.card["fields"]],
                         "数值不能被当成字段名")

    def test_variant_labels_belong_to_the_values_below_them(self):
        brightness = field(self.card, "屏幕", "亮度")
        pairs = [(value["text"], value["label"], value["variant"]) for value in brightness["values"]]
        self.assertEqual(pairs, [("450 nits", "典型亮度", "标准版"),
                                 ("500 nits", "典型亮度", "柔光版")],
                         "标准版/柔光版的亮度必须归到各自的 variant，不能错位或合并")

    def test_empty_field_is_dropped(self):
        names = [item["name"] for item in self.card["fields"]]
        self.assertNotIn("材料", names, "没有值的字段（材料）应被丢弃，而不是留一张空卡")
        self.assertTrue(all(item["values"] for item in self.card["fields"]),
                        "卡片里不应存在 values 为空的字段")
        battery = field(self.card, "电池", "容量")
        self.assertEqual(battery["values"][0]["text"], "54 Wh", "空值字段丢弃不应影响后面的容量字段")
        self.assertEqual(battery["values"][0]["inline"], "额定容量", "电池容量必须带上额定容量说明")


class ResolveTests(unittest.TestCase):
    """``facts.resolve``：别名命中、缺失返回 None、多值取舍、槽位名归一。"""

    def setUp(self):
        self.card = parse(CARD)

    def test_alias_finds_the_weight_field_of_its_section(self):
        found = facts.resolve(self.card, "重量")
        self.assertIsNotNone(found, "重量槽位应通过「尺寸与重量|重量」别名命中")
        self.assertEqual((found["section"], found["name"]), ("尺寸与重量", "重量"),
                         "命中的字段应是尺寸与重量段下的重量")
        self.assertEqual(found["raw"], "约 1.33 kg", "raw 保留不带条件的值文本")
        self.assertEqual(found["text"], "约 1.33 kg（圆键盘含电池）", "text 才是可直接填槽位的渲染结果")
        self.assertEqual(found["conditions"], ["实际机身重量根据配置、制造工艺、测量方法的不同可能有所差异。"],
                         "resolve 必须把限定条件一起带出来")
        self.assertTrue(found["source"], "resolve 应附带原文引文，便于人工确认")
        self.assertEqual(found["url"], "https://consumer.huawei.com/cn/demo/", "resolve 应带上来源 URL")

    def test_missing_slots_return_none_instead_of_guessing(self):
        self.assertIsNone(facts.resolve(self.card, "充电"), "卡片没有充电字段时槽位必须是 None")
        self.assertIsNone(facts.resolve(self.card, "防尘抗水"), "卡片没有防尘抗水字段时槽位必须是 None")
        self.assertIsNone(facts.resolve(self.card, "不存在的槽位"), "未知槽位名应返回 None，不能抛异常")

    def test_connector_section_becomes_a_short_summary_slot(self):
        """接口的卖点是「有哪几类口」，前端拿到的是短摘要而不是那一整段清单。"""
        summary = facts.resolve(self.card, "接口")
        self.assertIsNotNone(summary, "接口应可用：先汇总成短摘要，再进句子")
        self.assertIn("USB-C", summary["text"], "摘要里应出现主要接口类型")
        self.assertLessEqual(len(summary["text"]), 24, "摘要要短到能直接嵌进一句话")
        self.assertNotIn("\n", summary["text"], "摘要不能带换行")

    def test_section_level_field_keeps_its_most_informative_value(self):
        card = parse("""## 操作系统

Linux V20 版

Windows 11 家庭版
""")
        found = facts.resolve(card, "操作系统")
        self.assertIsNotNone(found, "操作系统是无名字段，槽位名与 section 同名时应能命中")
        self.assertEqual(found["raw"], "Windows 11 家庭版",
                         "多值的 section 级字段应按槽位偏好与信息量挑一条，而不是永远取第一条")
        self.assertEqual(found["text"], "Windows 11 家庭版", "没有条件时渲染结果与值文本一致")

    def test_fullwidth_parentheses_in_slot_names_are_normalized(self):
        card = parse("""## 存储

机身内存（ROM）

1 TB

运行内存（RAM）

16 GB
""")
        storage = facts.resolve(card, "存储")
        self.assertIsNotNone(storage, "别名里的全角括号（机身内存（ROM））应能匹配归一后的字段名")
        self.assertEqual(storage["raw"], "1 TB", "存储槽位应取机身内存（ROM）的值")
        memory = facts.resolve(card, "内存")
        self.assertIsNotNone(memory, "内存槽位应回退到「存储|运行内存（RAM）」别名")
        self.assertEqual(memory["raw"], "16 GB", "内存槽位应取运行内存（RAM）的值")


class DisplayTests(unittest.TestCase):
    """``facts.display``：带条件的值必须渲染出条件。"""

    def test_inline_condition_is_rendered_in_parentheses(self):
        value = {"text": "约 1.33 kg", "variant": "", "label": "", "inline": "圆键盘含电池",
                 "conditions": []}
        self.assertEqual(facts.display(value), "约 1.33 kg（圆键盘含电池）",
                         "行内条件应渲染成全角括号跟在值后面")

    def test_label_and_variant_are_rendered(self):
        value = {"text": "450 nits", "variant": "标准版", "label": "典型亮度", "inline": "",
                 "conditions": []}
        self.assertEqual(facts.display(value), "典型亮度 450 nits（标准版）",
                         "小标签应前置，variant 应作为条件渲染")

    def test_condition_already_inside_the_text_is_not_repeated(self):
        value = {"text": "120 Hz（典型值）", "variant": "", "label": "", "inline": "典型值",
                 "conditions": []}
        self.assertEqual(facts.display(value), "120 Hz（典型值）",
                         "值里已经写了的条件不应被重复渲染成两层括号")


class SourceLayoutTests(unittest.TestCase):
    """源文件版式差异（审计发现的三个真实坑，防止解析器退化）。

    笔记本规格表用「高度」表示机身厚度、以「可」开头的标签容易被当成值、
    描述性短语容易被当成字段名——这三处曾导致厚度缺失、对比度被子段吞掉、Fold 屏幕类型丢失。
    """

    def test_thickness_slot_accepts_the_height_label(self):
        """M1：笔记本源文件用「高度」表示机身厚度，厚度槽位应能取到。"""
        card = parse("""## 尺寸与重量

宽度

310.5 mm

深度

231.1 mm

高度

15.3 mm
""")
        found = facts.resolve(card, "厚度")
        self.assertIsNotNone(found, "厚度槽位应当识别「高度」字段，否则 5 张卡的厚度不可用")
        self.assertEqual(found["raw"], "15.3 mm", "厚度槽位取到的应是「高度」那一行的值")

    def test_view_angle_label_is_not_swallowed_as_a_value(self):
        """M2：以「可」开头的字段名被单字前缀判成值，被相邻字段吞掉。"""
        card = parse("""## 屏幕

对比度

1000000:1

可视角度

178°
""")
        names = [item["name"] for item in card["fields"]]
        self.assertIn("可视角度", names, "「可视角度」是字段名，不能被当成对比度的值")
        self.assertNotIn("可视角度", [value["text"] for value in field(card, "屏幕", "对比度")["values"]],
                         "对比度字段的值里不应出现「可视角度」这行标签")

    def test_descriptive_value_is_not_promoted_to_a_field_name(self):
        """M3：描述性短语被当成字段名，屏幕类型槽位因此丢失。"""
        card = parse("""## 屏幕

类型

双层 OLED（柔性显示屏）

UTG 超薄玻璃
""")
        found = facts.resolve(card, "屏幕类型")
        self.assertIsNotNone(found, "「双层 OLED（柔性显示屏）」是值，屏幕类型槽位应当取到它")
        self.assertEqual(found["text"], "双层 OLED（柔性显示屏）",
                         "屏幕类型应取类型那一行的值，括号里的说明随值一起渲染")


class ThicknessGuardTests(unittest.TestCase):
    """厚度槽位的量纲护栏：源文件把机身深度标成厚度时，宁可缺失也不输出错值。"""

    def test_thickness_over_fifty_millimetres_is_rejected(self):
        card = parse("""## 尺寸与重量

长度

15.9 mm

厚度

227.79 mm
""")
        self.assertIsNone(facts.resolve(card, "厚度"),
                          "227.79 mm 是机身深度，厚度槽位必须判为不可用而不是照抄")
        self.assertEqual([value["text"] for value in field(card, "尺寸与重量", "厚度")["values"]],
                         ["227.79 mm"], "可疑的原值仍要留在卡片里，供人工核对")


class FidelityTests(unittest.TestCase):
    """官方符号与全角标点必须原样保留，不能被 NFKC 改写成 TM 或半角逗号。"""

    def test_trademark_and_fullwidth_punctuation_survive(self):
        card = parse("""## 屏幕

分辨率

2880 × 1920，243 PPI

## 处理器

英特尔® 酷睿™ Ultra 7 155H 处理器
""")
        processor = facts.resolve(card, "处理器")
        self.assertIn("™", processor["raw"], "官方原文的 ™ 不能被展开成 TM")
        self.assertNotIn("TM", processor["raw"], "处理器文案里不应出现「酷睿TM」这种改写")
        resolution = facts.resolve(card, "分辨率")
        self.assertIn("，", resolution["text"],
                      "分辨率里的全角逗号必须保留，否则「1200，161」会读成一个数")


class GeneratedCardIntegrationTests(unittest.TestCase):
    """对已生成的事实卡做集成校验；卡片目录不存在时跳过而不是失败。

    ``facts/`` 是应用实际读的目录，``.local/facts-probe`` 是审计复核用的目录；
    两者都存在时都要满足同一组不变量。
    """

    def setUp(self):
        self.indexes = {root: facts.load_index(root)
                        for root in (Path(facts.FACTS_DIR), PROBE_DIR)
                        if (root / facts.INDEX_FILE).is_file()}
        if not self.indexes:
            self.skipTest("未生成事实卡（facts/ 与 .local/facts-probe 都不存在），跳过集成测试")
        if not any(index.get("cards") for index in self.indexes.values()):
            self.skipTest("index.json 没有登记任何卡片，跳过集成测试")

    def test_every_index_entry_loads_its_card(self):
        for root, index in self.indexes.items():
            for model, entry in index["cards"].items():
                with self.subTest(root=root.name, model=model):
                    card = facts.load_card(model, root)
                    self.assertIsNotNone(card, f"{model} 的卡片文件 {entry['file']} 应当可以按索引读回")
                    self.assertEqual(card["model"], model, f"{model} 的卡片 model 应与索引键一致")
                    self.assertTrue(card["fields"], f"{model} 应当至少解析出一个字段")
                    self.assertFalse([item for item in card["fields"] if not item["values"]],
                                     f"{model} 的卡片不应留下没有值的字段")

    def test_resolved_values_stay_inside_their_quoted_source(self):
        for root, index in self.indexes.items():
            for model in index["cards"]:
                card = facts.load_card(model, root)
                repeated = {}
                for item in card["fields"]:
                    key = facts.slot_key(item["section"], item["name"])
                    repeated[key] = repeated.get(key, 0) + 1
                for slot in facts.SLOT_ALIASES:
                    if slot == "接口":
                        # 接口槽位是把端口清单汇总成短摘要，不要求逐字出自引文。
                        continue
                    found = facts.resolve(card, slot)
                    if not found:
                        continue
                    key = facts.slot_key(found["section"], found["name"])
                    if repeated.get(key, 0) > 1:
                        # 同一 section 下重名字段（多 SKU）会合并取值，而引文只指向第一份，
                        # 见 .local/facts-audit.md 的 S7；这条不变量暂不覆盖这类卡片。
                        continue
                    with self.subTest(root=root.name, model=model, slot=slot):
                        self.assertTrue(found["text"], f"{model} 的 {slot} 不应渲染出空文本")
                        # 解析器会把脚注星号（USB-C × 1*）从值里去掉，引文保留原样，
                        # 所以比对时两边都先去掉星号，再要求值逐字出自自己的引文。
                        self.assertIn(found["raw"].replace("*", ""), found["source"].replace("*", ""),
                                      f"{model} 的 {slot} 值必须逐字出现在它自己的原文引文里")

    def test_pc_cards_carry_the_conditions_the_plan_requires(self):
        checked = 0
        for root, index in self.indexes.items():
            pc_cards = [(model, entry) for model, entry in index["cards"].items()
                        if "深度知识库_v7" in (entry.get("library") or "")]
            for model, _ in pc_cards:
                checked += 1
                card = facts.load_card(model, root)
                with self.subTest(root=root.name, model=model, slot="重量"):
                    weight = facts.resolve(card, "重量")
                    self.assertIsNotNone(weight, f"{model} 的重量槽位不应缺失")
                    self.assertTrue(weight["conditions"],
                                    f"{model} 的重量必须带上「实际重量因配置而异」的说明")
                    self.assertRegex(weight["raw"], r"\d\s*(?:kg|g)", f"{model} 的重量值必须带单位")
                with self.subTest(root=root.name, model=model, slot="电池"):
                    battery = facts.resolve(card, "电池")
                    self.assertIsNotNone(battery, f"{model} 的电池槽位不应缺失")
                    self.assertTrue(battery["condition"] or battery["conditions"],
                                    f"{model} 的电池必须带上典型值/额定值说明")
        if not checked:
            self.skipTest("当前事实卡目录里没有 P1 PC 知识库的卡片，跳过")


class ImageSourceTest(unittest.TestCase):
    """配图来源：本地知识库目录，以及部署环境里的私有归档 ZIP。"""

    def setUp(self) -> None:
        import tempfile

        self.temp = Path(tempfile.mkdtemp(prefix="zh-facts-images-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.temp, ignore_errors=True))
        self.root = self.temp / "workspace"
        self.root.mkdir()
        self.original_root = facts.WORKSPACE_ROOT
        facts.WORKSPACE_ROOT = self.root
        facts._IMAGE_CACHE.clear()
        if hasattr(facts, "_ARCHIVE_CACHE"):
            facts._ARCHIVE_CACHE.clear()
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        facts.WORKSPACE_ROOT = self.original_root
        facts._IMAGE_CACHE.clear()
        if hasattr(facts, "_ARCHIVE_CACHE"):
            facts._ARCHIVE_CACHE.clear()

    def _model_folder(self, manifest: str, relative: str) -> Path:
        folder = self.root / "测试库" / "P1-产品参数库" / "04-笔记本" / "测试机型"
        images = folder / "images"
        images.mkdir(parents=True, exist_ok=True)
        (images / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n0")
        (images / "b.jpg").write_bytes(b"\xff\xd8\xff\xe0")
        (folder / manifest).write_text(relative, encoding="utf-8")
        return folder

    def _card(self) -> dict:
        return {"model": "测试机型", "library": "测试库", "category": "04-笔记本", "folder": "测试机型"}

    def test_reads_pc_library_manifest(self) -> None:
        self._model_folder(
            "图片索引.csv",
            "文件名,官网图片说明,建议用途,来源页面,宽度,高度\n"
            "a.png,多彩配色外观,产品介绍配图,https://example.com/spec,800,600\n",
        )
        rows = facts.images(self._card())
        self.assertEqual(len(rows), 1)
        self.assertTrue(Path(rows[0]["path"]).is_file())
        self.assertEqual(rows[0]["placement"], "产品介绍配图")
        self.assertEqual(rows[0]["source_url"], "https://example.com/spec")

    def test_reads_official_library_manifest(self) -> None:
        self._model_folder(
            "images/图片清单.csv",
            '"文件名","说明","来源URL"\n'
            '"a.png","HUAWEI 测试机型 心动理由之屏幕","https://example.com/official"\n'
            '"b.jpg","HUAWEI 测试机型 超级终端",""\n',
        )
        rows = facts.images(self._card())
        self.assertEqual(len(rows), 2, "官方产品库用 images/图片清单.csv，也要读得到")
        self.assertEqual(rows[0]["official"], "HUAWEI 测试机型 心动理由之屏幕")
        self.assertEqual(rows[0]["source_url"], "https://example.com/official")

    def test_extracts_images_from_private_archive(self) -> None:
        """魔搭 Studio 没有本地知识库目录，只能从归档 ZIP 解图到临时目录。"""
        import zipfile

        facts.WORKSPACE_ROOT = self.temp / "empty-workspace"  # 模拟部署环境：没有本地知识库
        archive = self.temp / "knowledge.zip"
        prefix = "P1-产品参数库/04-笔记本/测试机型/"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr(prefix + "images/图片清单.csv",
                            '"文件名","说明","来源URL"\n'
                            '"a.png","HUAWEI 测试机型 心动理由之屏幕","https://example.com/spec"\n')
            bundle.writestr(prefix + "images/a.png", b"\x89PNG\r\n\x1a\n0")
        import knowledge_store

        original = knowledge_store.get_archive_path
        knowledge_store.get_archive_path = lambda: str(archive)
        self.addCleanup(lambda: setattr(knowledge_store, "get_archive_path", original))

        rows = facts.images(self._card())
        self.assertEqual(len(rows), 1, "归档里有的配图要被解出来")
        self.assertTrue(Path(rows[0]["path"]).is_file())
        self.assertTrue(Path(rows[0]["path"]).is_relative_to(facts.ARCHIVE_IMAGE_ROOT),
                        "解压目录必须在系统临时目录（Gradio 才允许读取）")

    def test_archive_without_manifest_returns_nothing(self) -> None:
        import zipfile

        facts.WORKSPACE_ROOT = self.temp / "empty-workspace"
        archive = self.temp / "empty.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("P1-产品参数库/04-笔记本/别的机型/产品事实.md", "# x")
        import knowledge_store

        original = knowledge_store.get_archive_path
        knowledge_store.get_archive_path = lambda: str(archive)
        self.addCleanup(lambda: setattr(knowledge_store, "get_archive_path", original))
        self.assertEqual(facts.images(self._card()), [], "没有清单就不要瞎猜图片")


if __name__ == "__main__":
    unittest.main()
