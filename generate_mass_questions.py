import json
import uuid
import random

questions = []
used_questions = set()

def add_q(subject_id, unit_id, q_type, diff, q_text, ans, choices=None, exp=None, alt=None):
    if q_text in used_questions:
        return False
    used_questions.add(q_text)
    
    q = {
        "id": f"{subject_id}-{str(uuid.uuid4())[:8]}",
        "subjectId": subject_id,
        "unitId": unit_id,
        "type": q_type,
        "difficulty": diff,
        "question": q_text,
        "answer": str(ans),
        "explanation": exp or ""
    }
    if choices:
        q["choices"] = [str(c) for c in choices]
    if alt:
        q["alternativeAnswers"] = [str(a) for a in alt]
    questions.append(q)
    return True

def generate_math_questions():
    # 数学Ⅰ (展開, 頂点, 二乗)
    for a in range(1, 15):
        for b in range(1, 15):
            add_q("math1", "math1-u1", "記述", 1, f"(x + {a})(x + {b}) を展開せよ。", f"x^2 + {a+b}x + {a*b}", alt=[f"x²+{(a+b)}x+{a*b}"])
            if len([q for q in questions if q["subjectId"] == "math1"]) >= 20: break
    for h in range(1, 20):
        for k in range(1, 10):
            choices = [f"({h}, {k})", f"({-h}, {k})", f"({h}, {-k})", f"({-h}, {-k})"]
            random.shuffle(choices)
            add_q("math1", "math1-u3", "選択", 2, f"y = (x - {h})^2 + {k} の頂点の座標は？", f"({h}, {k})", choices=choices)
            if len([q for q in questions if q["subjectId"] == "math1"]) >= 40: break
    for x in range(2, 22):
        add_q("math1", "math1-u1", "記述", 1, f"{x}^2 の値は？", x*x)
        if len([q for q in questions if q["subjectId"] == "math1"]) >= 50: break

    # 数学A (確率, 順列, 組合せ)
    import math
    for n in range(3, 10):
        for r in range(2, n+1):
            add_q("mathA", "mathA-u1", "記述", 2, f"{n}個から{r}個選んで一列に並べる順列 {n}P{r} の値は？", math.perm(n, r))
            if len([q for q in questions if q["subjectId"] == "mathA"]) >= 25: break
    for n in range(3, 10):
        for r in range(2, n):
            add_q("mathA", "mathA-u1", "記述", 2, f"{n}個から{r}個選ぶ組合せ {n}C{r} の値は？", math.comb(n, r))
            if len([q for q in questions if q["subjectId"] == "mathA"]) >= 50: break

    # 数学Ⅱ (微分, 積分)
    for a in range(1, 26):
        add_q("math2", "math2-u6", "記述", 1, f"f(x) = {a}x^2 を微分せよ。", f"{2*a}x")
    for a in range(1, 26):
        add_q("math2", "math2-u6", "記述", 2, f"f(x) = {a}x^3 を微分せよ。", f"{3*a}x^2", alt=[f"{3*a}x²"])

    # 数学B (等差数列, 等比数列)
    for a in range(1, 15):
        for d in range(2, 6):
            add_q("mathB", "mathB-u1", "記述", 1, f"初項{a}、公差{d}の等差数列の第5項は？", a + 4*d)
            if len([q for q in questions if q["subjectId"] == "mathB"]) >= 25: break
    for a in range(1, 15):
        for r in range(2, 5):
            add_q("mathB", "mathB-u1", "記述", 2, f"初項{a}、公比{r}の等比数列の第4項は？", a * (r**3))
            if len([q for q in questions if q["subjectId"] == "mathB"]) >= 50: break

    # 数学C (ベクトル)
    for x1 in range(1, 8):
        for y1 in range(1, 8):
            for x2 in range(1, 6):
                for y2 in range(1, 6):
                    add_q("mathC", "mathC-u1", "記述", 1, f"ベクトル a=({x1}, {y1}) と b=({x2}, {y2}) の和 a+b は？", f"({x1+x2}, {y1+y2})")
                    if len([q for q in questions if q["subjectId"] == "mathC"]) >= 25: break
            if len([q for q in questions if q["subjectId"] == "mathC"]) >= 50: break
    for x1 in range(1, 8):
        for y1 in range(1, 8):
            add_q("mathC", "mathC-u1", "記述", 2, f"ベクトル a=({x1}, {y1}) と b=({y1}, {-x1}) の内積 a・b は？", 0)

# 知識問題の汎用ジェネレータ
def generate_knowledge_questions(subject_id, unit_id, data_dict):
    count = 0
    items = list(data_dict.items())
    random.shuffle(items)
    
    # 形式を分散させて50問生成
    while count < 50:
        for key, val in items:
            if count >= 50: break
            
            # 形式をランダムに決定 (1:選択, 2:記述, 3:○×, 4:逆引き選択)
            q_type_choice = random.randint(1, 4)
            
            if q_type_choice == 1 or q_type_choice == 4:
                q_type = "選択"
                choices = [val if q_type_choice == 1 else key]
                others = [v if q_type_choice == 1 else k for k, v in items if (k if q_type_choice == 1 else v) != choices[0]]
                choices.extend(random.sample(others, min(3, len(others))))
                random.shuffle(choices)
                if q_type_choice == 1:
                    q = f"「{key}」の説明・意味・関連語として適切なものはどれか？"
                    ans = val
                else:
                    q = f"「{val}」に該当する用語はどれか？"
                    ans = key
                if add_q(subject_id, unit_id, q_type, random.randint(1, 2), q, ans, choices=choices):
                    count += 1
                
            elif q_type_choice == 2:
                q_type = "記述"
                q = f"「{val}」に該当する用語を答えよ。"
                ans = key
                if add_q(subject_id, unit_id, q_type, 2, q, ans):
                    count += 1
                
            elif q_type_choice == 3:
                q_type = "○×"
                is_true = random.random() > 0.5
                if is_true:
                    q = f"「{key}」とは「{val}」のことである。"
                    ans = "○"
                else:
                    wrong_val = random.choice([v for k, v in items if v != val])
                    q = f"「{key}」とは「{wrong_val}」のことである。"
                    ans = "×"
                if add_q(subject_id, unit_id, q_type, 1, q, ans):
                    count += 1
        
        # 1周しても50問に満たない場合はシャッフルしてもう1周（すでにadd_q内で重複チェックは行われているため、形式が違うものだけ追加される）
        random.shuffle(items)
        
        # もしこれ以上追加できる形式がない場合（無限ループ防止）
        if len(used_questions) > 5000: # セーフティ
            break

def run():
    generate_math_questions()
    
    # 現代の国語 (四字熟語、ことわざ、語彙)
    gendai_data = {
        "一期一会": "一生に一度だけの出会い", "試行錯誤": "何度も試みて失敗を重ねながら解決に近づくこと", "本末転倒": "根本的なことと些細なことを取り違えること",
        "温故知新": "昔の事を調べて、そこから新しい知識や見解を得ること", "悪戦苦闘": "困難な状況の中で、苦しみながら努力すること", "傍若無人": "周囲を気にせず、勝手気ままに振る舞うこと",
        "以心伝心": "言葉に出さなくても、お互いの心が通じ合うこと", "臨機応変": "その場その場の状況に合わせて適切な対応をすること", "自業自得": "自分の悪い行いの報いを自分が受けること",
        "千載一遇": "千年に一度しか巡り会えないような、めったにない好機", "一石二鳥": "一つの行為で二つの利益を得ること", "四面楚歌": "周囲がすべて敵や反対者で、孤立している状態",
        "日進月歩": "日に日に、また月ごとに絶えず進歩すること", "前代未聞": "これまで聞いたことがないような珍しいこと", "絶体絶命": "どうしても逃れられない困難な状況",
        "大器晩成": "偉大な人物は、大成するまでに時間がかかるということ", "馬耳東風": "人の意見や批評を心に留めず、聞き流すこと", "一喜一憂": "状況が変わるたびに喜んだり心配したりすること",
        "我田引水": "自分の都合のいいように物事を引き寄せること", "自画自賛": "自分で自分を褒めること",
        "アイデンティティ": "自己同一性。自分が自分であるという確信。", "パラダイム": "ある時代を支配する思考の枠組み。", "カタルシス": "心の中のわだかまりが解消され、すっきりすること。",
        "メタファー": "暗喩。形式上「～のようだ」などの言葉を使わない比喩。", "ジレンマ": "二つの選択肢の間で板挟みになること。", "ステレオタイプ": "固定観念。紋切り型の見方。",
        "アンビバレンス": "同一の対象に対して、愛と憎しみなど相反する感情を同時に持つこと。", "シニカル": "皮肉な態度。冷笑的。", "アイロニー": "皮肉。反語。",
        "ノスタルジー": "郷愁。過去や故郷を懐かしむ気持ち。", "モラトリアム": "猶予期間。社会的な責任を一時的に免除されている状態。", "エゴイズム": "利己主義。自己中心的な考え方。",
        "アニミズム": "すべての事物に霊魂が宿っているという考え方。", "ア・プリオリ": "先天的。経験に先立つもの。", "タブラ・ラサ": "白紙状態。経験以前の心。",
        "イデオロギー": "歴史的・社会的な立場に基づく根本的な考え方。", "ヒエラルキー": "階層制。ピラミッド型の階級組織。", "コスモロジー": "宇宙観。世界観。",
        "レトリック": "修辞学。効果的で美しい表現技法。", "ペシミズム": "悲観主義。物事を悪い方へ考える傾向。", "オプティミズム": "楽観主義。物事を良い方へ考える傾向。",
        "ニヒリズム": "虚無主義。すべての権威や価値を否定する立場。", "ストイック": "禁欲的。情念を抑え、義務を重んじる態度。", "ナルシシズム": "自己愛。自分自身に陶酔すること。",
        "コンプレックス": "劣等感。無意識の複合体。", "トラウマ": "心的外傷。精神的な傷。", "マジョリティ": "多数派。", "マイノリティ": "少数派。", "グローバル": "地球規模の。世界的な。", "ローカル": "局所的な。地域的な。"
    }
    
    # 古典探求 / 言語文化
    koten_data = {
        "いと": "とても、たいそう", "あはれなり": "しみじみと趣深い", "をかし": "趣がある、興味深い", "いみじ": "とても、すばらしい、ひどい",
        "ゆかし": "見たい、聞きたい、知りたい", "あやし": "不思議だ、身分が低い、粗末だ", "ありがたし": "めったにない、生きるのが難しい", "つきづきし": "似つかわしい、ふさわしい",
        "なまめかし": "優美だ、若々しい", "めでたし": "すばらしい", "うるはし": "きちんとしている、美しい", "やむごとなし": "高貴だ、格別だ",
        "おとなし": "大人びている、思慮分別がある", "ゆゆし": "不吉だ、すばらしい、たいそう", "かしこし": "恐れ多い、すばらしい、たいそう", "らうたし": "かわいらしい",
        "はづかし": "（こちらが恥ずかしくなるほど）立派だ、気が引ける", "心にくし": "奥ゆかしい", "にくし": "いやだ、あてこすりだ", "つれなし": "平然としている、冷淡だ",
        "ところせし": "窮屈だ、いばっている", "後ろめたし": "気がかりだ", "わりなし": "道理に合わない、どうしようもない、むやみに", "本意なし": "不本意だ、残念だ",
        "あぢきなし": "つまらない、どうにもならない", "すさまじ": "興ざめだ、殺風景だ", "びんなし": "不都合だ、気の毒だ", "うし": "つらい、いやだ",
        "むつかし": "不快だ、気味が悪い", "おぼつかなし": "はっきりしない、気がかりだ、待ち遠しい", "心もとなし": "はっきりしない、気がかりだ、待ち遠しい", "いとほし": "気の毒だ、かわいい",
        "いはけなし": "あどけない、子どもっぽい", "つれづれなり": "退屈だ、物寂しい", "むげなり": "ひどい", "あからさまなり": "ほんのちょっと",
        "かたくななり": "教養がない、見苦しい", "あだなり": "はかない、浮気だ", "すずろなり": "むやみに、思いがけない", "むなしくなる": "死ぬ",
        "おこたる": "病気が治る", "なやむ": "病気になる", "おどろく": "目を覚ます、はっと気づく", "ののしる": "大声で騒ぐ、評判になる", "念ず": "祈る、我慢する",
        "覚ゆ": "思われる、似ている、思い出す", "忍ぶ": "我慢する、人目を避ける", "頼む": "あてにする、あてにさせる", "かづく": "かぶる、いただく、かぶせる、与える", "わたる": "行く、来る、ずっと～する"
    }
    
    # 英語 (単語の意味)
    eigo_data = {
        "apple": "りんご", "book": "本", "cat": "猫", "dog": "犬", "elephant": "象",
        "environment": "環境", "education": "教育", "government": "政府", "society": "社会", "economy": "経済",
        "technology": "技術", "culture": "文化", "history": "歴史", "science": "科学", "language": "言語",
        "important": "重要な", "difficult": "難しい", "necessary": "必要な", "possible": "可能な", "different": "異なる",
        "develop": "発展させる", "improve": "向上させる", "protect": "保護する", "provide": "提供する", "consider": "考慮する",
        "require": "要求する", "include": "含む", "understand": "理解する", "remember": "思い出す", "believe": "信じる",
        "experience": "経験", "knowledge": "知識", "opportunity": "機会", "result": "結果", "reason": "理由",
        "problem": "問題", "solution": "解決策", "effect": "効果", "influence": "影響", "benefit": "利益",
        "beautiful": "美しい", "dangerous": "危険な", "popular": "人気のある", "successful": "成功した", "traditional": "伝統的な",
        "recently": "最近", "finally": "ついに", "usually": "たいてい", "especially": "特に", "probably": "おそらく"
    }

    # 理科 (化学基礎・生物基礎)
    kagaku_data = {
        "水素": "原子番号1、元素記号H", "ヘリウム": "原子番号2、元素記号He", "リチウム": "原子番号3、元素記号Li", "ベリリウム": "原子番号4、元素記号Be", "ホウ素": "原子番号5、元素記号B",
        "炭素": "原子番号6、元素記号C", "窒素": "原子番号7、元素記号N", "酸素": "原子番号8、元素記号O", "フッ素": "原子番号9、元素記号F", "ネオン": "原子番号10、元素記号Ne",
        "ナトリウム": "原子番号11、元素記号Na", "マグネシウム": "原子番号12、元素記号Mg", "アルミニウム": "原子番号13、元素記号Al", "ケイ素": "原子番号14、元素記号Si", "リン": "原子番号15、元素記号P",
        "硫黄": "原子番号16、元素記号S", "塩素": "原子番号17、元素記号Cl", "アルゴン": "原子番号18、元素記号Ar", "カリウム": "原子番号19、元素記号K", "カルシウム": "原子番号20、元素記号Ca",
        "イオン結合": "陽イオンと陰イオンの静電気的な引力による結合", "共有結合": "原子同士が価電子を共有してできる結合", "金属結合": "自由電子による金属原子間の結合",
        "同位体": "原子番号が同じで質量数が異なる原子（アイソトープ）", "同素体": "同じ元素からなる単体で性質が異なるもの（SCOP）",
        "酸": "水溶液中で水素イオン(H+)を生じる物質", "塩基": "水溶液中で水酸化物イオン(OH-)を生じる物質", "中和反応": "酸と塩基が反応して水と塩を生じる反応",
        "酸化": "酸素を受け取る、または電子を失う反応", "還元": "酸素を失う、または電子を受け取る反応", "モル(mol)": "物質量の単位", "アボガドロ定数": "6.02×10^23 /mol",
        "単体": "1種類の元素からなる物質", "化合物": "2種類以上の元素からなる物質", "混合物": "2種類以上の純物質が混ざったもの"
    }
    seibutsu_data = {
        "光合成": "植物が光エネルギーを用いて有機物を合成する働き", "呼吸": "酸素を用いて有機物を分解し、ATPを合成する働き", "ATP": "アデノシン三リン酸。生体内のエネルギー通貨",
        "DNA": "デオキシリボ核酸。遺伝情報の本体", "RNA": "リボ核酸", "ミトコンドリア": "呼吸の場となる細胞小器官", "葉緑体": "光合成の場となる細胞小器官",
        "リボソーム": "タンパク質合成の場", "核": "染色体を含む細胞小器官", "細胞膜": "細胞を包む膜", "酵素": "生体内の化学反応を促進する触媒", "アミノ酸": "タンパク質を構成する基本単位",
        "ニューロン": "神経細胞", "ホルモン": "内分泌腺から分泌され、特定の器官の働きを調節する物質", "抗体": "体内に侵入した抗原と特異的に結合するタンパク質（免疫グロブリン）"
    }

    # 社会 (歴史総合・世界史探求・公共)
    rekishi_data = {
        "1789年": "フランス革命が始まった年", "1868年": "明治維新が始まった年", "1914年": "第一次世界大戦が勃発した年", "1939年": "第二次世界大戦が勃発した年", "1945年": "第二次世界大戦が終結した年",
        "産業革命": "18世紀後半にイギリスで始まった、機械制工業への移行", "冷戦": "第二次世界大戦後の、アメリカ中心の資本主義陣営とソ連中心の社会主義陣営の対立",
        "大政奉還": "1867年、徳川慶喜が政権を朝廷に返上した出来事", "王政復古の大号令": "1867年、天皇中心の新政府樹立を宣言した出来事", "日清戦争": "1894年に勃発した日本と清の戦争",
        "日露戦争": "1904年に勃発した日本とロシアの戦争", "五・一五事件": "1932年、海軍青年将校らが犬養毅首相を暗殺した事件", "二・二六事件": "1936年、陸軍青年将校らが起こしたクーデター未遂事件",
        "ポツダム宣言": "1945年、日本が受諾し太平洋戦争が終結した宣言", "サンフランシスコ平和条約": "1951年、日本が主権を回復した条約"
    }
    sekaishi_data = {
        "カエサル": "古代ローマの政治家。「賽は投げられた」", "アウグストゥス": "初代ローマ皇帝（オクタウィアヌス）", "ムハンマド": "イスラーム教の開祖", "チンギス・ハン": "モンゴル帝国の創始者",
        "コロンブス": "1492年、アメリカ大陸（西インド諸島）に到達した人物", "マゼラン": "一行が世界周航を成し遂げた人物", "ルター": "ドイツの宗教改革の中心人物", "ワシントン": "アメリカ合衆国の初代大統領",
        "リンカン": "アメリカ合衆国の第16代大統領。「人民の、人民による、人民のための政治」", "ビスマルク": "ドイツ統一を推進した「鉄血宰相」", "レーニン": "ロシア革命の指導者", "ガンディー": "インド独立運動の指導者。「非暴力・不服従」",
        "ルネサンス": "14〜16世紀にヨーロッパで起きた文化運動。「文芸復興」", "マグナ・カルタ": "1215年、イギリスで王権を制限した大憲章", "権利の章典": "1689年、イギリスの名誉革命後に制定された法律",
        "フランス人権宣言": "1789年、フランス革命において採択された宣言", "ワイマール憲法": "1919年、ドイツで制定された、生存権を初めて保障した憲法"
    }
    koukyou_data = {
        "国会": "国権の最高機関であって、国の唯一の立法機関", "内閣": "行政権を担当する機関", "裁判所": "司法権を担当する機関", "三権分立": "立法・行政・司法の権力を分散させる仕組み",
        "基本的人権の尊重": "日本国憲法の三大原則の一つ（他は国民主権、平和主義）", "国民主権": "国の政治の決定権は国民にあるという原則", "平和主義": "戦争の放棄、戦力の不保持、交戦権の否認",
        "SDGs": "持続可能な開発目標。17の目標からなる", "需要と供給": "市場において価格を決定する基本的な要因", "インフレーション": "物価が継続的に上昇し、貨幣価値が下がる状態",
        "デフレーション": "物価が継続的に下落し、貨幣価値が上がる状態", "日本銀行": "日本の中央銀行", "独占禁止法": "公正かつ自由な競争を促進するための法律",
        "消費税": "商品やサービスの購入に対して課される間接税", "直接税": "税金を納める人と負担する人が同じ税金（所得税など）", "間接税": "税金を納める人と負担する人が異なる税金（消費税など）",
        "国際連合": "1945年、国際平和と安全の維持を目的として設立された国際機関", "安全保障理事会": "国際連合の主要機関の一つ。5つの常任理事国を含む",
        "拒否権": "安全保障理事会の常任理事国が持つ、実質事項の決定を阻止できる権限", "NGO": "非政府組織", "NPO": "非営利組織",
        "グローバリゼーション": "地球規模で人、モノ、カネ、情報が移動し、世界が一体化していく現象", "情報リテラシー": "情報を主体的に選択、評価、活用する能力", "少子高齢化": "子どもの数が減り、高齢者の割合が増える現象", "社会保障制度": "国民の生活の安定を図るための公的な制度（年金、医療、介護など）"
    }

    # 各教科ごとにデータを生成
    generate_knowledge_questions("gendai", "gendai-u1", gendai_data)
    generate_knowledge_questions("gengo", "gengo-u1", koten_data)
    generate_knowledge_questions("ronri_kokugo", "ronri_kokugo-u1", gendai_data) # 現代の国語データ
    generate_knowledge_questions("bungaku", "bungaku-u1", koten_data) # 古典データ
    generate_knowledge_questions("koten", "koten-u1", koten_data)
    
    generate_knowledge_questions("kagaku", "kagaku-u1", kagaku_data)
    generate_knowledge_questions("seibutsu", "seibutsu-u1", seibutsu_data)
    
    generate_knowledge_questions("eigo_c1", "eigo_c1-u1", eigo_data)
    generate_knowledge_questions("eigo_c2", "eigo_c2-u1", eigo_data)
    generate_knowledge_questions("ronri_e1", "ronri_e1-u1", eigo_data)
    generate_knowledge_questions("ronri_e2", "ronri_e2-u1", eigo_data)
    
    generate_knowledge_questions("rekishi", "rekishi-u1", rekishi_data)
    generate_knowledge_questions("sekaishi", "sekaishi-u1", sekaishi_data)
    generate_knowledge_questions("koukyou", "koukyou-u1", koukyou_data)
    
    # 情報・家庭は専用データ
    joho_data = {"URL": "Uniform Resource Locator。Webページの住所", "HTML": "Webページを作成するためのマークアップ言語", "CPU": "中央処理装置。コンピュータの頭脳", "RAM": "ランダムアクセスメモリ。主記憶装置", "ROM": "リードオンリーメモリ。読み出し専用の記憶装置", "OS": "オペレーティングシステム。基本ソフトウェア", "IPアドレス": "インターネット上の住所", "フィッシング詐欺": "偽サイトに誘導して個人情報を盗む詐欺", "マルウェア": "悪意のあるソフトウェアの総称", "LAN": "限定された範囲のネットワーク"}
    katei_data = {"炭水化物": "三大栄養素の一つ。エネルギー源になる", "脂質": "三大栄養素の一つ。エネルギー源になる", "たんぱく質": "三大栄養素の一つ。筋肉や臓器を作る", "ビタミン": "微量で体の調子を整える栄養素", "ミネラル": "無機質とも呼ばれ、骨や歯を作る栄養素", "クーリング・オフ": "一定期間内であれば無条件で契約を解除できる制度", "食中毒": "有害な細菌やウイルスが付着した食品を食べて起こる健康被害", "リサイクル": "廃棄物を資源として再利用すること", "食品ロス": "本来食べられるのに捨てられてしまう食品", "消費者基本法": "消費者の権利の尊重と自立の支援を目的とした法律"}
    
    generate_knowledge_questions("joho", "joho-u1", joho_data)
    generate_knowledge_questions("katei", "katei-u1", katei_data)

    # データを保存
    with open('data/questions.json', 'w', encoding='utf-8') as f:
        json.dump({"questions": questions}, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(questions)} unique questions.")

if __name__ == "__main__":
    run()
