import json
import re
from pathlib import Path

# デフォルトの入出力パス
DEFAULT_INPUT_PATH = Path(r"c:\Users\bbalmbcc\Downloads\1_ex.md")
DEFAULT_OUTPUT_PATH = Path("data/vocab_eiken_pre1_ex.json")

SUBJECT_ID = "eiken_pre1_ex"
TOTAL_EXPECTED_WORDS = 1680
UNIT_SIZE = 100
TOTAL_UNITS = (TOTAL_EXPECTED_WORDS + UNIT_SIZE - 1) // UNIT_SIZE  # 17単元

# 行フォーマット: <num>. **<word>**：<rhs>
ENTRY_LINE_RE = re.compile(r"^(\d+)\.\s*\*\*(.+?)\*\*：(.*)$")

# 品詞タグと丸数字（意味分割の境界として除去する）
POS_TAG_PATTERN = r"\[(?:名|動|形|副|前)\]"
CIRCLED_NUM_PATTERN = r"[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]"
SENSE_SPLIT_RE = re.compile(f"{POS_TAG_PATTERN}|{CIRCLED_NUM_PATTERN}")

# クイズの逆方向出題でヒント漏洩を防ぐため除去する類義語・対義語括弧注記
SYN_ANT_PAREN_RE = re.compile(r"[（(][≒⇔][^）)]*[）)]")

# 検証用の禁止マーカーパターン
FORBIDDEN_MEANING_RE = re.compile(f"{POS_TAG_PATTERN}|{CIRCLED_NUM_PATTERN}|[≒⇔]")


def extract_clean_meanings(raw_meaning: str) -> list[str]:
    """右辺の元の意味文字列から品詞タグ・丸数字・類義語/対義語注記を除去し、重複のない意味リストを返す。"""
    without_hints = SYN_ANT_PAREN_RE.sub("", raw_meaning)
    segments = SENSE_SPLIT_RE.split(without_hints)

    cleaned_meanings: list[str] = []
    seen: set[str] = set()
    for seg in segments:
        # 余分な空白・カンマ・読点を安全にトリムする
        normalized = re.sub(r"\s+", " ", seg).strip(" \t\r\n\u3000,，、")
        if normalized and normalized not in seen:
            seen.add(normalized)
            cleaned_meanings.append(normalized)

    return cleaned_meanings


def parse_eiken_pre1_ex(input_path: Path) -> dict:
    """Markdownファイルを解析し、StudyQuest用の単語帳JSONペイロードを構築する。"""
    units: dict[str, list[dict]] = {
        f"{SUBJECT_ID}-u{idx}": [] for idx in range(1, TOTAL_UNITS + 1)
    }

    with input_path.open("r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.rstrip("\r\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue

            match = ENTRY_LINE_RE.match(line)
            if not match:
                raise ValueError(f"想定外の行形式です (line {line_no}): {line}")

            num = int(match.group(1))
            word = match.group(2).strip()
            raw_meaning = match.group(3)

            meanings = extract_clean_meanings(raw_meaning)
            meaning = " / ".join(meanings)

            unit_idx = (num - 1) // UNIT_SIZE + 1
            unit_id = f"{SUBJECT_ID}-u{unit_idx}"
            if unit_id not in units:
                raise ValueError(f"単語番号が単元範囲外です (num={num}, line {line_no})")

            units[unit_id].append({
                "num": num,
                "word": word,
                "rawMeaning": raw_meaning,
                "meaning": meaning,
                "meanings": meanings,
            })

    return {
        "subjectId": SUBJECT_ID,
        "units": units,
    }


def verify_payload(payload: dict) -> dict:
    """生成されたJSONペイロードの整合性とエッジケースを検証し、サマリーを返す。"""
    if payload.get("subjectId") != SUBJECT_ID:
        raise AssertionError(f"subjectIdが不正です: {payload.get('subjectId')}")

    units = payload.get("units", {})
    expected_unit_ids = [f"{SUBJECT_ID}-u{i}" for i in range(1, TOTAL_UNITS + 1)]
    if list(units.keys()) != expected_unit_ids:
        raise AssertionError(f"単元キーが一致しません: {list(units.keys())}")

    all_nums: list[int] = []
    preserved_brackets: list[tuple[int, str, str]] = []

    for idx, unit_id in enumerate(expected_unit_ids, start=1):
        entries = units[unit_id]
        expected_len = 80 if idx == TOTAL_UNITS else UNIT_SIZE
        if len(entries) != expected_len:
            raise AssertionError(
                f"{unit_id} の語数が不正です: {len(entries)} (期待値: {expected_len})"
            )

        for entry in entries:
            num = entry["num"]
            word = entry["word"]
            raw_meaning = entry["rawMeaning"]
            meaning = entry["meaning"]
            meanings = entry["meanings"]

            all_nums.append(num)

            if not word or not raw_meaning or not meaning:
                raise AssertionError(f"必須フィールドが空です: num={num}, word={word}")
            if not isinstance(meanings, list) or not meanings:
                raise AssertionError(f"meaningsが空またはリストではありません: num={num}")
            if len(meanings) != len(set(meanings)):
                raise AssertionError(f"meaningsに重複があります: num={num}, {meanings}")
            if meaning != " / ".join(meanings):
                raise AssertionError(f"meaningとmeaningsの結合が一致しません: num={num}")

            # 禁止マーカー（品詞タグ・丸数字・≒・⇔）がmeaning/meaningsに残っていないことを確認
            if FORBIDDEN_MEANING_RE.search(meaning):
                raise AssertionError(f"禁止マーカーがmeaningに残存: num={num}, {meaning}")
            for item in meanings:
                if not item or FORBIDDEN_MEANING_RE.search(item):
                    raise AssertionError(f"禁止マーカーがmeaningsに残存: num={num}, {item}")

            for bracket in re.findall(r"\[[^\]]*\]", meaning):
                preserved_brackets.append((num, word, bracket))

    if len(all_nums) != TOTAL_EXPECTED_WORDS or all_nums != list(range(1, TOTAL_EXPECTED_WORDS + 1)):
        raise AssertionError(
            f"番号の連番チェックに失敗しました: count={len(all_nums)}, unique={len(set(all_nums))}"
        )

    return {
        "totalWords": len(all_nums),
        "unitCount": len(units),
        "u1Count": len(units[f"{SUBJECT_ID}-u1"]),
        "u17Count": len(units[f"{SUBJECT_ID}-u17"]),
        "preservedBrackets": preserved_brackets,
    }


def main() -> None:
    payload = parse_eiken_pre1_ex(DEFAULT_INPUT_PATH)
    summary = verify_payload(payload)

    DEFAULT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    print(
        f"Generated {DEFAULT_OUTPUT_PATH} with {summary['totalWords']} words "
        f"across {summary['unitCount']} units (u1={summary['u1Count']}, u17={summary['u17Count']})."
    )
    print(f"Preserved non-POS brackets ({len(summary['preservedBrackets'])}): {summary['preservedBrackets']}")


if __name__ == "__main__":
    main()
