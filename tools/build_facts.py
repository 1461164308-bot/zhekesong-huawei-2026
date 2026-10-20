"""Build ``facts/<型号>.json`` from the authorized P1 product facts.

    .venv\\Scripts\\python.exe tools\\build_facts.py [--root facts] [--library 名称] [--check]

The cards are the contractual input of quick publishing (快速发布), so this tool
is deliberately deterministic: same P1 material in, same cards out. Anything the
parser cannot classify is left out of the slots instead of being guessed; the
original quote is kept next to every value for human confirmation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import facts as fact_cards
from knowledge_store import WORKSPACE_ROOT, WORKSPACE_SOURCES, _product_key


def _product_dirs(source: Path) -> list[Path]:
    primary = source / "P1-产品参数库"
    if not primary.is_dir():
        return []
    return sorted(
        folder
        for category in sorted(primary.iterdir()) if category.is_dir()
        for folder in sorted(category.iterdir())
        if folder.is_dir() and (folder / fact_cards.FACT_FILE).is_file()
    )


def collect() -> list[dict]:
    """Every product folder across the authorized sources, first source winning."""
    cards, seen, seen_models, errors = [], set(), set(), []
    for relative in WORKSPACE_SOURCES:
        source = WORKSPACE_ROOT / relative
        if not source.is_dir():
            continue
        library = relative.as_posix()
        for folder in _product_dirs(source):
            key = _product_key(folder.name)
            if key in seen:
                continue
            try:
                card = fact_cards.card_from_file(folder / fact_cards.FACT_FILE, library=library)
            except (OSError, ValueError) as exc:
                errors.append(f"{library}/{folder.name}: {exc}")
                continue
            if not card["fields"]:
                errors.append(f"{library}/{folder.name}: 未解析到任何规格字段")
                continue
            # The first source wins a model that both libraries contain, even
            # when the two files spell the display name slightly differently.
            name_key = _product_key(card["model"])
            if name_key in seen_models:
                continue
            seen.add(key)
            seen_models.add(name_key)
            cards.append(card)
    return cards, errors


def write(cards: list[dict], root: Path) -> dict:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for stale in root.glob("*.json"):
        stale.unlink()
    index = {"generated_by": "tools/build_facts.py", "version": fact_cards.CARD_VERSION, "cards": {}}
    for card in cards:
        target = fact_cards.write_card(card, root)
        index["cards"][card["model"]] = {
            "file": target.name,
            "folder": card["folder"],
            "category": card["category"],
            "library": card["library"],
            "captured": card["captured"],
            "fields": len(card["fields"]),
            "slots": [slot for slot in fact_cards.SLOT_ALIASES if fact_cards.resolve(card, slot)],
        }
    (root / fact_cards.INDEX_FILE).write_text(
        json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return index


def quality_warnings(cards: list[dict]) -> list[str]:
    """宁缺勿错：把"能解析但不该直接进成稿"的卡片问题写进报告，人工确认。"""
    warnings: list[str] = []
    for card in cards:
        model = card["model"]
        screen = fact_cards.resolve(card, "屏幕尺寸")
        if screen and "深度知识库_v7" in card.get("library", ""):
            if not any(("圆角" in note or "标准矩形" in note) for note in screen["conditions"]):
                warnings.append(f"{model}: 屏幕尺寸缺「圆角设计/标准矩形」说明（源文件未采集）")
        for slot in fact_cards.SLOT_ALIASES:
            found = fact_cards.resolve(card, slot)
            if found and "*" in found["text"]:
                warnings.append(f"{model}: {slot} 值里残留脚注星号")
        labels = [field["name"] for field in card["fields"]
                  if field["section"] == "尺寸与重量"]
        if "厚度" in labels and not fact_cards.resolve(card, "厚度"):
            warnings.append(f"{model}: 厚度超出合理范围已停用（源文件标签疑似错位）")
    return list(dict.fromkeys(warnings))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成快发模式事实卡")
    parser.add_argument("--root", default=str(fact_cards.FACTS_DIR), help="事实卡输出目录")
    parser.add_argument("--library", action="append", default=None, help="只处理指定知识库（可重复）")
    parser.add_argument("--categories", default="", help="只保留类目名含这些关键字的型号，逗号分隔")
    parser.add_argument("--check", action="store_true", help="只校验，不写文件")
    args = parser.parse_args(argv)

    global WORKSPACE_SOURCES
    if args.library:
        WORKSPACE_SOURCES = tuple(Path(name) for name in args.library)
    cards, errors = collect()
    if args.categories:
        tokens = tuple(token.strip() for token in args.categories.split(",") if token.strip())
        cards = [card for card in cards if any(token in card["category"] for token in tokens)]
    if not cards:
        print("未在授权知识库中找到可解析的产品事实。", file=sys.stderr)
        for error in errors:
            print("  " + error, file=sys.stderr)
        return 1
    report = {"products": len(cards), "fields": sum(len(c["fields"]) for c in cards), "errors": errors}
    if not args.check:
        report.update(write(cards, Path(args.root)))
        report["root"] = str(Path(args.root).resolve())
    missing = {
        card["model"]: [slot for slot in ("重量", "屏幕尺寸", "电池") if not fact_cards.resolve(card, slot)]
        for card in cards
    }
    report["missing_core"] = {name: slots for name, slots in missing.items() if slots}
    warnings = quality_warnings(cards)
    report["warning_count"] = len(warnings)
    report["warnings"] = warnings[:40]
    print(json.dumps(report, ensure_ascii=False, indent=1)[:8000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
