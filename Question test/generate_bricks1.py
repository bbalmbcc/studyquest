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
data = {
    "bricks1-s1u1": [
        ("agree","同意する"),("allow","許す"),("arrive","到着する"),("believe","信じる"),("belong","属する"),
        ("borrow","借りる"),("celebrate","祝う"),("collect","集める"),("compare","比較する"),("complain","不平を言う"),
        ("connect","つなぐ"),("continue","続ける"),("control","支配する"),("correct","正しい"),("count","数える"),
        ("cover","覆う"),("create","創造する"),("cross","横切る"),("decide","決める"),("deliver","届ける"),
    ],
    "bricks1-s1u2": [
        ("depend","頼る"),("describe","描写する"),("design","設計する"),("destroy","破壊する"),("develop","発展させる"),
        ("disappear","消える"),("discover","発見する"),("discuss","議論する"),("divide","分ける"),("doubt","疑う"),
        ("earn","稼ぐ"),("encourage","励ます"),("enter","入る"),("escape","逃げる"),("exchange","交換する"),
        ("exist","存在する"),("expect","期待する"),("experience","経験する"),("explain","説明する"),("express","表現する"),
    ],
    "bricks1-s1u3": [
        ("fail","失敗する"),("feed","食べ物を与える"),("fix","修理する"),("float","浮かぶ"),("flow","流れる"),
        ("follow","従う"),("force","強いる"),("forget","忘れる"),("forgive","許す"),("gather","集まる"),
        ("guess","推測する"),("handle","扱う"),("harm","害を与える"),("hate","憎む"),("hide","隠す"),
        ("hire","雇う"),("hunt","狩る"),("hurry","急ぐ"),("imagine","想像する"),("improve","向上させる"),
    ],
    "bricks1-s1u4": [
        ("include","含む"),("increase","増やす"),("influence","影響を与える"),("insist","主張する"),("introduce","紹介する"),
        ("invent","発明する"),("invite","招待する"),("involve","含む"),("judge","判断する"),("knock","ノックする"),
        ("lack","欠けている"),("lead","導く"),("lend","貸す"),("limit","制限する"),("manage","管理する"),
        ("match","合う"),("measure","測る"),("mention","言及する"),("miss","逃す"),("mix","混ぜる"),
    ],
    "bricks1-s1u5": [
        ("nod","うなずく"),("notice","気づく"),("obey","従う"),("observe","観察する"),("occur","起こる"),
        ("offer","提供する"),("operate","操作する"),("order","命じる"),("owe","借りがある"),("own","所有する"),
        ("participate","参加する"),("perform","演じる"),("permit","許可する"),("pick","選ぶ"),("plant","植える"),
        ("please","喜ばせる"),("point","指さす"),("pour","注ぐ"),("praise","褒める"),("predict","予測する"),
    ],
    "bricks1-s2u1": [
        ("prepare","準備する"),("present","贈る"),("preserve","保存する"),("pretend","ふりをする"),("prevent","防ぐ"),
        ("produce","生産する"),("promise","約束する"),("propose","提案する"),("protect","保護する"),("prove","証明する"),
        ("provide","提供する"),("publish","出版する"),("punish","罰する"),("purchase","購入する"),("raise","上げる"),
        ("realize","気づく"),("receive","受け取る"),("recognize","認識する"),("recommend","推薦する"),("record","記録する"),
    ],
    "bricks1-s2u2": [
        ("reduce","減らす"),("reflect","反映する"),("refuse","断る"),("regard","みなす"),("regret","後悔する"),
        ("reject","拒絶する"),("relate","関係がある"),("release","解放する"),("remain","残る"),("remove","取り除く"),
        ("rent","賃貸する"),("repair","修理する"),("repeat","繰り返す"),("replace","取り替える"),("reply","返事する"),
        ("report","報告する"),("represent","代表する"),("request","要請する"),("require","要求する"),("research","研究する"),
    ],
    "bricks1-s2u3": [
        ("reserve","予約する"),("respond","応答する"),("restore","修復する"),("result","結果として生じる"),("retire","引退する"),
        ("reveal","明らかにする"),("review","復習する"),("reward","報いる"),("rob","奪う"),("satisfy","満足させる"),
        ("save","救う"),("search","探す"),("select","選ぶ"),("separate","分ける"),("serve","仕える"),
        ("settle","定住する"),("shake","振る"),("share","共有する"),("shelter","保護する"),("shift","移す"),
    ],
    "bricks1-s2u4": [
        ("shrink","縮む"),("sigh","ため息をつく"),("signal","合図する"),("solve","解決する"),("sort","分類する"),
        ("spread","広げる"),("steal","盗む"),("store","蓄える"),("struggle","もがく"),("succeed","成功する"),
        ("suffer","苦しむ"),("suggest","提案する"),("supply","供給する"),("support","支える"),("suppose","思う"),
        ("surround","囲む"),("survive","生き残る"),("suspect","疑う"),("swallow","飲み込む"),("sweep","掃く"),
    ],
    "bricks1-s2u5": [
        ("switch","切り替える"),("tend","傾向がある"),("threaten","脅す"),("throw","投げる"),("trade","取引する"),
        ("transfer","移す"),("transform","変える"),("translate","翻訳する"),("transport","輸送する"),("trap","罠にかける"),
        ("treat","扱う"),("trust","信頼する"),("unite","結合する"),("urge","促す"),("vary","異なる"),
        ("vote","投票する"),("wander","さまよう"),("warn","警告する"),("waste","浪費する"),("weigh","重さを量る"),
    ],
    "bricks1-s3u1": [
        ("abandon","捨てる"),("absorb","吸収する"),("accompany","同行する"),("accomplish","成し遂げる"),("accumulate","蓄積する"),
        ("accuse","告発する"),("acquire","獲得する"),("adapt","適応する"),("adjust","調整する"),("admire","称賛する"),
        ("adopt","採用する"),("advocate","主張する"),("afford","余裕がある"),("aid","援助する"),("aim","狙う"),
        ("alter","変える"),("amaze","驚かせる"),("analyze","分析する"),("appeal","訴える"),("apply","応用する"),
    ],
    "bricks1-s3u2": [
        ("appoint","任命する"),("appreciate","感謝する"),("approach","近づく"),("approve","承認する"),("arise","生じる"),
        ("arrange","手配する"),("assign","割り当てる"),("assist","手伝う"),("assume","仮定する"),("assure","保証する"),
        ("attach","取り付ける"),("attempt","試みる"),("attract","引きつける"),("avoid","避ける"),("ban","禁止する"),
        ("bear","耐える"),("blame","非難する"),("bless","祝福する"),("bloom","咲く"),("bore","退屈させる"),
    ],
    "bricks1-s3u3": [
        ("broadcast","放送する"),("burst","爆発する"),("calculate","計算する"),("capture","捕らえる"),("cease","やめる"),
        ("challenge","挑戦する"),("characterize","特徴づける"),("chase","追いかける"),("cheat","だます"),("claim","主張する"),
        ("classify","分類する"),("cling","しがみつく"),("collapse","崩壊する"),("command","命令する"),("commit","犯す"),
        ("communicate","伝える"),("compensate","補償する"),("compete","競争する"),("compose","構成する"),("compromise","妥協する"),
    ],
    "bricks1-s3u4": [
        ("concentrate","集中する"),("conclude","結論づける"),("conduct","行う"),("confess","告白する"),("confirm","確認する"),
        ("confuse","混乱させる"),("conquer","征服する"),("consist","成り立つ"),("construct","建設する"),("consult","相談する"),
        ("consume","消費する"),("contain","含む"),("contest","争う"),("contribute","貢献する"),("convert","変換する"),
        ("convince","説得する"),("cooperate","協力する"),("cope","対処する"),("cultivate","耕す"),("cure","治す"),
    ],
    "bricks1-s3u5": [
        ("dare","あえて～する"),("decay","腐る"),("decline","断る"),("defeat","負かす"),("define","定義する"),
        ("delay","遅らせる"),("demand","要求する"),("demonstrate","実演する"),("deny","否定する"),("deserve","値する"),
        ("desire","望む"),("detect","検出する"),("determine","決心する"),("devote","捧げる"),("differ","異なる"),
        ("diminish","減少する"),("disappoint","失望させる"),("discipline","しつける"),("display","展示する"),("distinguish","区別する"),
    ],
    "bricks1-s4u1": [
        ("distribute","配布する"),("disturb","邪魔する"),("dominate","支配する"),("donate","寄付する"),("drag","引きずる"),
        ("drift","漂う"),("ease","楽にする"),("elaborate","詳しく述べる"),("elect","選挙する"),("eliminate","除去する"),
        ("embrace","抱きしめる"),("emerge","現れる"),("emit","放出する"),("enable","可能にする"),("encounter","遭遇する"),
        ("endure","耐える"),("engage","従事する"),("enhance","高める"),("ensure","確実にする"),("envy","うらやむ"),
    ],
    "bricks1-s4u2": [
        ("equip","装備する"),("establish","設立する"),("estimate","見積もる"),("evaluate","評価する"),("evolve","進化する"),
        ("exaggerate","誇張する"),("examine","調べる"),("exceed","超える"),("exclude","除外する"),("execute","実行する"),
        ("exhibit","展示する"),("expand","拡大する"),("exploit","利用する"),("expose","さらす"),("extend","延長する"),
        ("extract","抽出する"),("fade","色あせる"),("fascinate","魅了する"),("fetch","取ってくる"),("flee","逃げる"),
    ],
    "bricks1-s4u3": [
        ("flourish","繁栄する"),("forbid","禁じる"),("forecast","予報する"),("found","設立する"),("freeze","凍る"),
        ("frighten","怖がらせる"),("fulfill","果たす"),("fund","資金を出す"),("gaze","じっと見る"),("generate","生み出す"),
        ("grab","つかむ"),("grant","与える"),("grasp","つかむ"),("guarantee","保証する"),("harbor","かくまう"),
        ("harvest","収穫する"),("hesitate","ためらう"),("highlight","強調する"),("identify","特定する"),("ignore","無視する"),
    ],
    "bricks1-s4u4": [
        ("illustrate","説明する"),("impose","課す"),("impress","印象づける"),("indicate","示す"),("inhabit","住む"),
        ("inherit","相続する"),("inquire","尋ねる"),("insert","挿入する"),("inspect","検査する"),("install","設置する"),
        ("institute","設立する"),("instruct","指示する"),("insure","保険をかける"),("integrate","統合する"),("intend","意図する"),
        ("interpret","解釈する"),("interrupt","遮る"),("investigate","調査する"),("isolate","孤立させる"),("justify","正当化する"),
    ],
    "bricks1-s4u5": [
        ("launch","発射する"),("lean","もたれる"),("leap","跳ぶ"),("lecture","講義する"),("liberate","解放する"),
        ("load","積む"),("locate","位置する"),("maintain","維持する"),("manufacture","製造する"),("merge","合併する"),
        ("migrate","移住する"),("modify","修正する"),("monitor","監視する"),("motivate","動機づける"),("multiply","増やす"),
        ("negotiate","交渉する"),("neglect","怠る"),("object","反対する"),("obtain","得る"),("occupy","占領する"),
    ],
    "bricks1-s5u1": [
        ("offend","怒らせる"),("oppose","反対する"),("organize","組織する"),("originate","起源を持つ"),("overcome","克服する"),
        ("overlook","見落とす"),("overwhelm","圧倒する"),("pause","一時停止する"),("perceive","知覚する"),("persist","固執する"),
        ("persuade","説得する"),("pledge","誓う"),("polish","磨く"),("possess","所有する"),("postpone","延期する"),
        ("precede","先行する"),("proceed","進む"),("promote","促進する"),("pronounce","発音する"),("provoke","挑発する"),
    ],
    "bricks1-s5u2": [
        ("pursue","追求する"),("qualify","資格を与える"),("quote","引用する"),("recall","思い出す"),("recover","回復する"),
        ("recruit","募集する"),("reform","改革する"),("reinforce","強化する"),("relieve","和らげる"),("rely","頼る"),
        ("remark","述べる"),("remedy","治療する"),("render","与える"),("renew","更新する"),("reproduce","再現する"),
        ("resemble","似ている"),("resign","辞任する"),("resist","抵抗する"),("resolve","解決する"),("restrict","制限する"),
    ],
    "bricks1-s5u3": [
        ("retain","保持する"),("retrieve","取り戻す"),("revise","修正する"),("revolt","反乱を起こす"),("revolve","回転する"),
        ("rid","取り除く"),("sacrifice","犠牲にする"),("scatter","まき散らす"),("seize","つかむ"),("sentence","判決を下す"),
        ("shed","流す"),("simulate","模擬実験する"),("slip","滑る"),("snap","ぱちんと鳴らす"),("soar","舞い上がる"),
        ("speculate","推測する"),("squeeze","絞る"),("stare","じっと見つめる"),("stimulate","刺激する"),("stir","かき混ぜる"),
    ],
    "bricks1-s5u4": [
        ("strain","緊張させる"),("strip","はぎ取る"),("stroke","なでる"),("submit","提出する"),("substitute","代用する"),
        ("subtract","引く"),("summon","召喚する"),("suspend","一時停止する"),("sustain","維持する"),("swing","揺れる"),
        ("sympathize","同情する"),("tackle","取り組む"),("tease","からかう"),("tempt","誘惑する"),("terminate","終わらせる"),
        ("tolerate","許容する"),("trace","たどる"),("transmit","伝える"),("trigger","引き起こす"),("triumph","勝利する"),
    ],
    "bricks1-s5u5": [
        ("undergo","経験する"),("undertake","引き受ける"),("undo","元に戻す"),("unfold","広げる"),("utilize","利用する"),
        ("vow","誓う"),("weed","草を取る"),("wipe","拭く"),("withdraw","引き出す"),("witness","目撃する"),
        ("worship","崇拝する"),("wrap","包む"),("yield","生む"),("acquire","習得する"),("allocate","割り当てる"),
        ("alleviate","軽減する"),("amplify","増幅する"),("anticipate","予期する"),("articulate","はっきり述べる"),("assert","断言する"),
    ],
    "bricks1-s6u1": [
        ("abundance","豊富"),("access","接近"),("achievement","達成"),("advantage","利点"),("agriculture","農業"),
        ("ancestor","先祖"),("anxiety","不安"),("appetite","食欲"),("atmosphere","雰囲気"),("attitude","態度"),
        ("authority","権威"),("basis","基礎"),("boundary","境界"),("burden","負担"),("capacity","能力"),
        ("career","職業"),("ceremony","式典"),("charity","慈善"),("circumstance","状況"),("civilization","文明"),
    ],
    "bricks1-s6u2": [
        ("climate","気候"),("colony","植民地"),("commerce","商業"),("committee","委員会"),("companion","仲間"),
        ("conflict","紛争"),("conscience","良心"),("consequence","結果"),("constitution","憲法"),("controversy","論争"),
        ("corporation","企業"),("creature","生き物"),("crisis","危機"),("criticism","批評"),("currency","通貨"),
        ("decade","10年間"),("democracy","民主主義"),("destiny","運命"),("device","装置"),("dignity","尊厳"),
    ],
    "bricks1-s6u3": [
        ("dimension","次元"),("disaster","災害"),("discipline","規律"),("discrimination","差別"),("disorder","混乱"),
        ("document","文書"),("empire","帝国"),("enterprise","企業"),("enthusiasm","熱意"),("epidemic","流行病"),
        ("essence","本質"),("evidence","証拠"),("evolution","進化"),("exception","例外"),("expense","費用"),
        ("extinction","絶滅"),("facility","施設"),("faculty","能力"),("famine","飢饉"),("fiction","小説"),
    ],
    "bricks1-s6u4": [
        ("fortune","財産"),("fossil","化石"),("foundation","基盤"),("frontier","国境"),("gender","性別"),
        ("glory","栄光"),("gravity","重力"),("habitat","生息地"),("heritage","遺産"),("hormone","ホルモン"),
        ("humanity","人類"),("hypothesis","仮説"),("identity","身元"),("ideology","思想"),("illusion","幻想"),
        ("immigrant","移民"),("immunity","免疫"),("impulse","衝動"),("insight","洞察"),("inspection","検査"),
    ],
    "bricks1-s6u5": [
        ("institution","制度"),("instruction","指示"),("insurance","保険"),("intelligence","知能"),("intention","意図"),
        ("invasion","侵略"),("irrigation","灌漑"),("justice","正義"),("landscape","景観"),("latitude","緯度"),
        ("legislation","法律"),("liberty","自由"),("literacy","読み書き能力"),("luxury","贅沢"),("mankind","人類"),
        ("mechanism","仕組み"),("mercy","慈悲"),("miracle","奇跡"),("monument","記念碑"),("narrative","物語"),
    ],
}

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
