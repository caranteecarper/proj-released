import os
import json
from summarizer import summarize_text


def main():
    src = "output_complete.json"
    out_dir = "generated_html"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "summarizer_top10.txt")

    lines = []
    if not os.path.exists(src):
        lines.append("[Error] output_complete.json not found.")
    else:
        try:
            with open(src, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
        except Exception as e:
            lines.append(f"[Error] Failed to load JSON: {e}")
            data = None

        if isinstance(data, list) and data:
            n = min(10, len(data))
            for i in range(n):
                rec = data[i] or {}
                title = rec.get("title") or ""
                url = rec.get("url") or ""
                content = rec.get("content") or ""
                summary = summarize_text(content, max_chars=120, title=title)
                lines.append(f"[#{i+1}]")
                lines.append(f"Title: {title}")
                if url:
                    lines.append(f"URL: {url}")
                preview = (content or "")[:180].replace("\n", " ")
                if content and len(content) > 180:
                    preview += "…"
                lines.append(f"Content preview: {preview}")
                lines.append(f"Summary: {summary}")
                lines.append("")
        else:
            lines.append("[Info] JSON is empty or not a list.")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(out_path)


if __name__ == "__main__":
    main()

