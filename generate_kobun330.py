import json
import re
from pathlib import Path

from generate_target1900 import split_meanings

# 古文単語330 章ごとの上限番号と単元IDのマッピング
KOBUN330_CHAPTERS = (
    (50, "kobun330-ch1"),
    (150, "kobun330-ch2"),
    (180, "kobun330-ch3"),
    (280, "kobun330-ch4"),
    (330, "kobun330-ch5"),
)


def get_kobun330_unit(num: int) -> str:
    """単語番号（1〜330）に対応する単元IDを返す"""
    for max_num, unit_id in KOBUN330_CHAPTERS:
        if num <= max_num:
            return unit_id
    raise ValueError(f"単語番号が範囲外です: {num}")


def main():
    input_path = Path(r"c:\Users\bbalmbcc\Downloads\330.md")
    vocab_output_path = Path("data/vocab_kobun330.json")
    questions_path = Path("data/questions.json")

    pattern = re.compile(r"^(\d+)\.\s*\*\*(.+?)\*\*[:：]\s*(.+)$")
    units = {unit_id: [] for _, unit_id in KOBUN330_CHAPTERS}

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
            unit_id = get_kobun330_unit(num)

            units[unit_id].append({
                "num": num,
                "word": word,
                "meaning": meaning,
                "meanings": meanings,
            })
            total_count += 1

    payload = {
        "subjectId": "kobun330",
        "units": units,
    }
    vocab_output_path.parent.mkdir(parents=True, exist_ok=True)
    with vocab_output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    # questions.json に残っている旧 kobun330 問題を除去（動的構築へ移行するため）
    if questions_path.exists():
        with questions_path.open("r", encoding="utf-8") as f:
            q_data = json.load(f)
        orig_qs = q_data.get("questions", [])
        filtered_qs = [q for q in orig_qs if q.get("subjectId") != "kobun330"]
        removed = len(orig_qs) - len(filtered_qs)
        if removed > 0:
            with questions_path.open("w", encoding="utf-8") as f:
                json.dump({"questions": filtered_qs}, f, ensure_ascii=False, indent=2)
            print(f"Removed {removed} legacy kobun330 questions from {questions_path}.")

    print(f"Generated {vocab_output_path} with {total_count} words across {len(units)} units.")


if __name__ == "__main__":
    main()
