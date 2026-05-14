import json, uuid, random

questions = []
used = set()

def add_q(sid, uid, qt, diff, qtxt, ans, choices=None, exp=None, alt=None):
    if qtxt in used: return False
    used.add(qtxt)
    q = {"id": f"{sid}-{str(uuid.uuid4())[:8]}", "subjectId": sid, "unitId": uid,
         "type": qt, "difficulty": diff, "question": qtxt, "answer": str(ans), "explanation": exp or ""}
    if choices: q["choices"] = [str(c) for c in choices]
    if alt: q["alternativeAnswers"] = [str(a) for a in alt]
    questions.append(q)
    return True

# Bricks 1 - Stage/Unit別の単語データ
# 各Stage5Unit、1Unitあたり約20語 = 計約600語
with open('data/vocab_bricks1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)["units"]

def gen_vocab_questions(unit_id, words):
    all_meanings = [m for _, m in words]
    all_words = [w for w, _ in words]
    count = 0
    for eng, jpn in words:
        # 英→日 選択
        wrong = random.sample([m for m in all_meanings if m != jpn], min(3, len(all_meanings)-1))
        ch = [jpn] + wrong; random.shuffle(ch)
        if add_q("bricks1", unit_id, "選択", 1, f"「{eng}」の意味は？", jpn, choices=ch): count += 1

        # 日→英 記述
        if add_q("bricks1", unit_id, "記述", 2, f"「{jpn}」を英語で答えよ。", eng): count += 1

        # ○× (正しい)
        if add_q("bricks1", unit_id, "○×", 1, f"「{eng}」は「{jpn}」という意味である。", "○"): count += 1

        # ○× (誤り)
        wrong_m = random.choice([m for m in all_meanings if m != jpn])
        if add_q("bricks1", unit_id, "○×", 1, f"「{eng}」は「{wrong_m}」という意味である。", "×"): count += 1

for uid, words in data.items():
    gen_vocab_questions(uid, words)

# 既存のquestions.jsonを読み込んで追加
with open('data/questions.json', 'r', encoding='utf-8') as f:
    existing = json.load(f)

# 既存のbricks1の問題を除去して新しいものに置き換え
existing_qs = [q for q in existing["questions"] if q["subjectId"] != "bricks1"]
existing_qs.extend(questions)

with open('data/questions.json', 'w', encoding='utf-8') as f:
    json.dump({"questions": existing_qs}, f, ensure_ascii=False, indent=2)

print(f"Bricks 1: Generated {len(questions)} questions across {len(data)} units.")
