import json
import uuid
import random

vocab = []
with open("kobun_raw1.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line: continue
        parts = line.split('\t')
        if len(parts) >= 2:
            word_part = parts[0].split(' ', 1)[1] if ' ' in parts[0] else parts[0]
            vocab.append((word_part, parts[1]))

with open("kobun_raw2.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line: continue
        parts = line.split('\t')
        if len(parts) >= 2:
            word_part = parts[0].split(' ', 1)[1] if ' ' in parts[0] else parts[0]
            vocab.append((word_part, parts[1]))

# Split into 5 chapters (66 words each)
data = {
    "kobun330-ch1": vocab[0:66],
    "kobun330-ch2": vocab[66:132],
    "kobun330-ch3": vocab[132:198],
    "kobun330-ch4": vocab[198:264],
    "kobun330-ch5": vocab[264:]
}

# 1. Create vocab_kobun330.json
vocab_out = {
    "subjectId": "kobun330",
    "units": {}
}
for k, v in data.items():
    vocab_out["units"][k] = [[w, m] for w, m in v]

with open("data/vocab_kobun330.json", "w", encoding="utf-8") as f:
    json.dump(vocab_out, f, ensure_ascii=False, indent=2)

# 2. Update questions.json
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

def gen_kobun_questions(unit_id, words):
    all_meanings = [m for _, m in words]
    all_words = [w for w, _ in words]
    for word, meaning in words:
        wrong = random.sample([m for m in all_meanings if m != meaning], min(3, len(all_meanings)-1))
        ch = [meaning] + wrong; random.shuffle(ch)
        add_q("kobun330", unit_id, "選択", 1, f"古語「{word}」の意味は？", meaning, choices=ch)
        
        add_q("kobun330", unit_id, "記述", 2, f"「{meaning}」を意味する古語を答えよ。", word)
        
        add_q("kobun330", unit_id, "○×", 1, f"古語「{word}」は「{meaning}」という意味である。", "○")
        
        wrong_m = random.choice([m for m in all_meanings if m != meaning])
        add_q("kobun330", unit_id, "○×", 1, f"古語「{word}」は「{wrong_m}」という意味である。", "×")

for uid, words in data.items():
    gen_kobun_questions(uid, words)

try:
    with open('data/questions.json', 'r', encoding='utf-8') as f:
        existing = json.load(f)
except Exception:
    existing = {"questions": []}

existing_qs = [q for q in existing["questions"] if q.get("subjectId") != "kobun330"]
existing_qs.extend(questions)

with open('data/questions.json', 'w', encoding='utf-8') as f:
    json.dump({"questions": existing_qs}, f, ensure_ascii=False, indent=2)

print(f"古文単語330: Generated {len(questions)} questions across {len(data)} chapters. Total words: {len(vocab)}")
