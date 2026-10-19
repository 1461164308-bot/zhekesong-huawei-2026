"""Huawei ecosystem product families for the semi-final scope.

The semi-final brief asks for phone / tablet / ecosystem promotion in addition
to the PC line. This module only classifies and lists product names; it never
carries product facts. Facts must still come from an authorised knowledge base
or from an explicitly supplied official Huawei Mall product page.
"""
from __future__ import annotations

import re
import unicodedata

# Curated model names only: enough for the picker and for exact-name matching.
# They deliberately omit prices, specs and marketing claims.
PHONES = [
    "HUAWEI Mate 70 Pro",
    "HUAWEI Mate 70",
    "HUAWEI Pura 70 Pro",
    "HUAWEI Pura 70",
    "HUAWEI Mate X6",
    "HUAWEI nova 13",
]
TABLETS = [
    "HUAWEI MatePad Pro 13.2",
    "HUAWEI MatePad Pro 11",
    "HUAWEI MatePad Air",
    "HUAWEI MatePad 11.5 S",
]
WEARABLES = [
    "HUAWEI WATCH 5",
    "HUAWEI FreeBuds Pro 4",
]

FAMILY_LABELS = {"pc": "PC", "phone": "手机", "tablet": "平板", "wearable": "穿戴", "ecosystem": "生态组合"}

_PC = re.compile(r"matebook|擎云", re.I)
_PHONE = re.compile(r"\bmate\s*[0-9x]|mate\s*x\d|pura|nova|畅享|pocket", re.I)
_TABLET = re.compile(r"matepad|平板", re.I)
_WEARABLE = re.compile(r"watch|freebuds|手环|耳机|手表", re.I)
_COMBO = re.compile(r"[+＋、/,，]|套装|组合|生态|全家桶|一起")


def catalog() -> list[str]:
    """Names available for the picker (PC names come from the authorised KB)."""
    return [*PHONES, *TABLETS, *WEARABLES]


def _norm(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value or ""))).casefold()


def product_family(product: str) -> str:
    """Classify a user-supplied product string.

    A string that names more than one device (e.g. "Mate 70 Pro + MatePad Pro")
    is treated as an ecosystem combination so the copy targets cross-device use.
    """
    text = str(product or "")
    families = set()
    if _PC.search(text):
        families.add("pc")
    if _PHONE.search(text):
        families.add("phone")
    if _TABLET.search(text):
        families.add("tablet")
    if _WEARABLE.search(text):
        families.add("wearable")
    if not families:
        return "pc"
    if len(families) > 1 or _COMBO.search(text.replace("MateBook", "")):
        return "ecosystem"
    return next(iter(families))


def needs_mall_evidence(family: str) -> bool:
    """Non-PC families have no authorised knowledge base in this deployment."""
    return family != "pc"


def family_label(family: str) -> str:
    return FAMILY_LABELS.get(family, "未识别")


def ecosystem_guidance(family: str) -> str:
    """Prompt fragment injected only for ecosystem families."""
    if family == "pc":
        return ""
    if family == "ecosystem":
        return ("本次任务面向华为生态组合（多设备）。写作必须围绕设备之间的协同使用场景展开，"
                "但任何跨设备能力、互联、流转、切换都必须由输入事实直接支持；"
                "不得把生态概念当成无条件功能，也不得替其他机型补写参数。")
    return (f"本次任务面向华为{family_label(family)}产品。写作时可以把该设备放回华为生态的使用场景，"
            "但跨设备协同、互联与配件能力必须由输入事实直接支持，没有依据就只写本机可核验的内容。")


def ecosystem_facts_scope() -> str:
    """Reminder appended to extraction for ecosystem tasks."""
    return ("当产品属于手机/平板/穿戴或生态组合时，只从提供的官方商品页正文提取事实，"
            "不得补充其他机型参数；跨设备协同能力必须有原文依据。")
