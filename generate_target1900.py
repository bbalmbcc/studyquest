import json
import re
from pathlib import Path


def split_meanings(meaning_text: str) -> list[str]:
    """括弧外の '/' を区切り文字として意味を分割する"""
    parts = []
    buf = []
    depth = 0
    open_chars = set("(（〔［")
    close_chars = set(")）〕］")

    for ch in meaning_text:
        if ch in open_chars:
            depth += 1
            buf.append(ch)
        elif ch in close_chars:
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == "/" and depth == 0:
            item = "".join(buf).strip()
            if item:
                parts.append(item)
            buf = []
        else:
            buf.append(ch)

    last = "".join(buf).strip()
    if last:
        parts.append(last)
    return parts


def main():
    input_path = Path(r"c:\Users\bbalmbcc\Downloads\1900_6.md")
    output_path = Path("data/vocab_target1900.json")

    pattern = re.compile(r"^(\d+)\.\s*\*\*(.+?)\*\*:\s*(.+)$")
    units = {f"target1900-u{i}": [] for i in range(1, 20)}

    total_count = 0
    with input_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            m = pattern.match(line)
            if not m:
                continue

            num = int(m.group(1))
            word = m.group(2).strip()
            meaning = m.group(3).strip()
            meanings = split_meanings(meaning)

            unit_idx = (num - 1) // 100 + 1
            unit_id = f"target1900-u{unit_idx}"
            if unit_id not in units:
                units[unit_id] = []

            units[unit_id].append({
                "num": num,
                "word": word,
                "meaning": meaning,
                "meanings": meanings,
            })
            total_count += 1

    payload = {
        "subjectId": "target1900",
        "units": units,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Generated {output_path} with {total_count} words across {len(units)} units.")


if __name__ == "__main__":
    main()
