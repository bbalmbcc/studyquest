import json
import uuid
import random

questions = []

def add_q(subject_id, unit_id, q_type, diff, q_text, ans, choices=None, exp=None, alt=None):
    q = {
        "id": f"{subject_id}-{str(uuid.uuid4())[:8]}",
        "subjectId": subject_id,
        "unitId": unit_id,
        "type": q_type,
        "difficulty": diff,
        "question": q_text,
        "answer": ans,
        "explanation": exp or ""
    }
    if choices:
        q["choices"] = choices
    if alt:
        q["alternativeAnswers"] = alt
    questions.append(q)

# 問題データリスト
data = [
    # 数学I
    ("math1", "math1-u1", "選択", 1, "(-2) × (-3) の計算結果は？", "6", ["-6", "6", "5", "-5"], None),
    ("math1", "math1-u1", "記述", 1, "(x + 2)(x + 3) を展開せよ。", "x^2 + 5x + 6", None, ["x²+5x+6"]),
    ("math1", "math1-u2", "○×", 1, "A = {1, 2, 3} と B = {2, 3, 4} の共通部分 A∩B は {2, 3} である。", "○", None, None),
    ("math1", "math1-u3", "選択", 2, "y = (x - 2)^2 + 3 の頂点の座標は？", "(2, 3)", ["(2, 3)", "(-2, 3)", "(2, -3)", "(-2, -3)"], None),
    ("math1", "math1-u4", "記述", 2, "直角三角形において、底辺が3、高さが4のとき、斜辺の長さは？", "5", None, None),
    
    # 数学A
    ("mathA", "mathA-u1", "選択", 1, "さいころを1回投げるとき、偶数が出る確率は？", "1/2", ["1/6", "1/3", "1/2", "2/3"], None),
    ("mathA", "mathA-u1", "記述", 2, "4人を一列に並べる並べ方は何通りあるか？", "24", None, ["24通り"]),
    ("mathA", "mathA-u2", "○×", 1, "三角形の3つの中線は1点で交わり、その点を重心という。", "○", None, None),
    
    # 数学II
    ("math2", "math2-u1", "○×", 1, "(a+b)^2 = a^2 + 2ab + b^2 は恒等式である。", "○", None, None),
    ("math2", "math2-u4", "選択", 1, "cos 60° の値は？", "1/2", ["1/2", "√2/2", "√3/2", "1"], None),
    ("math2", "math2-u6", "記述", 2, "f(x) = x^3 を微分せよ。", "3x^2", None, ["3x^2", "3x²"]),
    
    # 数学B
    ("mathB", "mathB-u1", "選択", 1, "初項2、公差3の等差数列の第3項は？", "8", ["5", "8", "11", "6"], None),
    ("mathB", "mathB-u1", "記述", 2, "1から10までの自然数の和は？", "55", None, None),
    
    # 数学C
    ("mathC", "mathC-u1", "○×", 2, "零ベクトルは大きさが0で、向きはない。", "○", None, None),
    ("mathC", "mathC-u1", "選択", 2, "ベクトル a=(1, 2) と b=(3, -1) の内積は？", "1", ["1", "5", "-1", "0"], None),

    # 国語系
    ("gendai", "gendai-u1", "選択", 1, "評論文を読む際、筆者の意見が最も表れやすい部分はどこか？", "結論部", ["序論部", "具体例", "結論部", "引用部"], None),
    ("gengo", "gengo-u1", "記述", 2, "「あはれなり」の現代語訳は？", "しみじみと趣深い", None, ["しみじみとした趣がある", "趣深い"]),
    ("ronri_kokugo", "ronri_kokugo-u1", "○×", 1, "論理的な文章では、客観的な事実と筆者の主観的な意見を区別することが重要である。", "○", None, None),
    ("bungaku", "bungaku-u1", "選択", 1, "小説において、物語の進行役となる人物を何というか？", "語り手", ["作者", "主人公", "語り手", "読者"], None),
    ("koten", "koten-u3", "選択", 2, "過去の助動詞「き」の連体形は？", "し", ["き", "し", "しか", "まる"], None),
    ("koten", "koten-u1", "記述", 1, "「枕草子」の作者は誰か？", "清少納言", None, ["清少納言（せいしょうなごん）"]),

    # 理科系
    ("kagaku", "kagaku-u1", "選択", 1, "水分子(H2O)はどのような結合でできているか？", "共有結合", ["イオン結合", "金属結合", "共有結合", "水素結合"], None),
    ("kagaku", "kagaku-u2", "記述", 1, "酸と塩基が反応して、水と塩ができる反応を何というか？", "中和反応", None, ["中和"]),
    ("seibutsu", "seibutsu-u1", "○×", 1, "動物細胞にも植物細胞にも、細胞膜が存在する。", "○", None, None),
    ("seibutsu", "seibutsu-u3", "選択", 2, "ヒトの心臓はいくつの部屋に分かれているか？", "4つ", ["2つ", "3つ", "4つ", "5つ"], None),
    ("seibutsu", "seibutsu-u4", "記述", 1, "植物が光のエネルギーを利用して有機物を合成する働きは？", "光合成", None, None),

    # 社会系
    ("rekishi", "rekishi-u1", "選択", 1, "1789年に起きた、フランスにおける市民革命を何というか？", "フランス革命", ["名誉革命", "アメリカ独立革命", "フランス革命", "産業革命"], None),
    ("sekaishi", "sekaishi-u2", "記述", 2, "イスラーム教の聖典は何か？", "コーラン", None, ["クルアーン"]),
    ("sekaishi", "sekaishi-u3", "○×", 1, "ルネサンスは「再生」を意味し、古代ギリシア・ローマの文化を理想とした。", "○", None, None),
    ("koukyou", "koukyou-u1", "選択", 1, "日本国憲法において、国権の最高機関とされるのはどれか？", "国会", ["内閣", "裁判所", "国会", "天皇"], None),
    ("koukyou", "koukyou-u3", "記述", 1, "SDGs（持続可能な開発目標）は、いくつの目標から構成されているか？", "17", None, ["17の目標", "17個"]),

    # 英語系
    ("eigo_c1", "eigo_c1-u1", "選択", 1, "I (   ) a student.", "am", ["am", "is", "are", "be"], None),
    ("eigo_c1", "eigo_c1-u2", "記述", 2, "「私は昨日、テニスをしました」の英訳: I (   ) tennis yesterday.", "played", None, None),
    ("eigo_c2", "eigo_c2-u1", "○×", 1, "現在完了形の基本形は「have/has + 過去分詞」である。", "○", None, None),
    ("ronri_e1", "ronri_e1-u3", "選択", 2, "I enjoy (   ) baseball.", "playing", ["to play", "playing", "play", "played"], None),
    ("ronri_e2", "ronri_e2-u2", "記述", 2, "「〜しながら」という意味を作る分詞構文は、通常動詞の何形で始まるか？（日本語で）", "ing形", None, ["現在分詞", "現在分詞形"]),

    # 情報・家庭
    ("joho", "joho-u1", "選択", 1, "インターネット上で個人情報を不正に取得する詐欺行為を何というか？", "フィッシング", ["スパム", "フィッシング", "マルウェア", "ハッキング"], None),
    ("joho", "joho-u4", "○×", 1, "Wi-Fiは無線LANの規格の一つである。", "○", None, None),
    ("katei", "katei-u1", "記述", 1, "三大栄養素とは、炭水化物、脂質と何か？", "たんぱく質", None, ["タンパク質"]),
    ("katei", "katei-u4", "選択", 1, "環境に配慮した商品の購入を促すマークで、ノートやトイレットペーパーなどについているものは？", "エコマーク", ["SGマーク", "JISマーク", "エコマーク", "ベルマーク"], None)
]

for subj, unit, t, diff, q, a, choices, alt in data:
    add_q(subj, unit, t, diff, q, a, choices=choices, alt=alt)

with open('data/questions.json', 'w', encoding='utf-8') as f:
    json.dump({"questions": questions}, f, ensure_ascii=False, indent=2)

print(f"Generated {len(questions)} unique questions.")
