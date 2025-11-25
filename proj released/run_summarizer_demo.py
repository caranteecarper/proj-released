import os
import json
from summarizer import summarize_text


def main():
    # Prepare samples
    zh_text = (
        "今天天气不错，我们下午三点开会。请提前准备材料。"
        "这个项目的目标是完成爬虫和摘要，并产出结构化结果。"
    )
    en_text = (
        "This project aims to build a crawler and a summarizer. "
        "We will meet at 3 pm to review progress. "
        "Please prepare materials in advance."
    )

    lines = []

    # Demo 1: Chinese sample
    lines.append("[CN demo]")
    lines.append("Input: " + zh_text)
    lines.append("Summary: " + summarize_text(zh_text, max_chars=60, title="项目会议通知"))
    lines.append("")

    # Demo 2: English sample
    lines.append("[EN demo]")
    lines.append("Input: " + en_text)
    lines.append("Summary: " + summarize_text(en_text, max_chars=80, title="Project meeting"))
    lines.append("")

    # Demo 3: From output_complete.json (first record if available)
    record_summary = None
    if os.path.exists("output_complete.json"):
        try:
            with open("output_complete.json", "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                rec = data[0]
                title = rec.get("title") or ""
                content = rec.get("content") or ""
                if content:
                    record_summary = summarize_text(content, max_chars=120, title=title)
                    lines.append("[From output_complete.json First Record]")
                    lines.append("Title: " + (title or "<no title>"))
                    # Keep input short for the demo file
                    preview = content[:180].replace("\n", " ") + ("…" if len(content) > 180 else "")
                    lines.append("Content preview: " + preview)
                    lines.append("Summary: " + record_summary)
        except Exception as e:
            lines.append("[JSON load error] " + str(e))

    out_dir = "generated_html"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "summarizer_demo_output.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(out_path)


if __name__ == "__main__":
    main()

