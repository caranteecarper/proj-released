import argparse
import json
import os
import sys
from typing import Any, Dict, List, Tuple

from translator_client import TencentTextTranslator, build_translator_from_env


def load_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected a list in output JSON.")
    return data


def save_json(path: str, data: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def has_cjk(text: str, threshold: float = 0.2) -> bool:
    if not text:
        return False
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    ratio = cjk / max(1, len(text))
    return ratio >= threshold


def translate_record(
    rec: Dict[str, Any],
    translator: TencentTextTranslator,
    source_lang: str,
    target_lang: str,
    skip_if_chinese: bool = True,
) -> Tuple[bool, Dict[str, Any]]:
    changed = False
    title = rec.get("title") or ""
    content = rec.get("content") or ""

    if skip_if_chinese:
        if has_cjk(title):
            title = title
        else:
            if title.strip():
                title = translator.translate_text(title, source=source_lang, target=target_lang)
                changed = True
        if has_cjk(content):
            content = content
        else:
            if content.strip():
                content = translator.translate_text(content, source=source_lang, target=target_lang)
                changed = True
    else:
        if title.strip():
            title = translator.translate_text(title, source=source_lang, target=target_lang)
            changed = True
        if content.strip():
            content = translator.translate_text(content, source=source_lang, target=target_lang)
            changed = True

    if changed:
        rec["title"] = title
        rec["content"] = content
    return changed, rec


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate title/content in output_complete.json via Tencent TextTranslate.")
    parser.add_argument("--input", default="output_complete.json", help="Input JSON path.")
    parser.add_argument("--output", default="output_complete.json", help="Output JSON path (can be same as input).")
    parser.add_argument("--source", default="auto", help="Source language, e.g., auto or en.")
    parser.add_argument("--target", default="zh", help="Target language, e.g., zh.")
    parser.add_argument("--project-id", type=int, default=0, help="Tencent Cloud ProjectId.")
    parser.add_argument("--max-len", type=int, default=4500, help="Max chars per request (will chunk).")
    parser.add_argument("--qps", type=float, default=4.5, help="Max requests per second (soft limit).")
    parser.add_argument("--skip-chinese", action="store_true", default=True, help="Skip items already containing Chinese.")
    parser.add_argument("--no-skip-chinese", action="store_false", dest="skip_chinese")
    parser.add_argument("--region", default=None, help="Override region (default env or ap-beijing).")
    args = parser.parse_args()

    try:
        translator = build_translator_from_env(
            default_region=args.region or "ap-beijing",
            project_id=args.project_id,
            max_len=args.max_len,
            qps=args.qps,
        )
    except Exception as e:
        print(f"Failed to init translator: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        items = load_json(args.input)
    except Exception as e:
        print(f"Failed to load {args.input}: {e}", file=sys.stderr)
        sys.exit(1)

    changed_count = 0
    for idx, rec in enumerate(items, 1):
        try:
            changed, rec = translate_record(
                rec,
                translator=translator,
                source_lang=args.source,
                target_lang=args.target,
                skip_if_chinese=args.skip_chinese,
            )
            if changed:
                changed_count += 1
        except Exception as e:
            print(f"[{idx}] translate failed: {e}", file=sys.stderr)
            continue

    try:
        save_json(args.output, items)
    except Exception as e:
        print(f"Failed to save {args.output}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Done. Translated records: {changed_count}/{len(items)}. Output -> {args.output}")


if __name__ == "__main__":
    main()
