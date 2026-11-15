"""StudyQuest 問題データ統合ジェネレータ。

3つの分割ジェネレータ（数学・理科 / 国語・情報Ⅰ / 英語・社会）の出力を統合し、
`data/subjects.json` と突合して全20通常教科（各150〜200問）の整合性を検証したうえで
`data/questions.json` を生成する。
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from generators.part_en_soc import generate as generate_en_soc
from generators.part_jp_info import generate as generate_jp_info
from generators.part_math_sci import generate as generate_math_sci

ROOT_DIR = Path(__file__).resolve().parent
SUBJECTS_PATH = ROOT_DIR / "data" / "subjects.json"
QUESTIONS_PATH = ROOT_DIR / "data" / "questions.json"

# 動的出題する単語帳教科（questions.jsonには問題行を持たせない）
VOCAB_BOOK_SUBJECT_IDS = frozenset({"target1900", "eiken_pre1_ex", "kobun330"})
MIN_QUESTIONS_PER_SUBJECT = 150
MAX_QUESTIONS_PER_SUBJECT = 200


def load_regular_subject_units(subjects_path: Path = SUBJECTS_PATH) -> dict[str, list[str]]:
    """`subjects.json` から単語帳以外の通常20教科と単元ID一覧を読み込む。"""
    payload = json.loads(subjects_path.read_text(encoding="utf-8"))
    regular: dict[str, list[str]] = {}
    for subj in payload.get("subjects", []):
        sid = subj["id"]
        if sid in VOCAB_BOOK_SUBJECT_IDS:
            continue
        regular[sid] = [u["id"] for u in subj.get("units", [])]
    return regular


def validate_all_questions(
    questions: list[dict],
    regular_units: dict[str, list[str]],
) -> dict[str, dict]:
    """全問題データの一意性・スキーマ・教科別件数（150〜200）・全単元網羅を検証する。"""
    seen_ids: set[str] = set()
    seen_questions: set[str] = set()
    by_subject: dict[str, list[dict]] = {sid: [] for sid in regular_units}

    for idx, q in enumerate(questions):
        qid = q.get("id")
        sid = q.get("subjectId")
        uid = q.get("unitId")
        qtype = q.get("type")
        diff = q.get("difficulty")
        qtext = q.get("question")
        ans = q.get("answer")
        exp = q.get("explanation")

        if not isinstance(qid, str) or not qid or qid in seen_ids:
            raise ValueError(f"重複または不正なid (index={idx}): {qid!r}")
        seen_ids.add(qid)

        if sid not in regular_units:
            raise ValueError(f"通常教科外のsubjectId (id={qid}): {sid!r}")
        if uid not in regular_units[sid]:
            raise ValueError(f"不正なunitId (id={qid}, subjectId={sid}): {uid!r}")

        if not isinstance(qtext, str) or not qtext.strip() or qtext in seen_questions:
            raise ValueError(f"空または全体重複のquestion (id={qid}): {qtext!r}")
        seen_questions.add(qtext)

        if qtype not in ("選択", "記述", "○×"):
            raise ValueError(f"不正なtype (id={qid}): {qtype!r}")
        if diff not in (1, 2, 3):
            raise ValueError(f"不正なdifficulty (id={qid}): {diff!r}")
        if not isinstance(ans, str) or not ans.strip():
            raise ValueError(f"空のanswer (id={qid})")
        if not isinstance(exp, str) or not exp.strip():
            raise ValueError(f"空のexplanation (id={qid})")

        if qtype == "選択":
            choices = q.get("choices")
            if not isinstance(choices, list) or len(choices) != 4:
                raise ValueError(f"選択問題のchoicesが4つではありません (id={qid}): {choices!r}")
            if len(set(choices)) != 4:
                raise ValueError(f"選択問題のchoicesに重複があります (id={qid}): {choices!r}")
            if ans not in choices:
                raise ValueError(f"選択問題のchoicesにanswerが含まれません (id={qid}): {ans!r}")
        else:
            if "choices" in q:
                raise ValueError(f"選択問題以外にchoicesが存在します (id={qid})")
            if qtype == "○×" and ans not in ("○", "×"):
                raise ValueError(f"○×問題のanswerが不正です (id={qid}): {ans!r}")

        if "alternativeAnswers" in q and q["alternativeAnswers"] is not None:
            alts = q["alternativeAnswers"]
            if not isinstance(alts, list) or not all(isinstance(a, str) and a.strip() for a in alts):
                raise ValueError(f"alternativeAnswersの形式が不正です (id={qid}): {alts!r}")

        by_subject[sid].append(q)

    summary: dict[str, dict] = {}
    for sid, expected_uids in regular_units.items():
        items = by_subject[sid]
        count = len(items)
        if not (MIN_QUESTIONS_PER_SUBJECT <= count <= MAX_QUESTIONS_PER_SUBJECT):
            raise ValueError(
                f"{sid} の問題数が {MIN_QUESTIONS_PER_SUBJECT}..{MAX_QUESTIONS_PER_SUBJECT} の範囲外です: {count}"
            )
        u_counts = Counter(item["unitId"] for item in items)
        missing_units = [u for u in expected_uids if u_counts[u] == 0]
        if missing_units:
            raise ValueError(f"{sid} に問題数0の単元があります: {missing_units}")
        summary[sid] = {
            "total": count,
            "units": {u: u_counts[u] for u in expected_uids},
            "types": dict(Counter(item["type"] for item in items)),
            "diffs": dict(sorted(Counter(item["difficulty"] for item in items).items())),
        }

    return summary


def build_questions() -> list[dict]:
    """3つのパート別ジェネレータを統合した全問題リストを返す。"""
    combined: list[dict] = []
    combined.extend(generate_math_sci())
    combined.extend(generate_jp_info())
    combined.extend(generate_en_soc())
    return combined


def main() -> None:
    regular_units = load_regular_subject_units()
    if len(regular_units) != 20:
        raise RuntimeError(f"通常教科数が20ではありません: {len(regular_units)} ({list(regular_units)})")

    questions = build_questions()
    summary = validate_all_questions(questions, regular_units)

    QUESTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with QUESTIONS_PATH.open("w", encoding="utf-8") as f:
        json.dump({"questions": questions}, f, ensure_ascii=False, indent=2)

    print(f"Generated {QUESTIONS_PATH} with {len(questions)} questions across {len(summary)} subjects:")
    for sid, info in summary.items():
        print(f"  - {sid:13s}: {info['total']:3d}問 | units={info['units']} | types={info['types']}")


if __name__ == "__main__":
    main()
