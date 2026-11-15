"""数学・理科（7科目）の高品質問題ジェネレータモジュール。

対象科目:
- math1 (数学Ⅰ): 5単元 × 34問 = 170問
- mathA (数学A): 3単元 × 55問 = 165問
- math2 (数学Ⅱ): 6単元 × 28問 = 168問
- mathB (数学B): 2単元 × 85問 = 170問
- mathC (数学C): 2単元 × 85問 = 170問
- kagaku (化学基礎): 3単元 × 56問 = 168問
- seibutsu (生物基礎): 4単元 × 42問 = 168問
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
import math
import random
import re


# ============================================================
# 共通数式フォーマット・問題登録ヘルパー
# ============================================================

def fmt_poly_terms(terms: list[tuple[int | Fraction, str]]) -> str:
    """(係数, 文字部) のリストを降べき・標準表記の多項式文字列に整形する。"""
    parts: list[str] = []
    for coef, var_part in terms:
        if coef == 0:
            continue
        is_neg = coef < 0
        abs_c = -coef if is_neg else coef
        if isinstance(abs_c, Fraction):
            c_str = str(abs_c.numerator) if abs_c.denominator == 1 else f"({abs_c.numerator}/{abs_c.denominator})"
        else:
            c_str = str(abs_c)

        if var_part:
            body = var_part if abs_c == 1 else f"{c_str}{var_part}"
        else:
            body = c_str

        if not parts:
            parts.append(f"-{body}" if is_neg else body)
        else:
            parts.append(f" - {body}" if is_neg else f" + {body}")
    return "".join(parts) if parts else "0"


def poly_alts(expr: str) -> list[str]:
    """上付き文字（x²・x³など）の表記ゆれ許容リストを生成する。"""
    alts: list[str] = []
    sup = expr.replace("^2", "²").replace("^3", "³").replace("^4", "⁴")
    if sup != expr:
        alts.append(sup)
    return alts


def fmt_frac(val: Fraction | int) -> str:
    """Fraction または整数を既約分数・整数文字列に変換する。"""
    if isinstance(val, int):
        return str(val)
    if val.denominator == 1:
        return str(val.numerator)
    return f"{val.numerator}/{val.denominator}"


def simplify_sqrt(n: int) -> tuple[int, int]:
    """正の整数 n を (外に出る係数 a, ルート内の平方因子なし整数 b) に分解する。"""
    if n < 0:
        raise ValueError(f"負の平方根は扱えません: {n}")
    if n == 0:
        return 0, 1
    out = 1
    rem = n
    d = 2
    while d * d <= rem:
        while rem % (d * d) == 0:
            out *= d
            rem //= d * d
        d += 1
    return out, rem


def fmt_sqrt(coef: int, rad: int) -> str:
    """coef * √rad を簡約した文字列に整形する。"""
    if coef == 0 or rad == 0:
        return "0"
    a, b = simplify_sqrt(rad)
    k = coef * a
    if b == 1:
        return str(k)
    if k == 1:
        return f"√{b}"
    if k == -1:
        return f"-√{b}"
    return f"{k}√{b}"


def fmt_sqrt_frac(coef: int, rad: int, den: int) -> str:
    """(coef * √rad) / den を約分して文字列化する。"""
    if coef == 0 or rad == 0:
        return "0"
    if den < 0:
        coef = -coef
        den = -den
    a, b = simplify_sqrt(rad)
    k = coef * a
    g = math.gcd(abs(k), den)
    k //= g
    den //= g
    if b == 1:
        return str(k) if den == 1 else f"{k}/{den}"
    if k == 1:
        num_str = f"√{b}"
    elif k == -1:
        num_str = f"-√{b}"
    else:
        num_str = f"{k}√{b}"
    return num_str if den == 1 else f"{num_str}/{den}"


def fmt_complex(re_val: int | Fraction, im_val: int | Fraction) -> str:
    """複素数 a + bi を標準的な文字列に整形する。"""
    if isinstance(re_val, int):
        re_val = Fraction(re_val)
    if isinstance(im_val, int):
        im_val = Fraction(im_val)
    if re_val == 0 and im_val == 0:
        return "0"
    if im_val == 0:
        return fmt_frac(re_val)
    abs_im = abs(im_val)
    im_body = "i" if abs_im == 1 else f"{fmt_frac(abs_im)}i"
    if re_val == 0:
        return f"-{im_body}" if im_val < 0 else im_body
    sign = " - " if im_val < 0 else " + "
    return f"{fmt_frac(re_val)}{sign}{im_body}"


def fmt_vec(*coords: int | Fraction) -> str:
    """ベクトル・座標を "(x, y)" 形式で文字列化する。"""
    parts = [fmt_frac(c) if isinstance(c, Fraction) else str(c) for c in coords]
    return "(" + ", ".join(parts) + ")"


def sqrt_alts(expr: str) -> list[str]:
    """平方根の sqrt(...) 記法や小括弧なし表記を許容リストとして返す。"""
    if "√" not in expr:
        return []
    alt1 = re.sub(r"√(\d+)", r"sqrt(\1)", expr)
    return [alt1] if alt1 != expr else []


def chem_alts(expr: str) -> list[str]:
    """化学式の下付き数字（H₂O など）の表記ゆれリストを返す。"""
    sub_map = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    alts: list[str] = []
    # イオン価数（例: SO4^2-）などの上付きではなく通常の化学式数字を下付きに変換
    sub = re.sub(r"(?<=[A-Za-z\)])(\d+)", lambda m: m.group(1).translate(sub_map), expr)
    if sub != expr:
        alts.append(sub)
    return alts


def make_choices(rng: random.Random, answer: str, distractors: list[str]) -> list[str]:
    """正解と異なる3つの誤答を選び、4要素をシャッフルした選択肢リストを返す。"""
    seen = {answer}
    picked: list[str] = []
    for d in distractors:
        if d not in seen:
            seen.add(d)
            picked.append(d)
            if len(picked) == 3:
                break
    if len(picked) < 3:
        raise ValueError(f"選択肢が4つ作れません: answer={answer!r}, distractors={distractors!r}")
    choices = [answer] + picked
    rng.shuffle(choices)
    return choices


class QuestionBank:
    """科目ごとの問題登録と重複・スキーマ検証を担うビルダークラス。"""

    def __init__(self, seed: int = 20261115) -> None:
        self.rng = random.Random(seed)
        self.by_subject: dict[str, list[dict]] = {}
        self.seen_questions: set[str] = set()

    def add(
        self,
        subject_id: str,
        unit_id: str,
        q_type: str,
        difficulty: int,
        question: str,
        answer: str,
        explanation: str,
        choices: list[str] | None = None,
        alt: list[str] | None = None,
    ) -> None:
        """1問をバリデーションのうえ登録する。"""
        if q_type not in {"選択", "記述", "○×"}:
            raise ValueError(f"不正な問題タイプ: {q_type}")
        if difficulty not in {1, 2, 3}:
            raise ValueError(f"不正な難易度: {difficulty}")
        if not question or not answer or not explanation:
            raise ValueError(f"空のフィールドがあります: {subject_id}/{unit_id} q={question!r}")
        if question in self.seen_questions:
            raise ValueError(f"問題文が重複しています: {question!r}")
        self.seen_questions.add(question)

        item: dict = {
            "id": "",  # 最後に科目ごとの連番を採番する
            "subjectId": subject_id,
            "unitId": unit_id,
            "type": q_type,
            "difficulty": difficulty,
            "question": question,
            "answer": str(answer),
            "explanation": explanation,
        }

        if q_type == "選択":
            if not choices or len(choices) != 4 or len(set(choices)) != 4:
                raise ValueError(f"選択問題のchoicesが不正です: {choices!r} (q={question!r})")
            if str(answer) not in choices:
                raise ValueError(f"choicesに正解が含まれていません: ans={answer!r}, choices={choices!r}")
            item["choices"] = [str(c) for c in choices]
        elif q_type == "○×":
            if str(answer) not in {"○", "×"}:
                raise ValueError(f"○×問題の正解は ○ または × のみです: {answer!r}")
        else:
            # 記述問題のみ、必要なら別解リストを付与
            if alt:
                cleaned_alt = []
                seen_alt = {str(answer).replace(" ", "").lower()}
                for a in alt:
                    a_str = str(a)
                    norm = a_str.replace(" ", "").lower()
                    if norm not in seen_alt:
                        seen_alt.add(norm)
                        cleaned_alt.append(a_str)
                if cleaned_alt:
                    item["alternativeAnswers"] = cleaned_alt

        self.by_subject.setdefault(subject_id, []).append(item)

    def add_mc(
        self,
        subject_id: str,
        unit_id: str,
        difficulty: int,
        question: str,
        answer: str,
        distractors: list[str],
        explanation: str,
    ) -> None:
        """4択問題を登録するショートカット。"""
        choices = make_choices(self.rng, str(answer), [str(d) for d in distractors])
        self.add(subject_id, unit_id, "選択", difficulty, question, str(answer), explanation, choices=choices)

    def add_ox(
        self,
        subject_id: str,
        unit_id: str,
        difficulty: int,
        question: str,
        is_true: bool,
        explanation: str,
    ) -> None:
        """○×問題を登録するショートカット。"""
        self.add(subject_id, unit_id, "○×", difficulty, question, "○" if is_true else "×", explanation)

    def add_write(
        self,
        subject_id: str,
        unit_id: str,
        difficulty: int,
        question: str,
        answer: str,
        explanation: str,
        alt: list[str] | None = None,
    ) -> None:
        """記述問題を登録するショートカット。"""
        self.add(subject_id, unit_id, "記述", difficulty, question, str(answer), explanation, alt=alt)

    def build(self) -> list[dict]:
        """全問題をID採番済みの一覧として返す。"""
        result: list[dict] = []
        for sid, items in self.by_subject.items():
            for idx, item in enumerate(items, start=1):
                item["id"] = f"{sid}-{idx:03d}"
                result.append(item)
        return result


# ============================================================
# 1. 数学Ⅰ (math1): 5単元 × 34問 = 170問
# ============================================================

def generate_math1(qb: QuestionBank) -> None:
    sid = "math1"

    # --- math1-u1: 数と式 (34問) ---
    uid = "math1-u1"
    # 1) 式の展開 (記述 5問)
    expand_params = [
        (1, 3, 1, -5, 1),
        (2, -1, 1, 4, 1),
        (3, 2, 2, -3, 2),
        (2, -5, 3, 1, 2),
        (1, -4, 1, 4, 1),
    ]
    for a, b, c, d, diff in expand_params:
        left = fmt_poly_terms([(a, "x"), (b, "")])
        right = fmt_poly_terms([(c, "x"), (d, "")])
        q = f"({left})({right}) を展開せよ。"
        c2, c1, c0 = a * c, a * d + b * c, b * d
        ans = fmt_poly_terms([(c2, "x^2"), (c1, "x"), (c0, "")])
        exp = f"分配法則より、x^2 の係数は {a}×{c}={c2}、x の係数は {a}×({d})+({b})×{c}={c1}、定数項は ({b})×({d})={c0} となり、{ans}。"
        qb.add_write(sid, uid, diff, q, ans, exp, alt=poly_alts(ans))

    # 2) 3次公式の展開・因数分解 (選択 5問)
    factor_items = [
        (1, "x^2 - 7x + 12 を因数分解せよ。", "(x - 3)(x - 4)", ["(x + 3)(x + 4)", "(x - 2)(x - 6)", "(x - 3)(x + 4)"],
         "積が 12、和が -7 となる2数は -3 と -4 である。"),
        (2, "2x^2 + 5x - 3 を因数分解せよ。", "(2x - 1)(x + 3)", ["(2x + 1)(x - 3)", "(2x - 3)(x + 1)", "(x - 1)(2x + 3)"],
         "たすき掛けにより、2×3 + (-1)×1 = 5 となるため (2x - 1)(x + 3)。"),
        (2, "6x^2 - 7x - 5 を因数分解せよ。", "(2x + 1)(3x - 5)", ["(2x - 1)(3x + 5)", "(6x + 1)(x - 5)", "(3x + 1)(2x - 5)"],
         "たすき掛けにより、2×(-5) + 1×3 = -7 となるため (2x + 1)(3x - 5)。"),
        (2, "x^3 + 8 を因数分解せよ。", "(x + 2)(x^2 - 2x + 4)", ["(x + 2)(x^2 + 2x + 4)", "(x - 2)(x^2 + 2x + 4)", "(x + 2)^3"],
         "公式 a^3 + b^3 = (a + b)(a^2 - ab + b^2) に a=x, b=2 を代入する。"),
        (3, "x^4 - 5x^2 + 4 を実数の範囲で因数分解せよ。", "(x - 1)(x + 1)(x - 2)(x + 2)", ["(x^2 - 1)(x^2 - 4)", "(x - 1)^2(x - 2)^2", "(x^2 + 1)(x^2 - 4)"],
         "x^2 = t とおくと (t - 1)(t - 4) = (x^2 - 1)(x^2 - 4) となり、さらにそれぞれ和と差の積に分解できる。"),
    ]
    for diff, q, ans, dist, exp in factor_items:
        qb.add_mc(sid, uid, diff, q, ans, dist, exp)

    # 3) 対称式の値 (記述 4問)
    sym_params = [
        (5, 3, "x^2 + y^2", 5**2 - 2 * 3, 2, "(x+y)^2 - 2xy = 5^2 - 2×3 = 19"),
        (4, 2, "x^3 + y^3", 4**3 - 3 * 4 * 2, 3, "(x+y)^3 - 3xy(x+y) = 64 - 24 = 40"),
        (6, 7, "x^2 + y^2", 6**2 - 2 * 7, 2, "(x+y)^2 - 2xy = 36 - 14 = 22"),
        (-3, -4, "x^2 - xy + y^2", (-3)**2 - 3 * (-4), 3, "(x+y)^2 - 3xy = 9 + 12 = 21"),
    ]
    for s, p, expr, ans_val, diff, exp in sym_params:
        q = f"x + y = {s}, xy = {p} のとき、{expr} の値は？"
        qb.add_write(sid, uid, diff, q, str(ans_val), exp)

    # 4) 平方根・有理化・二重根号 (選択 4問 + 記述 2問)
    rad_mc = [
        (1, "√48 + √27 を簡単にすると？", "7√3", ["7√6", "5√3", "12√3"], "√48 = 4√3, √27 = 3√3 より、4√3 + 3√3 = 7√3。"),
        (2, "1 / (√5 - √3) の分母を有理化すると？", "(√5 + √3)/2", ["(√5 - √3)/2", "√5 + √3", "(√5 + √3)/8"],
         "分母・分子に √5 + √3 を掛けると (√5 + √3)/(5 - 3) = (√5 + √3)/2。"),
        (3, "二重根号 √(7 + 2√10) を簡単にすると？", "√5 + √2", ["√7 + √10", "√5 - √2", "2√5 + √2"],
         "和が 7、積が 10 となる2数は 5 と 2 なので √(5) + √(2)。"),
        (3, "二重根号 √(9 - 2√14) を簡単にすると？", "√7 - √2", ["√2 - √7", "√7 + √2", "3 - √2"],
         "和が 9、積が 14 となる2数は 7 と 2 で、√7 > √2 より √7 - √2。"),
    ]
    for diff, q, ans, dist, exp in rad_mc:
        qb.add_mc(sid, uid, diff, q, ans, dist, exp)
    qb.add_write(sid, uid, 2, "x = (√7 + √3)/2, y = (√7 - √3)/2 のとき、xy の値は？", "1",
                 "xy = {(√7)^2 - (√3)^2} / 4 = (7 - 3)/4 = 1。")
    qb.add_write(sid, uid, 2, "1 / (√6 + √5) + 1 / (√6 - √5) の値を求めよ。", "2√6",
                 "有理化すると (√6 - √5) + (√6 + √5) = 2√6。", alt=["2sqrt(6)"])

    # 5) 絶対値・実数 (記述 3問 + 選択 3問 + ○× 3問)
    qb.add_write(sid, uid, 2, "方程式 |x - 3| = 5 の2つの解の和は？", "6", "x - 3 = ±5 より x = 8, -2。和は 8 + (-2) = 6。")
    qb.add_write(sid, uid, 2, "|2 - √7| + |3 - √7| の値を簡単にせよ（整数で答えよ）。", "1",
                 "2 < √7 < 3 より 2 - √7 < 0, 3 - √7 > 0。よって (√7 - 2) + (3 - √7) = 1。")
    qb.add_write(sid, uid, 3, "不等式 |2x - 1| < 5 を満たす整数 x は何個あるか？", "4",
                 "-5 < 2x - 1 < 5 より -4 < 2x < 6、すなわち -2 < x < 3。満たす整数は -1, 0, 1, 2 の4個。", alt=["4個"])

    qb.add_mc(sid, uid, 1, "循環小数 0.363636... を既約分数で表すと？", "4/11", ["9/25", "3/8", "36/99"],
              "x = 0.3636... とおくと 100x - x = 36 より 99x = 36、x = 4/11。")
    qb.add_mc(sid, uid, 2, "連立不等式 2x - 1 >= 3 かつ 3x + 1 < 13 の解は？", "2 <= x < 4",
              ["2 < x <= 4", "1 <= x < 4", "2 <= x < 5"],
              "2x >= 4 より x >= 2、3x < 12 より x < 4。共通範囲は 2 <= x < 4。")
    qb.add_mc(sid, uid, 3, "不等式 x - a < 3 を満たす最大の整数 x が 5 であるとき、定数 a の値の範囲は？", "2 < a <= 3",
              ["2 <= a < 3", "2 < a < 3", "1 < a <= 2"],
              "x < a + 3 の最大整数が 5 となる条件は 5 < a + 3 <= 6、すなわち 2 < a <= 3。")

    qb.add_ox(sid, uid, 1, "無理数と無理数の和は必ず無理数になる。", False,
              "反例: √2 + (-√2) = 0 は有理数になるため偽。")
    qb.add_ox(sid, uid, 1, "単項式 3x^2 y^3 の次数は 5 である。", True,
              "掛け合わされている文字の個数は x が2個、y が3個で合計5個のため次数は 5。")
    qb.add_ox(sid, uid, 2, "任意の実数 a に対して √(a^2) = a が成り立つ。", False,
              "a < 0 のときは √(a^2) = -a となるため偽。正しくは √(a^2) = |a|。")

    # 1次不等式の整数解など残り 5問 (計34問)
    ineq_params = [
        (3, 1, 16, 1, "最大"),  # 3x + 1 <= 16 -> x <= 5
        (4, -3, 17, 2, "最大"), # 4x - 3 < 17 -> x < 5 -> max 4
        (2, 5, 11, 1, "最小"),  # 2x + 5 >= 11 -> x >= 3
        (5, -2, 18, 2, "最小"), # 5x - 2 > 18 -> x > 4 -> min 5
    ]
    for a, b, rhs, mode, label in ineq_params:
        op = "<=" if mode == 1 and label == "最大" else ("<" if label == "最大" else (">=" if mode == 1 else ">"))
        expr = fmt_poly_terms([(a, "x"), (b, "")])
        if label == "最大":
            val = math.floor((rhs - b) / a) if op == "<=" else math.ceil((rhs - b) / a) - 1
        else:
            val = math.ceil((rhs - b) / a) if op == ">=" else math.floor((rhs - b) / a) + 1
        q = f"1次不等式 {expr} {op} {rhs} を満たす{label}の整数 x の値は？"
        exp = f"{a}x {op} {rhs - b} より、満たす{label}の整数は {val}。"
        qb.add_write(sid, uid, 1 if mode == 1 else 2, q, str(val), exp)
    qb.add_mc(sid, uid, 2, "多項式 2x^3 - 5x^2y + 4y^2 - 7 を y に着目したときの定数項は？", "2x^3 - 7",
              ["-7", "4y^2 - 7", "2x^3"], "y を含まない項をすべて集めると 2x^3 - 7 となる。")

    # --- math1-u2: 集合と命題 (34問) ---
    uid = "math1-u2"
    # 1) 集合の演算・部分集合・要素の個数 (記述 5問 + 選択 5問)
    set_specs = [
        ({1, 2, 3, 4, 5}, {2, 4, 6, 8}, "∩", "sum", 1),
        ({1, 3, 5, 7, 9}, {2, 3, 5, 7}, "∪", "len", 1),
        ({1, 2, 4, 8}, {2, 3, 4, 6}, "∪", "sum", 2),
        ({1, 2, 3, 6, 9}, {3, 6, 9, 12}, "∩", "len", 1),
        ({2, 4, 6, 8, 10}, {4, 8, 12}, "∩", "sum", 2),
    ]
    for a_set, b_set, op, kind, diff in set_specs:
        res = (a_set & b_set) if op == "∩" else (a_set | b_set)
        a_str = "{" + ", ".join(map(str, sorted(a_set))) + "}"
        b_str = "{" + ", ".join(map(str, sorted(b_set))) + "}"
        r_str = "{" + ", ".join(map(str, sorted(res))) + "}"
        if kind == "len":
            ans = len(res)
            q = f"A = {a_str}, B = {b_str} のとき、A{op}B の要素の個数は？"
            exp = f"A{op}B = {r_str} なので、要素数は {ans} 個。"
        else:
            ans = sum(res)
            q = f"A = {a_str}, B = {b_str} のとき、A{op}B に属するすべての要素の和は？"
            exp = f"A{op}B = {r_str} なので、和は {ans}。"
        qb.add_write(sid, uid, diff, q, str(ans), exp)

    # 補集合・部分集合・個数 (選択 5問)
    qb.add_mc(sid, uid, 1, "集合 A = {1, 2, 3} の部分集合（空集合∅および A 自身も含む）は全部で何個あるか？", "8個",
              ["6個", "7個", "9個"], "各要素が入る・入らないの2通りずつあるため 2^3 = 8 個。")
    qb.add_mc(sid, uid, 2, "全体集合 U = {1, 2, 3, 4, 5, 6}、A = {1, 2, 3}、B = {2, 4, 6} のとき、Ā ∩ B は？", "{4, 6}",
              ["{2}", "{1, 3}", "{5}"], "Ā = {4, 5, 6} と B = {2, 4, 6} の共通部分は {4, 6}。")
    qb.add_mc(sid, uid, 2, "全体集合 U = {x | x は10以下の自然数}、A = {2の倍数}、B = {3の倍数} のとき、(A∪B) の補集合は？", "{1, 5, 7}",
              ["{1, 5, 7, 9}", "{5, 7}", "{1, 7}"], "A∪B = {2, 3, 4, 6, 8, 9, 10} なので、U からこれらを除くと {1, 5, 7}。")
    qb.add_mc(sid, uid, 3, "全体集合 U の部分集合 A, B について、n(U)=50, n(A)=28, n(B)=22, n(A∩B)=10 のとき、n(Ā∩B̄) は？", "10",
              ["0", "20", "40"], "n(A∪B) = 28 + 22 - 10 = 40。ド・モルガンの法則より n(Ā∩B̄) = n(U) - n(A∪B) = 50 - 40 = 10。")
    qb.add_mc(sid, uid, 3, "集合 A = {x | -1 <= x <= 3}, B = {x | 1 < x < 5} について、A∩B を表すのはどれか？", "{x | 1 < x <= 3}",
              ["{x | 1 <= x <= 3}", "{x | -1 <= x < 5}", "{x | 1 < x < 3}"], "数直線で共通部分をとると左端 1 は含まず、右端 3 は含む。")

    # 2) 必要条件・十分条件 (選択 10問)
    ns_choices = [
        "必要十分条件である",
        "十分条件であるが、必要条件ではない",
        "必要条件であるが、十分条件ではない",
        "必要条件でも十分条件でもない",
    ]
    ns_items = [
        (1, "x = 2 は、x^2 = 4 であるための何条件か？（x は実数）", 1,
         "x=2 ⇒ x^2=4 は真だが、x^2=4 ⇒ x=2 は反例 x=-2 があり偽。よって十分条件であるが必要条件ではない。"),
        (1, "x^2 = 9 は、x = 3 であるための何条件か？（x は実数）", 2,
         "x^2=9 ⇒ x=3 は反例 x=-3 で偽、x=3 ⇒ x^2=9 は真。よって必要条件であるが十分条件ではない。"),
        (2, "ab = 0 は、a = 0 かつ b = 0 であるための何条件か？（a, b は実数）", 2,
         "a=0かつb=0 ⇒ ab=0 は真だが、ab=0 は片方のみ0でも成り立つため逆は偽。"),
        (2, "a^2 + b^2 = 0 は、a = 0 かつ b = 0 であるための何条件か？（a, b は実数）", 0,
         "実数では a^2>=0, b^2>=0 より a^2+b^2=0 ⇔ a=0かつb=0 となり必要十分条件。"),
        (2, "x > 3 は、x > 1 であるための何条件か？（x は実数）", 1,
         "x>3 ⇒ x>1 は真だが、x>1 ⇒ x>3 は反例 x=2 で偽。"),
        (2, "自然数 n が 6 の倍数であることは、n が 3 の倍数であるための何条件か？", 1,
         "6の倍数 ⇒ 3の倍数は真、3の倍数 ⇒ 6の倍数は反例 n=3 で偽。"),
        (2, "x > 0 かつ y > 0 は、xy > 0 であるための何条件か？（x, y は実数）", 1,
         "x>0かつy>0 ⇒ xy>0 は真だが、x=-1, y=-1 のとき xy=1>0 なので逆は偽。"),
        (3, "x + y > 0 は、xy > 0 であるための何条件か？（x, y は実数）", 3,
         "x=3, y=-1 で x+y>0 だが xy<0。x=-1, y=-2 で xy>0 だが x+y<0。どちらも成り立たない。"),
        (2, "△ABC が正三角形であることは、△ABC が二等辺三角形であるための何条件か？", 1,
         "正三角形なら必ず二等辺三角形だが、二等辺三角形でも正三角形とは限らない。"),
        (3, "|a| + |b| = 0 は、ab = 0 であるための何条件か？（a, b は実数）", 1,
         "|a|+|b|=0 ⇔ a=0かつb=0 ⇒ ab=0 は真。逆は a=0, b=1 で偽。"),
    ]
    for diff, q, ans_idx, exp in ns_items:
        ans = ns_choices[ans_idx]
        dist = [c for i, c in enumerate(ns_choices) if i != ans_idx]
        qb.add_mc(sid, uid, diff, q, ans, dist, exp)

    # 3) 命題の真偽 (○× 6問) + 集合の基本 (○× 4問)
    ox_u2 = [
        (1, "空集合 ∅ は、すべての集合の部分集合である。", True, "定義より、空集合 ∅ は任意の集合の部分集合とみなす。"),
        (1, "集合 A = {1, 2, 3} について、{1} ∈ A と表記するのは正しい。", False, "{1} は集合なので {1} ⊂ A が正しい。要素の帰属は 1 ∈ A と書く。"),
        (2, "命題「n が素数ならば、n は奇数である」は真である。", False, "反例 n = 2 がある（2 は唯一の偶数の素数）。よって偽。"),
        (2, "命題「x^2 - 4 = 0 ならば x = 2 である」の反例は x = -2 である。", True, "(-2)^2 - 4 = 0 を満たすが x = 2 ではないため反例となる。"),
        (2, "命題「実数 x, y について、x + y が有理数ならば x, y はともに有理数である」は真である。", False, "反例 x = √2, y = -√2 のとき、x + y = 0（有理数）となる。"),
        (3, "命題「実数 x について、x^2 = 1 ならば x^3 = 1 である」は偽である。", True, "x = -1 のとき x^2 = 1 だが x^3 = -1 ≠ 1 なので偽であるという記述は正しい。"),
        (2, "条件「x < 2 または x >= 5」の否定は「2 <= x < 5」である。", True, "ド・モルガンの法則により、「AまたはB」の否定は「Aでない かつ Bでない」となる。"),
        (2, "元の命題が真であるとき、その「逆」も必ず真になる。", False, "元の命題と「対偶」の真偽は一致するが、「逆」と「裏」の真偽は元の命題と一致するとは限らない。"),
        (1, "ド・モルガンの法則により、(A∩B) の補集合は Ā∪B̄ に等しい。", True, "∩ と ∪ が反転し、それぞれに補集合がつく。"),
        (3, "命題「すべての実数 x について x^2 + 1 > 0」の否定は「ある実数 x について x^2 + 1 <= 0」である。", True, "「すべての」の否定は「ある〜（少なくとも1つの〜）」に変わり、不等号も否定される。"),
    ]
    for diff, q, is_t, exp in ox_u2:
        qb.add_ox(sid, uid, diff, q, is_t, exp)

    # 4) 逆・裏・対偶・否定 (選択 4問)
    qb.add_mc(sid, uid, 1, "命題「x = 1 ならば x^2 = 1」の対偶はどれか？", "x^2 ≠ 1 ならば x ≠ 1",
              ["x^2 = 1 ならば x = 1", "x ≠ 1 ならば x^2 ≠ 1", "x ≠ 1 ならば x^2 = 1"],
              "p ⇒ q の対偶は (not q) ⇒ (not p) である。")
    qb.add_mc(sid, uid, 2, "条件「x > 0 かつ y <= 2」の否定はどれか？", "x <= 0 または y > 2",
              ["x <= 0 かつ y > 2", "x < 0 または y >= 2", "x <= 0 または y >= 2"],
              "「かつ」は「または」に反転し、各不等号の向きと等号の有無が逆転する。")
    qb.add_mc(sid, uid, 2, "命題「n^2 が偶数ならば n は偶数である（n は整数）」を証明するとき、どの命題を使うと簡潔か？",
              "対偶「n が奇数ならば n^2 は奇数である」",
              ["逆「n が偶数ならば n^2 は偶数である」", "裏「n^2 が奇数ならば n は奇数である」", "否定「n^2 が偶数かつ n が奇数」"],
              "元の命題と対偶は真偽が一致するため、対偶「n = 2k+1 ⇒ n^2 = 2(2k^2+2k)+1」を示すと容易。")
    qb.add_mc(sid, uid, 3, "「少なくとも一方は 3 の倍数である」の否定はどれか？", "どちらも 3 の倍数ではない",
              ["少なくとも一方は 3 の倍数ではない", "両方とも 3 の倍数である", "一方は 3 の倍数で他方は異なる"],
              "「少なくとも一方〜」は「AまたはB」と同値なので、否定は「Aでない かつ Bでない」＝どちらも〜でない。")

    # --- math1-u3: 二次関数 (34問) ---
    uid = "math1-u3"
    # 1) 平方完成・頂点 (記述 4問 + 選択 3問)
    vertex_params = [
        (1, -6, 11, 1, "記述"),
        (1, 4, -3, 1, "記述"),
        (2, -8, 5, 2, "記述"),
        (-1, 6, -4, 2, "記述"),
        (3, 12, 7, 2, "選択"),
        (-2, -8, 1, 2, "選択"),
        (2, 4, -5, 1, "選択"),
    ]
    for a, b, c, diff, qt in vertex_params:
        # y = a(x + b/(2a))^2 + c - b^2/(4a)
        p = Fraction(-b, 2 * a)
        q_val = Fraction(c) - Fraction(b * b, 4 * a)
        func_str = fmt_poly_terms([(a, "x^2"), (b, "x"), (c, "")])
        ans = fmt_vec(p, q_val)
        exp = f"平方完成すると y = {a}(x - ({fmt_frac(p)}))^2 + ({fmt_frac(q_val)}) となるため頂点は {ans}。"
        if qt == "記述":
            qb.add_write(sid, uid, diff, f"2次関数 y = {func_str} の頂点の座標を求めよ。", ans, exp)
        else:
            dist = [fmt_vec(-p, q_val), fmt_vec(p, -q_val), fmt_vec(p, q_val + 2)]
            qb.add_mc(sid, uid, diff, f"2次関数 y = {func_str} の頂点の座標はどれか？", ans, dist, exp)

    # 2) 平行移動・対称移動 (選択 4問 + 記述 2問)
    qb.add_mc(sid, uid, 1, "放物線 y = 2x^2 を x 軸方向に 3、y 軸方向に -1 だけ平行移動した放物線の方程式は？",
              "y = 2(x - 3)^2 - 1",
              ["y = 2(x + 3)^2 - 1", "y = 2(x - 3)^2 + 1", "y = 2(x + 3)^2 + 1"],
              "x を x - 3 に、y を y - (-1) に置き換えるため y = 2(x - 3)^2 - 1。")
    qb.add_mc(sid, uid, 2, "放物線 y = x^2 - 4x + 5 を x 軸に関して対称移動した放物線の方程式は？",
              "y = -x^2 + 4x - 5",
              ["y = x^2 + 4x + 5", "y = -x^2 - 4x + 5", "y = -x^2 + 4x + 5"],
              "x 軸対称移動では y を -y に置き換えるため、-y = x^2 - 4x + 5 より y = -x^2 + 4x - 5。")
    qb.add_mc(sid, uid, 2, "放物線 y = x^2 - 2x + 3 を y 軸に関して対称移動した放物線の方程式は？",
              "y = x^2 + 2x + 3",
              ["y = -x^2 + 2x - 3", "y = x^2 - 2x - 3", "y = -x^2 - 2x + 3"],
              "y 軸対称移動では x を -x に置き換えるため y = (-x)^2 - 2(-x) + 3 = x^2 + 2x + 3。")
    qb.add_mc(sid, uid, 3, "放物線 y = x^2 - 6x + 4 を原点に関して対称移動した放物線の頂点は？",
              "(-3, 5)", ["(3, -5)", "(-3, -5)", "(3, 5)"],
              "元の頂点は (3, -5)。原点対称移動により x, y の符号がともに反転し (-3, 5) になる。")
    qb.add_write(sid, uid, 2, "放物線 y = x^2 + 2x + 3 を平行移動して、頂点が (4, -2) になるようにしたとき、x 軸方向の移動量は？", "5",
                 "元の頂点は (-1, 2)。(-1) から 4 への移動量は 4 - (-1) = 5。")
    qb.add_write(sid, uid, 2, "放物線 y = x^2 - 4x + 1 を x 軸方向に 1、y 軸方向に 3 平行移動した放物線の y 切片は？", "9",
                 "元の頂点は (2, -3)。移動後の頂点は (3, 0) なので y = (x - 3)^2 = x^2 - 6x + 9。y 切片は 9。")

    # 3) 定義域付きの最大値・最小値 (記述 5問 + 選択 2問)
    minmax_specs = [
        (1, -4, 5, 0, 3, "最小値", 2),
        (1, -4, 5, 0, 3, "最大値", 2),
        (-1, 6, -2, 1, 4, "最大値", 2),
        (2, -8, 3, 3, 5, "最小値", 3),
        (-2, 4, 1, -2, 0, "最小値", 3),
    ]
    for a, b, c, lo, hi, target, diff in minmax_specs:
        def fval(xv: Fraction) -> Fraction:
            return a * xv * xv + b * xv + c
        axis = Fraction(-b, 2 * a)
        pts = [Fraction(lo), Fraction(hi)]
        if lo <= axis <= hi:
            pts.append(axis)
        vals = [fval(x) for x in pts]
        ans_v = min(vals) if target == "最小値" else max(vals)
        func_str = fmt_poly_terms([(a, "x^2"), (b, "x"), (c, "")])
        q = f"2次関数 y = {func_str} ({lo} <= x <= {hi}) の{target}を求めよ。"
        exp = f"軸は x = {fmt_frac(axis)}。端点と（範囲内にあれば）頂点での値を比較すると{target}は {fmt_frac(ans_v)}。"
        qb.add_write(sid, uid, diff, q, fmt_frac(ans_v), exp)

    qb.add_mc(sid, uid, 3, "y = x^2 - 2ax + 1 (0 <= x <= 2) の最小値が a = 3 のときどうなるか？",
              "x = 2 で最小値 5 - 4a（a=3 なら -7）",
              ["x = a で最小値 1 - a^2", "x = 0 で最小値 1", "x = 1 で最小値 2 - 2a"],
              "a = 3 のとき軸 x = 3 は定義域 [0, 2] の右側にあるため、右端 x = 2 で最小となり 4 - 4a + 1 = -7。")
    qb.add_mc(sid, uid, 2, "2次関数 y = -x^2 + 4x + k の最大値が 10 であるとき、定数 k の値は？", "6",
              ["4", "8", "14"], "y = -(x - 2)^2 + 4 + k より最大値は 4 + k = 10。よって k = 6。")

    # 4) 判別式・x軸との共有点・2次方程式 (記述 4問 + 選択 3問 + ○× 2問)
    qb.add_write(sid, uid, 1, "2次方程式 x^2 - 5x + 6 = 0 の2つの解の積は？", "6", "因数分解 (x - 2)(x - 3) = 0 より解は 2, 3。積は 6。")
    qb.add_write(sid, uid, 2, "2次方程式 2x^2 - 3x + k = 0 が重解をもつとき、k の値は？", "9/8",
                 "判別式 D = (-3)^2 - 4(2)k = 9 - 8k = 0 より k = 9/8。")
    qb.add_write(sid, uid, 2, "放物線 y = x^2 - 6x + m が x 軸と接するとき、定数 m の値は？", "9",
                 "D/4 = (-3)^2 - m = 9 - m = 0 より m = 9。")
    qb.add_write(sid, uid, 3, "放物線 y = x^2 - 5x + 4 が x 軸から切り取る線分の長さは？", "3",
                 "x^2 - 5x + 4 = 0 の解は x = 1, 4。切り取る長さは 4 - 1 = 3。")
    qb.add_mc(sid, uid, 1, "2次関数 y = x^2 - 4x + 5 のグラフと x 軸との共有点の個数は？", "0個",
              ["1個", "2個", "3個"], "D/4 = (-2)^2 - 5 = -1 < 0 なので x 軸と共有点をもたない。")
    qb.add_mc(sid, uid, 2, "2次方程式 x^2 + kx + 4 = 0 が異なる2つの実数解をもつような定数 k の範囲は？",
              "k < -4, 4 < k", ["-4 < k < 4", "k <= -4, 4 <= k", "k > 4"],
              "D = k^2 - 16 > 0 より (k - 4)(k + 4) > 0、よって k < -4, 4 < k。")
    qb.add_mc(sid, uid, 3, "放物線 y = x^2 + ax + b が2点 (1, 0), (3, 0) を通るとき、(a, b) は？", "(-4, 3)",
              ["(4, 3)", "(-4, -3)", "(2, -3)"], "y = (x - 1)(x - 3) = x^2 - 4x + 3 より a = -4, b = 3。")
    qb.add_ox(sid, uid, 1, "2次関数 y = ax^2 + bx + c (a > 0) のグラフは下に凸である。", True,
              "x^2 の係数 a が正なら下に凸、負なら上に凸となる。")
    qb.add_ox(sid, uid, 2, "2次不等式 x^2 + 1 < 0 の解は「すべての実数」である。", False,
              "実数 x に対して常に x^2 + 1 >= 1 > 0 なので、解は「ない（空集合）」。")

    # 5) 2次不等式 (選択 3問 + ○× 2問)
    qb.add_mc(sid, uid, 1, "2次不等式 x^2 - 5x + 4 < 0 の解は？", "1 < x < 4",
              ["x < 1, 4 < x", "1 <= x <= 4", "-4 < x < -1"], "(x - 1)(x - 4) < 0 より 1 < x < 4。")
    qb.add_mc(sid, uid, 2, "2次不等式 x^2 - 6x + 9 > 0 の解は？", "x ≠ 3 のすべての実数",
              ["すべての実数", "解なし", "x > 3"], "(x - 3)^2 > 0 は x = 3 のとき 0 となり成り立たないため x ≠ 3 のすべての実数。")
    qb.add_mc(sid, uid, 3, "すべての実数 x に対して x^2 + 2kx + k + 6 > 0 が成り立つような定数 k の範囲は？",
              "-2 < k < 3", ["k < -2, 3 < k", "-3 < k < 2", "-2 <= k <= 3"],
              "下に凸なので D/4 = k^2 - (k + 6) < 0 が条件。(k - 3)(k + 2) < 0 より -2 < k < 3。")
    qb.add_ox(sid, uid, 2, "2次不等式 x^2 - 4x + 4 <= 0 の解は x = 2 のみである。", True,
              "(x - 2)^2 <= 0 は (x - 2)^2 >= 0 より x - 2 = 0 すなわち x = 2 のみ満たす。")
    qb.add_ox(sid, uid, 3, "2次方程式 ax^2 + bx + c = 0 が実数解を持たないとき、放物線 y = ax^2 + bx + c は必ず x 軸より上側にある。", False,
              "a < 0（上に凸）の場合は常に x 軸より下側にあるため、a > 0 かどうかで決まる。")

    # --- math1-u4: 図形と計量 (34問) ---
    uid = "math1-u4"
    # 1) 有名角の三角比 (選択 4問 + 記述 2問)
    trig_vals = [
        ("sin 120°", "√3/2", ["1/2", "-1/2", "-√3/2"], 1, "120° のとき第2象限なので sin は正で √3/2。"),
        ("cos 135°", "-√2/2", ["√2/2", "-1/2", "1/2"], 1, "135° のとき第2象限なので cos は負で -1/√2 = -√2/2。"),
        ("tan 150°", "-√3/3", ["√3/3", "-√3", "√3"], 2, "150° では x = -√3, y = 1 より tan 150° = -1/√3 = -√3/3。"),
        ("cos 150°", "-√3/2", ["√3/2", "-1/2", "-√2/2"], 1, "cos 150° = -cos 30° = -√3/2。"),
    ]
    for expr, ans, dist, diff, exp in trig_vals:
        qb.add_mc(sid, uid, diff, f"{expr} の値はどれか？", ans, dist, exp)
    qb.add_write(sid, uid, 1, "cos 120° の値を分数で答えよ。", "-1/2", "cos 120° = -cos 60° = -1/2。")
    qb.add_write(sid, uid, 1, "tan 135° の値は？", "-1", "tan 135° = -tan 45° = -1。")

    # 2) 三角比の相互関係 (記述 4問 + 選択 3問) - ピタゴラス数 (3,4,5), (5,12,13), (8,15,17), (7,24,25) を活用
    pyth = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25)]
    for idx_p, (a, b, c) in enumerate(pyth):
        # sinθ = a/c (0°<θ<90°) のとき cosθ または tanθ
        s_str = f"{a}/{c}"
        if idx_p % 2 == 0:
            ans = f"{b}/{c}"
            q = f"0° < θ < 90° で sinθ = {s_str} のとき、cosθ の値は？"
            exp = f"cos^2θ = 1 - ({a}/{c})^2 = ({b}/{c})^2。θは鋭角なので cosθ = {b}/{c}。"
        else:
            ans = fmt_frac(Fraction(a, b))
            q = f"0° < θ < 90° で sinθ = {s_str} のとき、tanθ の値は？"
            exp = f"cosθ = {b}/{c} より tanθ = sinθ/cosθ = {a}/{b}。"
        qb.add_write(sid, uid, 2, q, ans, exp)

    qb.add_mc(sid, uid, 2, "0° < θ < 180° で cosθ = -3/5 のとき、sinθ の値は？", "4/5",
              ["-4/5", "3/4", "16/25"], "0° < θ < 180° では常に sinθ > 0。sinθ = √(1 - 9/25) = 4/5。")
    qb.add_mc(sid, uid, 2, "0° < θ < 90° で tanθ = 2 のとき、cos^2θ の値は？", "1/5",
              ["2/5", "4/5", "1/3"], "1 + tan^2θ = 1/cos^2θ より 1 + 4 = 1/cos^2θ、よって cos^2θ = 1/5。")
    qb.add_mc(sid, uid, 3, "0° < θ < 90° で sinθ + cosθ = √2 のとき、sinθ cosθ の値は？", "1/2",
              ["1", "1/4", "√2/2"], "両辺を2乗すると 1 + 2sinθcosθ = 2 より sinθcosθ = 1/2。")

    # 3) 正弦定理 (記述 3問 + 選択 3問)
    sine_items = [
        ("△ABC において a = 6, A = 30° のとき、外接円の半径 R は？", "6",
         "2R = a / sinA = 6 / (1/2) = 12 より R = 6。", 1),
        ("△ABC において b = 4√2, B = 45° のとき、外接円の半径 R は？", "4",
         "2R = 4√2 / (1/√2) = 8 より R = 4。", 2),
        ("△ABC において c = 6√3, C = 120° のとき、外接円の半径 R は？", "6",
         "2R = 6√3 / (√3/2) = 12 より R = 6。", 2),
    ]
    for q, ans, exp, diff in sine_items:
        qb.add_write(sid, uid, diff, q, ans, exp)

    qb.add_mc(sid, uid, 2, "△ABC において A = 45°, B = 60°, a = 2 のとき、辺 b の長さは？", "√6",
              ["2√3", "√3", "2√6"], "正弦定理より b = a sinB / sinA = 2 × (√3/2) / (1/√2) = √6。")
    qb.add_mc(sid, uid, 2, "△ABC において B = 30°, C = 105°, a = 4 のとき、外接円の半径 R は？", "2√2",
              ["4√2", "2", "4"], "A = 180° - 30° - 105° = 45°。2R = 4 / sin45° = 4√2 より R = 2√2。")
    qb.add_mc(sid, uid, 3, "△ABC の外接円の半径が 5、a = 5√3 で ∠A が鋭角のとき、∠A の大きさは？", "60°",
              ["30°", "45°", "120°"], "sinA = a/(2R) = 5√3 / 10 = √3/2。鋭角なので A = 60°。")

    # 4) 余弦定理 (記述 3問 + 選択 3問)
    cos_triples = [
        (3, 5, 7, "120°", "-1/2", 2),
        (3, 8, 7, "60°", "1/2", 2),
        (5, 7, 8, "60°", "1/2", 2),
    ]
    for a, b, c, deg, cos_str, diff in cos_triples:
        # c^2 = a^2 + b^2 - 2ab cosC -> c が対辺
        q = f"△ABC において a = {a}, b = {b}, c = {c} のとき、cosC の値を分数で求めよ。"
        exp = f"余弦定理より cosC = ({a}^2 + {b}^2 - {c}^2) / (2×{a}×{b}) = {cos_str}（C = {deg}）。"
        qb.add_write(sid, uid, diff, q, cos_str, exp)

    qb.add_mc(sid, uid, 2, "△ABC において b = 4, c = 5, A = 60° のとき、辺 a の長さは？", "√21",
              ["√61", "√41", "3√2"], "a^2 = 16 + 25 - 2×4×5×(1/2) = 41 - 20 = 21 より a = √21。")
    qb.add_mc(sid, uid, 2, "△ABC において a = 5, b = 3, C = 120° のとき、辺 c の長さは？", "7",
              ["√19", "8", "√34"], "c^2 = 25 + 9 - 2×5×3×(-1/2) = 34 + 15 = 49 より c = 7。")
    qb.add_mc(sid, uid, 3, "3辺の長さが 7, 8, 13 の三角形において、最大の角の大きさは？", "120°",
              ["90°", "135°", "150°"], "最大角は最長辺 13 の対角。cosθ = (49+64-169)/(2×7×8) = -56/112 = -1/2 より 120°。")

    # 5) 面積・内接円・空間・性質 (記述 3問 + 選択 3問 + ○× 3問) -> 6+7+6+6+9 = 34問！
    qb.add_write(sid, uid, 1, "△ABC において b = 6, c = 8, A = 30° のとき、面積 S は？", "12",
                 "S = (1/2)×6×8×sin30° = 24 × (1/2) = 12。")
    qb.add_write(sid, uid, 3, "3辺の長さが 13, 14, 15 の三角形の面積は 84 である。この三角形の内接円の半径 r は？", "4",
                 "S = (1/2)r(a+b+c) より 84 = (1/2)r(13+14+15) = 21r、よって r = 4。")
    qb.add_write(sid, uid, 2, "直方体の3辺の長さが 2, 3, 6 のとき、対角線の長さは？", "7",
                 "対角線の長さは √(2^2 + 3^2 + 6^2) = √(4 + 9 + 36) = √49 = 7。")

    qb.add_mc(sid, uid, 2, "1辺の長さが 6 の正三角形の面積は？", "9√3",
              ["18√3", "6√3", "12√3"], "S = (1/2)×6×6×sin60° = 18 × (√3/2) = 9√3。")
    qb.add_mc(sid, uid, 3, "円に内接する四角形 ABCD で AB=2, BC=3, CD=1, DA=2 のとき、対角線 AC の長さを出すには cosB と何を等置するか？",
              "cosD = -cosB", ["cosD = cosB", "sinD = -sinB", "tanD = tanB"],
              "内接四角形の対角の和は 180° なので D = 180° - B、よって cosD = -cosB として AC^2 を2通りで表す。")
    qb.add_mc(sid, uid, 3, "1辺の長さが a の正四面体の体積を表す式は？", "(√2/12)a^3",
              ["(√3/12)a^3", "(√2/4)a^3", "(√3/6)a^3"], "底面積 (√3/4)a^2、高さ (√6/3)a より V = (1/3)×(√3/4)a^2×(√6/3)a = (√2/12)a^3。")

    qb.add_ox(sid, uid, 1, "0° < θ < 180° の範囲では、cosθ の値は必ず正になる。", False,
              "90° < θ < 180° の鈍角では cosθ < 0 となる。")
    qb.add_ox(sid, uid, 2, "任意の角 θ について sin(180° - θ) = sinθ が成り立つ。", True,
              "単位円上で 180°-θ は θ と y 軸対称な位置にあるため y 座標（sin）は等しい。")
    qb.add_ox(sid, uid, 2, "三角形の3辺の長さ a, b, c に対して a^2 + b^2 < c^2 ならば、∠C は鈍角である。", True,
              "余弦定理 cosC = (a^2 + b^2 - c^2)/(2ab) < 0 となるため ∠C > 90°（鈍角）。")

    # --- math1-u5: データの分析 (34問) ---
    uid = "math1-u5"

    def quartiles_m1(xs: list[int]) -> tuple[Fraction, Fraction, Fraction]:
        """高校数学Ⅰの教科書定義による (Q1, Q2, Q3) を厳密計算する。"""
        s = sorted(xs)
        n = len(s)

        def med(arr: list[int]) -> Fraction:
            m = len(arr)
            if m % 2 == 1:
                return Fraction(arr[m // 2])
            return Fraction(arr[m // 2 - 1] + arr[m // 2], 2)

        q2 = med(s)
        half = n // 2
        if n % 2 == 0:
            q1, q3 = med(s[:half]), med(s[half:])
        else:
            q1, q3 = med(s[:half]), med(s[half + 1:])
        return q1, q2, q3

    # 1) 代表値・四分位数 (記述 7問 + 選択 5問)
    datasets_rep = [
        ([3, 7, 5, 9, 6], "平均値", 1),
        ([12, 8, 15, 10, 20], "中央値", 1),
        ([4, 7, 4, 9, 4, 8, 7], "最頻値", 1),
        ([14, 6, 22, 9, 18, 11], "範囲（レンジ）", 1),
        ([2, 5, 8, 10, 12, 15, 19], "第1四分位数", 2),
        ([2, 5, 8, 10, 12, 15, 19], "第3四分位数", 2),
        ([4, 6, 9, 11, 14, 17, 20, 25], "四分位範囲", 2),
    ]
    for arr, metric, diff in datasets_rep:
        s = sorted(arr)
        q1, q2, q3 = quartiles_m1(arr)
        if metric == "平均値":
            val = Fraction(sum(arr), len(arr))
            exp = f"合計 {sum(arr)} を個数 {len(arr)} で割ると {fmt_frac(val)}。"
        elif metric == "中央値":
            val = q2
            exp = f"小さい順に並べると {s}。中央の値は {fmt_frac(val)}。"
        elif metric == "最頻値":
            val = Fraction(Counter(arr).most_common(1)[0][0])
            exp = f"最も多く出現する値は {fmt_frac(val)}。"
        elif metric == "範囲（レンジ）":
            val = Fraction(max(arr) - min(arr))
            exp = f"最大値 {max(arr)} - 最小値 {min(arr)} = {fmt_frac(val)}。"
        elif metric == "第1四分位数":
            val = q1
            exp = f"昇順 {s} の下位データ {s[:len(s)//2]} の中央値は {fmt_frac(val)}。"
        elif metric == "第3四分位数":
            val = q3
            exp = f"昇順 {s} の上位データの中央値は {fmt_frac(val)}。"
        else:
            val = q3 - q1
            exp = f"昇順 {s} より Q1 = {fmt_frac(q1)}, Q3 = {fmt_frac(q3)}。四分位範囲 = Q3 - Q1 = {fmt_frac(val)}。"
        q = f"データ {arr} の{metric}は？"
        qb.add_write(sid, uid, diff, q, fmt_frac(val), exp)

    rep_mc = [
        ([1, 4, 6, 9, 10, 14], "中央値", 1),
        ([3, 8, 11, 15, 20, 24], "四分位範囲", 2),
        ([5, 8, 10, 13, 17, 21, 25, 30, 35], "四分位偏差", 3),
        ([10, 12, 15, 18, 25], "平均値", 1),
        ([6, 9, 12, 14, 18, 21, 24, 32], "第3四分位数", 2),
    ]
    for arr, metric, diff in rep_mc:
        s = sorted(arr)
        q1, q2, q3 = quartiles_m1(arr)
        if metric == "中央値":
            val = q2
            exp = f"昇順 {s} より中央の2数 {s[len(s)//2-1]} と {s[len(s)//2]} の平均 {fmt_frac(val)}。"
            dists = [fmt_frac(val + 1), fmt_frac(val - 1), str(s[len(s)//2]), fmt_frac(val + 2), fmt_frac(q1)]
        elif metric == "四分位範囲":
            val = q3 - q1
            exp = f"Q1={fmt_frac(q1)}, Q3={fmt_frac(q3)} より Q3 - Q1 = {fmt_frac(val)}。"
            dists = [fmt_frac(val + 2), fmt_frac(val / 2), fmt_frac(q3), fmt_frac(val - 2), fmt_frac(val + 4)]
        elif metric == "四分位偏差":
            val = (q3 - q1) / 2
            exp = f"Q1={fmt_frac(q1)}, Q3={fmt_frac(q3)} より四分位偏差 = (Q3 - Q1)/2 = {fmt_frac(val)}。"
            dists = [fmt_frac(q3 - q1), fmt_frac(val + 1), fmt_frac(q2), fmt_frac(val - 1), fmt_frac(val + 2)]
        elif metric == "平均値":
            val = Fraction(sum(arr), len(arr))
            exp = f"合計 {sum(arr)} / {len(arr)} = {fmt_frac(val)}。"
            dists = [str(q2), fmt_frac(val + 1), fmt_frac(val + 2), fmt_frac(val - 2), fmt_frac(q3)]
        else:
            val = q3
            exp = f"昇順 {s} の上位4個 {s[4:]} の中央値は {fmt_frac(val)}。"
            dists = [fmt_frac(q1), fmt_frac(q2), fmt_frac(val + 2), fmt_frac(val - 2), fmt_frac(q3 - q1)]
        qb.add_mc(sid, uid, diff, f"データ {arr} の{metric}はどれか？", fmt_frac(val), dists, exp)

    # 2) 分散と標準偏差 (記述 4問 + 選択 3問)
    var_datasets = [
        ([2, 4, 6, 8, 10], "分散", 2),
        ([1, 3, 5, 7, 9], "分散", 2),
        ([10, 12, 14, 16, 18], "分散", 2),
        ([2, 2, 6, 6], "標準偏差", 2),
    ]
    for arr, metric, diff in var_datasets:
        mean = Fraction(sum(arr), len(arr))
        var = sum((Fraction(x) - mean) ** 2 for x in arr) / len(arr)
        if metric == "分散":
            val_str = fmt_frac(var)
            exp = f"平均値は {fmt_frac(mean)}。偏差の2乗の平均は {val_str}。"
        else:
            # 2,2,6,6 -> 平均4, 偏差±2, 分散4, 標準偏差2
            sd = math.isqrt(var.numerator) if var.denominator == 1 else 0
            val_str = str(sd)
            exp = f"平均値 {fmt_frac(mean)}、分散 {fmt_frac(var)} より標準偏差は √{fmt_frac(var)} = {val_str}。"
        qb.add_write(sid, uid, diff, f"データ {arr} の{metric}を求めよ。", val_str, exp)

    qb.add_mc(sid, uid, 2, "データ [3, 5, 7, 9] の分散は？", "5", ["4", "6", "√5"],
              "平均 6。偏差は -3, -1, 1, 3 なので分散 = (9+1+1+9)/4 = 5。")
    qb.add_mc(sid, uid, 3, "5個のデータ x_1,...,x_5 の平均値が 4、x_k^2 の平均値が 25 のとき、このデータの分散は？", "9",
              ["21", "16", "3"], "公式 (分散) = (x^2の平均) - (平均)^2 = 25 - 4^2 = 9。")
    qb.add_mc(sid, uid, 3, "データ [1, 5, 5, 9] の標準偏差は？", "2√2", ["8", "4", "√6"],
              "平均 5。偏差は -4, 0, 0, 4 なので分散 = (16+0+0+16)/4 = 8。よって標準偏差は √8 = 2√2。")

    # 3) 変量変換 y = ax + b (記述 3問 + 選択 3問 + ○× 2問)
    qb.add_write(sid, uid, 2, "変量 x の平均値が 10、標準偏差が 3 のとき、y = 2x + 5 の平均値は？", "25",
                 "変換後の平均値は 2×10 + 5 = 25。")
    qb.add_write(sid, uid, 2, "変量 x の標準偏差が 4 のとき、y = -3x + 7 の標準偏差は？", "12",
                 "標準偏差は |-3|×4 = 12（平行移動 +7 は影響せず、符号は絶対値になる）。")
    qb.add_write(sid, uid, 3, "変量 x の分散が 5 のとき、y = 3x - 4 の分散は？", "45",
                 "分散は a^2 倍されるので 3^2 × 5 = 45。")
    qb.add_mc(sid, uid, 2, "変量 x の分散が 16 のとき、標準偏差 s_x と y = (1/2)x + 10 の標準偏差 s_y の組は？", "(4, 2)",
              ["(4, 12)", "(4, 1)", "(8, 4)"], "s_x = √16 = 4。y = (1/2)x + 10 より s_y = (1/2)×4 = 2。")
    qb.add_mc(sid, uid, 3, "変量 x, y について u = 2x + 1, v = -3y + 4 と変換したとき、x と y の相関係数 r_{xy} と u, v の相関係数 r_{uv} の関係は？",
              "r_{uv} = -r_{xy}", ["r_{uv} = r_{xy}", "r_{uv} = -6 r_{xy}", "r_{uv} = (2/3) r_{xy}"],
              "相関係数は a, c の符号の積のみに影響される。2×(-3) < 0 なので符号だけ反転する。")
    qb.add_mc(sid, uid, 3, "あるテストの平均点が 50 点、標準偏差が 10 点のとき、全員の点数を 1.2 倍して 5 点引くと新しい標準偏差は？", "12点",
              ["7点", "14.4点", "17点"], "標準偏差は 1.2 倍のみ影響を受け 10×1.2 = 12 点。")
    qb.add_ox(sid, uid, 1, "データのすべての値に同じ定数 5 を足すと、分散も 5 増える。", False,
              "全データが同じだけ平行移動しても散らばり具合は変わらないため、分散は変化しない。")
    qb.add_ox(sid, uid, 2, "変量 x を y = -x + 100 で変換すると、x の中央値 m に対して y の中央値は -m + 100 になる。", True,
              "大小関係が完全に逆転するが、中央の位置にある値自身は線形変換 -m + 100 に移る。")

    # 4) 相関係数・散布図・箱ひげ図 (記述 2問 + 選択 2問 + ○× 3問) -> 12+7+8+7 = 34問!
    qb.add_write(sid, uid, 2, "x の標準偏差が 4、y の標準偏差が 5、x と y の共分散が 12 のとき、相関係数 r を小数で答えよ。", "0.6",
                 "r = 共分散 / (s_x × s_y) = 12 / (4 × 5) = 12/20 = 0.6。", alt=["3/5"])
    qb.add_write(sid, uid, 3, "x の分散が 9、y の分散が 16、共分散が -6 のとき、相関係数 r を分数で答えよ。", "-1/2",
                 "s_x = 3, s_y = 4 なので r = -6 / (3 × 4) = -1/2。", alt=["-0.5"])
    qb.add_mc(sid, uid, 2, "相関係数 r のとり得る値の範囲として正しいものは？", "-1 <= r <= 1",
              ["0 <= r <= 1", "-1 < r < 1", "-∞ < r < ∞"], "コーシー=シュワルツの不等式より常に -1 <= r <= 1。")
    qb.add_mc(sid, uid, 2, "散布図において点が右下がりの直線付近に密集しているとき、相関係数 r に最も近い値は？", "-0.92",
              ["0.92", "-0.12", "0.05"], "強い負の相関があるため、-1 に近い負の値 -0.92 が適切。")
    qb.add_ox(sid, uid, 1, "相関係数が 0.9 のように強い正の相関がある場合、必ず因果関係が存在するといえる。", False,
              "相関関係は因果関係を意味しない（疑似相関などの可能性がある）。")
    qb.add_ox(sid, uid, 2, "箱ひげ図において、箱の内部に含まれるデータの個数は全体のおよそ 50% である。", True,
              "箱は第1四分位数 Q1 から第3四分位数 Q3 までを表すため、中央のおよそ 50% が入る。")
    qb.add_ox(sid, uid, 2, "データの中に極端に大きな外れ値が1つ加わると、中央値よりも平均値の方が大きく影響を受けやすい。", True,
              "平均値はすべての値の和を使うため外れ値の影響を強く受けるが、中央値は位置で決まるため影響を受けにくい。")


# ============================================================
# 2. 数学A (mathA): 3単元 × 55問 = 165問
# ============================================================

def generate_mathA(qb: QuestionBank) -> None:
    sid = "mathA"

    # --- mathA-u1: 場合の数と確率 (55問) ---
    uid = "mathA-u1"
    # 1) 倍数の個数・和の法則・積の法則 (記述 5問 + 選択 3問)
    mult_specs = [
        (100, 3, 5, "少なくとも一方", 1),
        (100, 4, 6, "少なくとも一方", 2),
        (150, 3, 7, "どちらでも割り切れない", 2),
        (120, 2, 5, "2で割り切れるが5で割り切れない", 2),
        (200, 4, 5, "少なくとも一方", 1),
    ]
    for N, a, b, cond, diff in mult_specs:
        l = math.lcm(a, b)
        na, nb, nab = N // a, N // b, N // l
        if cond == "少なくとも一方":
            ans = na + nb - nab
            exp = f"{a}の倍数は {na}個、{b}の倍数は {nb}個、{l}の倍数は {nab}個。よって {na}+{nb}-{nab} = {ans}個。"
        elif cond == "どちらでも割り切れない":
            ans = N - (na + nb - nab)
            exp = f"少なくとも一方で割り切れる数は {na}+{nb}-{nab} = {na+nb-nab}個。全体 {N} から引いて {ans}個。"
        else:
            ans = na - nab
            exp = f"2の倍数 {na}個から 10の倍数 {nab}個を引いて {ans}個。"
        qb.add_write(sid, uid, diff, f"1から{N}までの自然数のうち、{a}と{b}について「{cond}」ものは何個あるか？", str(ans), exp, alt=[f"{ans}個"])

    qb.add_mc(sid, uid, 1, "大小2個のさいころを同時に投げるとき、出た目の和が 6 または 8 になる場合は何通り？", "10通り",
              ["8通り", "11通り", "12通り"], "和が6は5通り、和が8は5通り。互いに排反なので 5+5 = 10通り。")
    qb.add_mc(sid, uid, 1, "男子4人、女子3人から代表を男女1人ずつ選ぶ選び方は何通り？", "12通り",
              ["7通り", "24通り", "42通り"], "積の法則より 4 × 3 = 12通り。")
    qb.add_mc(sid, uid, 2, "展開式 (a+b+c)(x+y+z+w)(p+q) を展開したとき、同類項をまとめると項はいくつできるか？", "24個",
              ["9個", "12個", "18個"], "各項がすべて異なる文字から成るため 3 × 4 × 2 = 24個。")

    # 2) 順列・円順列・重複順列 (記述 7問 + 選択 4問)
    for n, r in [(5, 3), (6, 2), (7, 3), (4, 4)]:
        ans = math.perm(n, r)
        qb.add_write(sid, uid, 1, f"異なる{n}個のものから{r}個を取り出して一列に並べる順列 {n}P{r} の値は？", str(ans),
                     f"{n}P{r} = " + "×".join(str(n - i) for i in range(r)) + f" = {ans}。")
    qb.add_write(sid, uid, 2, "大人2人と子ども4人が円卓に座るとき、大人2人が隣り合う座り方は何通り？", "48",
                 "大人2人を1組とみて5つの円順列 (5-1)! = 24通り。大人2人の並びが 2! = 2通りで 24×2 = 48通り。", alt=["48通り"])
    qb.add_write(sid, uid, 2, "0, 1, 2, 3, 4 の5枚のカードから異なる3枚を選んで3桁の整数を作るとき、全部で何個できるか？", "48",
                 "百の位は0以外の4通り、十の位は残り4通り、一の位は3通り。よって 4×4×3 = 48個。", alt=["48個"])
    qb.add_write(sid, uid, 2, "5人を部屋 A, B, C の3つに入れる方法は、空き部屋があってもよいとすると何通りあるか？", "243",
                 "各人について3通りの行き先があるので重複順列 3^5 = 243通り。", alt=["243通り"])

    qb.add_mc(sid, uid, 2, "6人が手をつないで輪を作るときの並び方は何通り？", "120通り",
              ["720通り", "60通り", "240通り"], "円順列の公式より (6 - 1)! = 5! = 120通り。")
    qb.add_mc(sid, uid, 2, "男子3人、女子3人が一列に並ぶとき、女子3人が全員隣り合う並び方は何通り？", "144通り",
              ["72通り", "720通り", "36通り"], "女子3人を1まとまりとみると 4! = 24通り。女子の並び替えが 3! = 6通りで 24×6 = 144通り。")
    qb.add_mc(sid, uid, 3, "両親と子ども4人の計6人が円卓に座るとき、両親が向かい合う座り方は何通り？", "24通り",
              ["48通り", "120通り", "12通り"], "父を固定すると母の位置は正面の1通り。残り4人の並び方は 4! = 24通り。")
    qb.add_mc(sid, uid, 3, "5個の数 1, 2, 3 を重複を許して並べて4桁の整数を作るとき、何個できるか？", "81個",
              ["64個", "24個", "125個"], "各位それぞれ3通りずつ選べるため 3^4 = 81個。")

    # 3) 組合せ・同じものを含む順列・重複組合せ・組分け (記述 7問 + 選択 5問)
    for n, r in [(6, 3), (8, 2), (7, 4), (9, 3)]:
        ans = math.comb(n, r)
        qb.add_write(sid, uid, 1, f"{n}個から{r}個選ぶ組合せ {n}C{r} の値は？", str(ans),
                     f"{n}C{r} = {n}P{r} / {r}! = {ans}。")
    qb.add_write(sid, uid, 2, "a が3個、b が2個、c が1個の計6文字をすべて使って一列に並べる方法は何通り？", "60",
                 "同じものを含む順列より 6! / (3! 2! 1!) = 720 / 12 = 60通り。", alt=["60通り"])
    qb.add_write(sid, uid, 2, "縦4区画、横3区画の碁盤の目状の道で、左下から右上まで最短距離で行く道順は何通り？", "35",
                 "上4回、右3回の計7回の並び替えなので 7C3 = 35通り。", alt=["35通り"])
    qb.add_write(sid, uid, 3, "x + y + z = 8 を満たす負でない整数 (x, y, z) の組は何通りあるか？", "45",
                 "3H8 = (8+3-1)C8 = 10C2 = 45通り。", alt=["45通り"])

    qb.add_mc(sid, uid, 2, "6人を 2人ずつの3組（A, B, Cの区別なし）に分ける方法は何通り？", "15通り",
              ["90通り", "45通り", "30通り"], "まず区別ありで 6C2 × 4C2 × 2C2 = 90通り。3組の区別をなくすため 3! = 6 で割って 15通り。")
    qb.add_mc(sid, uid, 2, "正八角形の頂点を結んでできる三角形は全部で何個あるか？", "56個",
              ["28個", "336個", "64個"], "8個の頂点から3個を選ぶので 8C3 = 56個。")
    qb.add_mc(sid, uid, 2, "正十角形の対角線は全部で何本あるか？", "35本",
              ["45本", "70本", "25本"], "10C2 - 10 = 45 - 10 = 35本。")
    qb.add_mc(sid, uid, 3, "x + y + z = 7 を満たす正の整数 (x, y, z) の組は何通り？", "15通り",
              ["36通り", "21通り", "28通り"], "各変数にあらかじめ1を配ると x'+y'+z'=4 の非負整数解に帰着し、6C2 = 15通り。")
    qb.add_mc(sid, uid, 2, "りんご、みかん、バナナから重複を許して5個買う選び方は何通り？", "21通り",
              ["15通り", "125通り", "35通り"], "3H5 = (5+3-1)C5 = 7C2 = 21通り。")

    # 4) 基本確率・余事象・独立・反復試行 (記述 6問 + 選択 6問)
    qb.add_write(sid, uid, 1, "大小2個のさいころを投げるとき、出た目の和が 9 になる確率を既約分数で答えよ。", "1/9",
                 "(3,6),(4,5),(5,4),(6,3) の4通り。4/36 = 1/9。")
    qb.add_write(sid, uid, 2, "赤玉4個、白玉3個が入った袋から同時に2個取り出すとき、2個とも赤玉である確率は？", "2/7",
                 "4C2 / 7C2 = 6 / 21 = 2/7。")
    qb.add_write(sid, uid, 2, "赤玉4個、白玉3個が入った袋から同時に2個取り出すとき、少なくとも1個が白玉である確率は？", "5/7",
                 "余事象「2個とも赤玉」の確率は 2/7。よって 1 - 2/7 = 5/7。")
    qb.add_write(sid, uid, 2, "1枚の硬貨を4回投げるとき、表がちょうど2回出る確率は？", "3/8",
                 "反復試行より 4C2 × (1/2)^2 × (1/2)^2 = 6/16 = 3/8。")
    qb.add_write(sid, uid, 2, "さいころを3回投げるとき、出た目の積が偶数になる確率は？", "7/8",
                 "余事象「3回とも奇数」は (1/2)^3 = 1/8。よって 1 - 1/8 = 7/8。")
    qb.add_write(sid, uid, 3, "5本のうち2本が当たりのくじを、A、Bの順に1本ずつ引いて元に戻さないとき、Bが当たる確率は？", "2/5",
                 "くじを引く確率は引く順番によらない。2/5 × 1/4 + 3/5 × 2/4 = 8/20 = 2/5。")

    qb.add_mc(sid, uid, 1, "1から20までの番号札から1枚引くとき、番号が 3 の倍数または 5 の倍数である確率は？", "9/20",
              ["1/2", "2/5", "11/20"], "3の倍数は6個、5の倍数は4個、15の倍数は1個なので 6+4-1 = 9個。確率 9/20。")
    qb.add_mc(sid, uid, 2, "A, B, C, D, E の5人が一列に並ぶとき、A と B が隣り合う確率は？", "2/5",
              ["1/5", "3/5", "1/10"], "2! × 4! / 5! = 2/5。")
    qb.add_mc(sid, uid, 2, "さいころを4回投げるとき、6の目が少なくとも1回出る確率を表す式は？", "1 - (5/6)^4",
              ["(1/6)^4", "4 × (1/6)", "1 - (1/6)^4"], "余事象「4回とも6以外」の確率は (5/6)^4。よって 1 - (5/6)^4。")
    qb.add_mc(sid, uid, 2, "Aがシュートを決める確率は 2/3、Bが決める確率は 3/4 で互いに独立とする。2人とも決める確率は？", "1/2",
              ["5/12", "11/12", "1/4"], "独立試行の乗法定理より (2/3) × (3/4) = 1/2。")
    qb.add_mc(sid, uid, 3, "さいころを5回投げるとき、1の目がちょうど2回出る確率は？", "625/3888",
              ["125/1296", "25/216", "125/3888"], "5C2 × (1/6)^2 × (5/6)^3 = 10 × 125 / 7776 = 625/3888。")
    qb.add_mc(sid, uid, 3, "6個の玉（赤3, 白3）を無作為に一列に並べるとき、同じ色の玉が交互に並ぶ確率は？", "1/10",
              ["1/20", "1/5", "3/10"], "全並びは 6C3 = 20通り。交互は赤白赤白赤白と白赤白赤白赤の2通り。よって 2/20 = 1/10。")

    # 5) 条件付き確率・期待値・○× (記述 4問 + 選択 3問 + ○× 5問) -> 8+11+12+12+12 = 55問！
    qb.add_write(sid, uid, 2, "100円硬貨1枚と50円硬貨2枚を同時に投げ、表が出た硬貨の合計金額の期待値はいくらか？", "100",
                 "線形性より 100×(1/2) + 50×(1/2) + 50×(1/2) = 50 + 25 + 25 = 100円。", alt=["100円"])
    qb.add_write(sid, uid, 3, "赤玉3個、白玉2個の袋から戻さずに2回引く。1回目が赤だったとき、2回目も赤である条件付き確率は？", "1/2",
                 "1回目が赤のあと袋には赤2個、白2個の計4個が残るため 2/4 = 1/2。")
    qb.add_write(sid, uid, 3, "男子20人(眼鏡6人)、女子15人(眼鏡5人)のクラスから1人選び眼鏡をかけていたとき、それが男子である確率は？", "6/11",
                 "眼鏡は計 6+5 = 11人。そのうち男子は6人なので条件付き確率は 6/11。")
    qb.add_write(sid, uid, 2, "1回投げると出る目の数だけポイントがもらえるさいころ（1〜6が等確率）のポイントの期待値を小数で答えよ。", "3.5",
                 "(1+2+3+4+5+6)/6 = 21/6 = 3.5。", alt=["7/2"])

    qb.add_mc(sid, uid, 2, "2つの事象 A, B が互いに排反であるとき、必ず成り立つ等式はどれか？", "P(A∪B) = P(A) + P(B)",
              ["P(A∩B) = P(A)P(B)", "P(A∪B) = P(A)P(B)", "P_A(B) = P(B)"],
              "排反とは A∩B = ∅ なので P(A∩B) = 0 となり、加法定理から P(A∪B) = P(A) + P(B)。")
    qb.add_mc(sid, uid, 3, "当たる確率 1/10 のくじが10本あるとき（独立復元）、少なくとも1回当たる確率は1より小さいか？", "1 - (9/10)^10 であり 1 より小さい",
              ["ちょうど 1 である", "10 × (1/10) = 1 より大きくなる", "1/10 である"],
              "すべて外れる確率が (9/10)^10 > 0 のため、1 - (9/10)^10 ≈ 0.651 < 1。")
    qb.add_mc(sid, uid, 3, "条件付き確率 P_A(B) の定義式として正しいものは？（ただし P(A) > 0）", "P(A∩B) / P(A)",
              ["P(A∩B) / P(B)", "P(A∪B) / P(A)", "P(A) / P(A∩B)"],
              "A が起こったという条件のもとで B が起こる確率は P(A∩B)/P(A)。")

    ox_a1 = [
        (1, "事象 A と B が互いに排反ならば、P(A∩B) = 0 である。", True, "排反事象は同時に起こらないため P(A∩B) = 0。"),
        (1, "nCr = nC(n-r) はすべての整数 0 <= r <= n で成り立つ。", True, "r 個選ぶことは残す n-r 個を選ぶことと同じである。"),
        (2, "0!（0の階乗）の値は 0 と定義される。", False, "0! = 1 と定義される（nC0 = nCn = 1 などが成り立つため）。"),
        (2, "2つの事象 A, B が排反（P(A)>0, P(B)>0）であるとき、A と B は独立である。", False, "排反なら P(A∩B)=0 だが P(A)P(B)>0 なので一致せず、むしろ従属である。"),
        (3, "「同じものを含む円順列（数珠順列でない）」は常に (総順列数) ÷ n で計算できる。", False, "回転して重なる周期が n の約数になる場合があるため単純に n で割れないことがある（例: 赤2白2）。"),
    ]
    for diff, q, is_t, exp in ox_a1:
        qb.add_ox(sid, uid, diff, q, is_t, exp)

    # --- mathA-u2: 図形の性質 (55問) ---
    uid = "mathA-u2"
    # 1) 角の二等分線・線分比 (記述 5問 + 選択 3問)
    bisector_cases = [
        (6, 9, 10, "BD", 4, 1),   # AB=6, AC=9, BC=10 -> BD:DC=2:3 -> BD=4
        (8, 12, 15, "BD", 6, 1),  # 8:12=2:3 -> BD=6
        (10, 15, 10, "DC", 6, 2), # 10:15=2:3 -> DC=6
        (9, 6, 5, "BD", 3, 1),    # 9:6=3:2 -> BD=3
        (12, 8, 10, "DC", 4, 2),  # 12:8=3:2 -> DC=4
    ]
    for ab, ac, bc, seg, ans, diff in bisector_cases:
        q = f"△ABC において ∠A の二等分線と辺 BC の交点を D とする。AB={ab}, AC={ac}, BC={bc} のとき、線分 {seg} の長さは？"
        exp = f"BD : DC = AB : AC = {ab} : {ac} より {seg} = {ans}。"
        qb.add_write(sid, uid, diff, q, str(ans), exp)

    qb.add_mc(sid, uid, 2, "△ABC (AB=9, AC=6, BC=5) において ∠A の外角の二等分線と直線 BC の交点を E とするとき、CE の長さは？", "10",
              ["6", "12", "15"], "BE : CE = AB : AC = 9 : 6 = 3 : 2。BE - CE = BC = 5 より比の差 1 が 5、ゆえに CE = 2×5 = 10。")
    qb.add_mc(sid, uid, 2, "AB = 12 の線分 AB を 2 : 1 に外分する点を Q とするとき、AQ の長さは？", "24",
              ["12", "8", "18"], "AQ : BQ = 2 : 1 かつ Q は B の側にあるので AB が比 1 に相当。よって AQ = 12 × 2 = 24。")
    qb.add_mc(sid, uid, 1, "平行線と線分の比について、△ABC の辺 AB, AC 上の点 P, Q が PQ // BC を満たすとき成り立つ比はどれか？",
              "AP : AB = PQ : BC", ["AP : PB = PQ : BC", "AP : QC = PQ : BC", "PB : AB = PQ : BC"],
              "△APQ ∽ △ABC より対応する辺の比 AP : AB = AQ : AC = PQ : BC が成り立つ。")

    # 2) 三角形の五心 (記述 5問 + 選択 5問 + ○× 4問)
    qb.add_write(sid, uid, 1, "△ABC の重心を G とし、頂点 A から辺 BC の中点 M へ引いた中線 AM の長さが 12 のとき、AG の長さは？", "8",
                 "重心は中線を頂点から 2 : 1 に内分するため、AG = 12 × (2/3) = 8。")
    qb.add_write(sid, uid, 1, "点 O を △ABC の外心とする。∠BAC = 50° のとき、∠BOC の大きさ（度）は？", "100",
                 "外接円の円周角と中心角の関係より ∠BOC = 2∠BAC = 100°。", alt=["100°"])
    qb.add_write(sid, uid, 2, "点 I を △ABC の内心とする。∠A = 70° のとき、∠BIC の大きさ（度）は？", "125",
                 "∠BIC = 90° + (1/2)∠A = 90° + 35° = 125°。", alt=["125°"])
    qb.add_write(sid, uid, 2, "△ABC の面積が 36、重心を G とするとき、△GBC の面積は？", "12",
                 "重心は元の三角形の面積を3等分するため △GBC = 36 / 3 = 12。")
    qb.add_write(sid, uid, 3, "直角三角形 ABC（∠C = 90°）で AB = 10 のとき、外接円の半径は？", "5",
                 "直角三角形の外心は斜辺 AB の中点と一致するため、外接円の半径は 10 / 2 = 5。")

    qb.add_mc(sid, uid, 1, "三角形の3つの内角の二等分線が1点で交わるとき、その点は何と呼ばれるか？", "内心",
              ["外心", "重心", "垂心"], "各辺から等距離にある点であり内接円の中心になるため内心。")
    qb.add_mc(sid, uid, 1, "三角形の3辺の垂直二等分線が交わる点は何と呼ばれるか？", "外心",
              ["内心", "重心", "垂心"], "各頂点から等距離にある点であり外接円の中心になるため外心。")
    qb.add_mc(sid, uid, 2, "鋭角三角形の内部に常に存在する五心として正しい組合せは？", "外心・内心・重心・垂心すべて",
              ["重心と内心のみ", "外心と内心のみ", "重心と垂心のみ"], "鈍角三角形では外心と垂心が三角形の外部に出るが、鋭角三角形では4つとも内部にある。")
    qb.add_mc(sid, uid, 2, "鈍角三角形において、必ず三角形の外部にある五心の組合せは？", "外心と垂心",
              ["内心と重心", "外心と重心", "内心と垂心"], "重心と内心はどんな三角形でも必ず内部にあり、外心と垂心は鈍角三角形で外部に出る。")
    qb.add_mc(sid, uid, 3, "三角形の1つの内角の二等分線と、他の2つの外角の二等分線が1点で交わる点を何というか？", "傍心",
              ["垂心", "内心", "外心"], "1つの辺と他の2辺の延長に接する円の中心を傍心という（1つの三角形に3つ存在する）。")

    qb.add_ox(sid, uid, 1, "三角形の重心は、必ず三角形の内部にある。", True, "中線の交点であるため常に内部にある。")
    qb.add_ox(sid, uid, 2, "直角三角形の垂心は、直角の頂点に一致する。", True, "直角を挟む2辺がそのまま垂線となるため直角の頂点で交わる。")
    qb.add_ox(sid, uid, 2, "正三角形では、外心・内心・重心・垂心の4つの点がすべて同じ1点に一致する。", True, "対称性により中線・角の二等分線・垂直二等分線・垂線がすべて一致する。")
    qb.add_ox(sid, uid, 2, "三角形の外心は、3つの辺から等距離にある点である。", False, "3辺から等距離なのは内心。外心は3つの頂点から等距離にある。")

    # 3) チェバ・メネラウス (記述 4問 + 選択 3問)
    qb.add_write(sid, uid, 2, "△ABC の内部の点 O と各頂点を結ぶ直線が対辺と P(BC上), Q(CA上), R(AB上) で交わる。AR=2, RB=3, BP=4, PC=2, CQ=3 のとき QA は？", "4",
                 "チェバの定理 (AR/RB)(BP/PC)(CQ/QA) = 1 より (2/3)×(4/2)×(3/QA) = 4/QA = 1、よって QA = 4。")

    qb.add_write(sid, uid, 2, "△ABC の内部の点 O からのチェバ線で、AR:RB=1:2, BP:PC=3:4 のとき、CQ:QA = 8 : x とすると x は？", "3",
                 "チェバの定理 (1/2)×(3/4)×(CQ/QA) = 1 より CQ/QA = 8/3。よって x = 3。")
    qb.add_write(sid, uid, 2, "△ABC の辺 AB 上に R、AC 上に Q、辺 BC の延長上に P があり一直線上に並ぶ。AR=3, RB=2, BP=8, PC=4, CQ=2 のとき QA は？", "6",
                 "メネラウスの定理 (AR/RB)(BP/PC)(CQ/QA) = 1 より (3/2)×(8/4)×(2/QA) = 6/QA = 1。よって QA = 6。")
    qb.add_write(sid, uid, 3, "△ABC の辺 AB 上に D (AD:DB=2:1)、辺 AC 上に E (AE:EC=3:2) をとり、BE と CD の交点を P、AP と BC の交点を F とするとき、BF : FC = 3 : x とおくと x は？", "4",
                 "チェバの定理 (AD/DB)(BF/FC)(CE/EA) = 1 より 2 × (BF/FC) × (2/3) = 1、ゆえに BF:FC = 3:4 なので x = 4。")

    qb.add_mc(sid, uid, 2, "チェバの定理が成り立つための条件として適切な状況は？", "3頂点と対辺(または延長)上の3点を結ぶ直線が1点で交わる",
              ["一直線上に3点がある", "3点が同一円周上にある", "三角形が二等辺三角形である"],
              "3本のチェバ線が1点（または平行）で交わるとき比の積が1になる。3点が一直線上はメネラウスの定理。")
    qb.add_mc(sid, uid, 3, "△ABC で AR:RB=1:2, BP:PC=3:1 のとき、P, Q(AC延長上), R が一直線上にあるための CQ:QA は？", "2 : 3",
              ["3 : 2", "1 : 6", "6 : 1"], "メネラウスの定理 (1/2)×(3/1)×(CQ/QA) = 1 より CQ/QA = 2/3。")
    qb.add_mc(sid, uid, 3, "△ABC の辺 BC の中点を M、辺 AB を 1:2 に内分する点を D、AM と CD の交点を P とするとき、AP : PM は？", "1 : 1",
              ["2 : 1", "1 : 2", "3 : 2"], "△ABM と直線 CD にメネラウスの定理: (AD/DB)(BC/CM)(MP/PA) = 1 ⇒ (1/2)(2/1)(MP/PA) = 1 ⇒ AP:PM = 1:1。")

    # 4) 円の性質 (記述 6問 + 選択 5問)
    qb.add_write(sid, uid, 1, "円に内接する四角形 ABCD において、∠A = 75° のとき ∠C の大きさ（度）は？", "105",
                 "円に内接する四角形の対角の和は 180° なので 180° - 75° = 105°。", alt=["105°"])
    qb.add_write(sid, uid, 2, "円に内接する四角形 ABCD において、∠B = 82° のとき、頂点 D における外角の大きさ（度）は？", "82",
                 "円に内接する四角形の外角は、その内対角に等しいため 82°。", alt=["82°"])
    qb.add_write(sid, uid, 2, "点 A で円に接する直線 AT と円上の点 B, C について ∠TAB = 58°（鋭角側）のとき、円周角 ∠ACB の大きさ（度）は？", "58",
                 "接弦定理により ∠TAB = ∠ACB = 58°。", alt=["58°"])
    qb.add_write(sid, uid, 2, "円 O の直径 AB と円周上の点 C について ∠CAB = 37° のとき、∠ABC の大きさ（度）は？", "53",
                 "直径に対する円周角 ∠ACB = 90° より ∠ABC = 90° - 37° = 53°。", alt=["53°"])
    qb.add_write(sid, uid, 2, "円 O の外部の点 P から円へ引いた2本の接線の接点を A, B とする。∠APB = 50° のとき、中心角 ∠AOB（劣弧側）は（度）？", "130",
                 "∠OAP = ∠OBP = 90° なので四角形 OAPB の内角の和より 360° - 180° - 50° = 130°。", alt=["130°"])
    qb.add_write(sid, uid, 3, "四角形 ABCD が円に内接し、AB の延長と DC の延長が P で交わる。∠P = 30°, ∠B = 70° のとき、∠BAD の大きさ（度）は？", "80",
                 "内対角の性質より ∠ADP = ∠B = 70°。△PAD の内角の和より ∠BAD = 180° - 70° - 30° = 80°。", alt=["80°"])

    qb.add_mc(sid, uid, 1, "四角形 ABCD が円に内接するための条件として正しくないものはどれか？",
              "対角線の長さが等しい",
              ["1組の対角の和が 180° である", "1つの外角がその内対角に等しい", "対角線 AC に対し同じ側にある ∠ABD = ∠ACD である"],
              "等脚台形や長方形は対角線が等しく円に内接するが、一般の凧形や対角線が等しいだけの四角形は内接するとは限らない。")
    qb.add_mc(sid, uid, 2, "円周上の4点 A, B, C, D がこの順に並び、AC と BD が P で交わる。∠ABD = 40°, ∠BDC = 35° のとき ∠APD は？", "75°",
              ["105°", "85°", "65°"], "弧 AD の円周角より ∠ACD = ∠ABD = 40°。△PCD の外角より ∠APD = ∠PCD + ∠PDC = 40° + 35° = 75°。")
    qb.add_mc(sid, uid, 2, "円の内部に交わる2つの弦 AB, CD の交点を P とするとき、方べきの定理が表す等式は？", "PA・PB = PC・PD",
              ["PA・PC = PB・PD", "PA + PB = PC + PD", "PA^2 = PC・PD"], "△PAC ∽ △PDB より PA : PD = PC : PB、よって PA・PB = PC・PD。")
    qb.add_mc(sid, uid, 2, "△ABC の内接円が3辺 BC, CA, AB とそれぞれ D, E, F で接するとき、必ず成り立つ関係は？", "AF = AE",
              ["AF = BF", "BD = DC", "AE = EC"], "円外の点 A から引いた2本の接線の長さは等しいため AF = AE。")
    qb.add_mc(sid, uid, 3, "AB=5, BC=6, CA=7 の △ABC の内接円が辺 AB と接する点を F とするとき、AF の長さは？", "3",
              ["2", "4", "2.5"], "AF=AE=x, BF=BD=y, CD=CE=z とおくと x+y=5, y+z=6, z+x=7。3式を足して2で割ると x+y+z=9 より x = 9 - 6 = 3。")

    # 5) 方べきの定理計算・2円の位置関係 (記述 4問 + 選択 4問 + ○× 3問)
    qb.add_write(sid, uid, 1, "円の2つの弦 AB, CD が点 P で交わり、PA = 3, PB = 8, PC = 4 のとき、PD の長さは？", "6",
                 "方べきの定理 PA・PB = PC・PD より 3×8 = 4×PD、よって PD = 6。")
    qb.add_write(sid, uid, 2, "円外の点 P から引いた接線の接点を T、割線と円の交点を A, B とする。PA = 4, AB = 5 のとき、PT の長さは？", "6",
                 "PB = PA + AB = 9。方べきの定理 PT^2 = PA・PB = 4×9 = 36 より PT = 6。")
    qb.add_write(sid, uid, 2, "半径 5 と半径 3 の2つの円が外接しているとき、2つの円の中心間の距離は？", "8",
                 "外接の条件は d = R + r なので 5 + 3 = 8。")
    qb.add_write(sid, uid, 3, "半径 7 と半径 2 の2つの円の中心間距離が 13 のとき、共通外接線の長さは？", "12",
                 "中心線に平行な垂線を下ろすと、直角三角形の斜辺 13、1辺 7-2 = 5 より √(13^2 - 5^2) = 12。")

    qb.add_mc(sid, uid, 1, "半径 R=6, r=4 の2つの円の中心間距離 d が 2 のとき、2つの円の位置関係は？", "内接する",
              ["外接する", "2点で交わる", "一方が他方の内部にある"], "d = R - r = 6 - 4 = 2 なので、2円は内接する。")
    qb.add_mc(sid, uid, 2, "2つの円が互いに外部にある（離れている）とき、引くことができる共通接線は全部で何本か？", "4本",
              ["2本", "3本", "1本"], "共通外接線が2本、共通内接線が2本の計4本引ける。")
    qb.add_mc(sid, uid, 2, "半径 8 と半径 3 の2つの円が 2点で交わるとき、中心間距離 d のとり得る値の範囲は？", "5 < d < 11",
              ["3 < d < 8", "5 <= d <= 11", "d > 11"], "2点で交わる条件は |R - r| < d < R + r なので 5 < d < 11。")
    qb.add_mc(sid, uid, 3, "半径 5 と半径 3 の2円の中心間距離が 10 のとき、共通内接線の長さは？", "6",
              ["8", "2√21", "4"], "共通内接線の長さは √(d^2 - (R + r)^2) = √(10^2 - 8^2) = √36 = 6。")

    qb.add_ox(sid, uid, 1, "2つの円が外接するとき、共通接線は全部で 3本 引ける。", True,
              "共通外接線が2本と、接点を通る共通内接線が1本の計3本である。")
    qb.add_ox(sid, uid, 2, "4点 A, B, C, D について、直線 AB と CD が点 P で交わり PA・PB = PC・PD が成り立つならば、4点 A, B, C, D は同一円周上にある。", True,
              "方べきの定理の逆が成り立つ（ただし P に対する A, B と C, D の位置関係が内分同士または外分同士のとき）。")
    qb.add_ox(sid, uid, 2, "互いに直交する2つの直線が円の直径でない弦であるとき、それらの交点は必ず円の中心になる。", False,
              "単なる直交する2弦の交点は中心とは限らない（中心になるのは2弦がともに直径または垂直二等分線のとき）。")

    # 6) 空間図形・多面体 (記述 2問 + 選択 2問 + ○× 4問) -> 8+14+7+11+11+8 = 59? 数えよう: 5+3=8, 5+5+4=14, 4+3=7, 6+5=11, 4+4+3=11 -> 計51問! なのであと4問で55問！
    qb.add_write(sid, uid, 1, "正八面体の辺の数は全部で何本か？", "12",
                 "1面が3辺×8面 = 24、各辺を2回ずつ数えているため 24 / 2 = 12本。", alt=["12本"])
    qb.add_write(sid, uid, 2, "ある凸多面体の頂点の数が 12、辺の数が 30 のとき、面の数はいくつあるか？（オイラーの多面体定理）", "20",
                 "V - E + F = 2 より 12 - 30 + F = 2、よって F = 20（正二十面体など）。", alt=["20面"])
    qb.add_mc(sid, uid, 2, "すべての面が合同な正多角形で、各頂点に集まる面の数が等しい凸多面体（正多面体）は何種類あるか？", "5種類",
              ["4種類", "6種類", "無限にある"], "正四面体、正六面体、正八面体、正十二面体、正二十面体の5種類のみ。")
    qb.add_ox(sid, uid, 2, "正十二面体の1つの面は、正五角形である。", True, "正十二面体は12枚の正五角形からできている。")

    # --- mathA-u3: 整数の性質 (55問) ---
    uid = "mathA-u3"
    # 1) 約数・倍数・平方数 (記述 6問 + 選択 4問 + ○× 3問)
    for n, mode, diff in [(72, "count", 1), (120, "count", 1), (360, "count", 2), (24, "sum", 2), (45, "sum", 2)]:
        # 素因数分解
        temp = n
        factors: dict[int, int] = {}
        d = 2
        while d * d <= temp:
            while temp % d == 0:
                factors[d] = factors.get(d, 0) + 1
                temp //= d
            d += 1
        if temp > 1:
            factors[temp] = factors.get(temp, 0) + 1
        f_str = " × ".join(f"{p}^{e}" if e > 1 else f"{p}" for p, e in sorted(factors.items()))
        if mode == "count":
            ans = 1
            for e in factors.values():
                ans *= (e + 1)
            q = f"{n} の正の約数は全部で何個あるか？"
            exp = f"{n} = {f_str} なので、約数の個数は " + "×".join(f"({e}+1)" for _, e in sorted(factors.items())) + f" = {ans}個。"
            qb.add_write(sid, uid, diff, q, str(ans), exp, alt=[f"{ans}個"])
        else:
            ans = 1
            for p, e in factors.items():
                ans *= sum(p ** i for i in range(e + 1))
            q = f"{n} の正の約数の総和を求めよ。"
            exp = f"{n} = {f_str} より、約数の総和は " + "×".join("(" + "+".join(f"{p}^{i}" for i in range(e + 1)) + ")" for p, e in sorted(factors.items())) + f" = {ans}。"
            qb.add_write(sid, uid, diff, q, str(ans), exp)

    qb.add_write(sid, uid, 2, "54n が自然数の平方となるような最小の自然数 n の値は？", "6",
                 "54 = 2 × 3^3。指数をすべて偶数にするには 2 × 3 = 6 を掛ける必要がある。")

    qb.add_mc(sid, uid, 1, "整数が 9 の倍数であるための条件として正しいものは？", "各位の数の和が 9 の倍数である",
              ["下2桁が 9 の倍数である", "一の位が 9 である", "各位の数の積が 9 の倍数である"],
              "10^k ≡ 1 (mod 9) なので、元の数は各位の数の和と9を法として合同になる。")
    qb.add_mc(sid, uid, 2, "4桁の整数 23a4 が 4 の倍数かつ 3 の倍数になるような数字 a (0〜9) の総和は？", "6",
              ["9", "12", "18"], "4の倍数より下2桁 a4 から a ∈ {0, 2, 4, 6, 8}。3の倍数より 9+a が3の倍数なので a=0, 6。総和は 0+6 = 6。")

    qb.add_mc(sid, uid, 2, "240 の正の約数のうち、偶数は何個あるか？", "16個",
              ["20個", "4個", "12個"], "240 = 2^4 × 3 × 5。偶数の約数は 2 を少なくとも1個含むため (4)×(1+1)×(1+1) = 16個。")
    qb.add_mc(sid, uid, 3, "5桁の整数 12345 を 11 で割った余りは？", "3",
              ["0", "5", "8"], "奇数桁(右から1,3,5位)の和 5+3+1=9、偶数桁の和 4+2=6。差 9-6 = 3 なので余りは 3。")

    qb.add_ox(sid, uid, 1, "2つの整数 a, b がともに 3 の倍数ならば、a + b も 3 の倍数である。", True, "3m + 3n = 3(m+n) より成り立つ。")
    qb.add_ox(sid, uid, 1, "1 は素数である。", False, "素数は「1と自分自身以外に正の約数をもたない 2 以上の自然数」と定義され、1 は含まない。")
    qb.add_ox(sid, uid, 2, "正の約数の個数が奇数であるような自然数は、平方数（整数の2乗）に限られる。", True, "素因数分解の指数 e_i について Π(e_i+1) が奇数 ⇔ すべての e_i が偶数 ⇔ 平方数。")

    # 2) n! の素因数・末尾の0 (記述 5問 + 選択 2問)
    def legendre(n: int, p: int) -> int:
        res = 0
        pk = p
        while pk <= n:
            res += n // pk
            pk *= p
        return res

    for n, p, diff in [(30, 2, 2), (50, 5, 2), (100, 3, 3)]:
        ans = legendre(n, p)
        qb.add_write(sid, uid, diff, f"{n}! を素因数分解したとき、素因数 {p} の指数（何回割り切れるか）は？", str(ans),
                     f"ガウス記号の和で計算すると {ans} 回割り切れる。")
    for n, diff in [(40, 2), (125, 3)]:
        ans = legendre(n, 5)
        qb.add_write(sid, uid, diff, f"{n}! を計算したとき、末尾に 0 は何個連続して並ぶか？", str(ans),
                     f"末尾の0の個数は素因数5の個数と一致する。{n}//5 + ... = {ans}個。", alt=[f"{ans}個"])
    qb.add_mc(sid, uid, 2, "20! は 6^n で最大何回割り切れるか？", "8回",
              ["10回", "4回", "18回"], "6 = 2×3 なので 3 の指数を求めればよい。20//3 + 20//9 = 6 + 2 = 8回。")
    qb.add_mc(sid, uid, 3, "連続する3つの整数 n(n+1)(n+2) の積は、任意の整数 n に対して必ず何の倍数になるか？", "6の倍数",
              ["12の倍数", "4の倍数", "9の倍数"], "連続3整数には必ず 2の倍数と3の倍数が含まれるため 2×3=6 の倍数になる。")

    # 3) GCD・LCM・互除法 (記述 6問 + 選択 4問)
    gcd_cases = [(84, 126, "最大公約数"), (18, 24, "最小公倍数"), (221, 143, "最大公約数"), (12, 15, "最小公倍数")]
    for a, b, mode in gcd_cases:
        val = math.gcd(a, b) if mode == "最大公約数" else math.lcm(a, b)
        qb.add_write(sid, uid, 1 if a < 100 else 2, f"{a} と {b} の{mode}を求めよ。", str(val),
                     f"素因数分解またはユークリッドの互除法より {mode} は {val}。")
    qb.add_write(sid, uid, 2, "2つの自然数 a, b の最大公約数が 6、最小公倍数が 72 であるとき、積 ab の値は？", "432",
                 "公式 ab = GL より 6 × 72 = 432。")
    qb.add_write(sid, uid, 3, "積が 360、最大公約数が 6 である2つの自然数の組 (a <= b) のうち、最小公倍数は？", "60",
                 "ab = GL より L = 360 / 6 = 60。")

    qb.add_mc(sid, uid, 2, "ユークリッドの互除法を用いて 391 と 299 の最大公約数を求めると？", "23",
              ["17", "13", "29"], "391 = 299×1 + 92、299 = 92×3 + 23、92 = 23×4 + 0 より GCD = 23。")
    qb.add_mc(sid, uid, 2, "2つの自然数 a, b が「互いに素」であるとはどういう意味か？", "最大公約数が 1 である",
              ["どちらも素数である", "最小公倍数が 1 である", "共通の約数が 0 個である"],
              "1以外の正の公約数をもたない、すなわち gcd(a, b) = 1 であることを互いに素という。")
    qb.add_mc(sid, uid, 3, "最大公約数が 5、最小公倍数が 150 である2つの自然数の和としてあり得る最小の値は？（a, b はともに5より大きいとする）", "55",
              ["155", "65", "45"], "a=5a', b=5b' (互いに素) とすると a'b'=30。(a', b')=(5, 6) のとき和が最小で 5(5+6) = 55。")
    qb.add_mc(sid, uid, 3, "自然数 n と n + 1 の最大公約数として正しいものは？", "常に 1",
              ["n によって変わる", "常に 2", "n の値に等しい"], "gcd(n+1, n) = gcd(n, 1) = 1 より隣り合う2整数は常に互いに素。")

    # 4) 1次不定方程式・合同式 (記述 8問 + 選択 6問 + ○× 2問)
    dioph_cases = [
        (5, 7, 1),
        (7, 11, 2),
        (4, 9, 3),
        (13, 5, 1),
    ]
    for a, b, c in dioph_cases:
        # ax - by = c で最小の正の整数 x
        x_ans = next(x for x in range(1, b + 1) if (a * x - c) % b == 0)
        y_ans = (a * x_ans - c) // b
        qb.add_write(sid, uid, 2, f"1次不定方程式 {a}x - {b}y = {c} の整数解のうち、x が最小の正の整数となる x の値は？", str(x_ans),
                     f"x = {x_ans}, y = {y_ans} を代入すると {a}({x_ans}) - {b}({y_ans}) = {c} となり、これが正で最小。")

    mod_cases = [
        (2, 100, 7, 2),
        (3, 50, 4, 1),
        (7, 20, 5, 2),
        (5, 30, 6, 1),
    ]
    for base, exp_n, mod_m, diff in mod_cases:
        rem = pow(base, exp_n, mod_m)
        qb.add_write(sid, uid, diff, f"{base}^{exp_n} を {mod_m} で割った余りは？", str(rem),
                     f"合同式を用いてべき乗の周期（{base}^k mod {mod_m}）を調べると余りは {rem}。")

    qb.add_mc(sid, uid, 2, "不定方程式 6x + 9y = 10 について正しい記述はどれか？", "整数解は存在しない",
              ["整数解は1組だけ存在する", "整数解は無限に存在する", "x=1, y=1 が解である"],
              "左辺 6x+9y = 3(2x+3y) は3の倍数だが、右辺 10 は3の倍数でないため整数解は存在しない。")
    qb.add_mc(sid, uid, 2, "整数 a を 5 で割ると 2 余り、b を 5 で割ると 4 余る。積 ab を 5 で割った余りは？", "3",
              ["1", "2", "4"], "a ≡ 2, b ≡ 4 (mod 5) より ab ≡ 2×4 = 8 ≡ 3 (mod 5)。")
    qb.add_mc(sid, uid, 3, "3で割ると2余り、5で割ると3余り、7で割ると2余る最小の自然数は？", "23",
              ["53", "38", "128"], "3でも7でも余り2なので n-2 は21の倍数。n = 21k+2 に k=1 を入れると 23（5で割ると余り3）。")
    qb.add_mc(sid, uid, 3, "今日が日曜日のとき、2^100 日後は何曜日か？", "火曜日",
              ["月曜日", "水曜日", "木曜日"], "2^3 = 8 ≡ 1 (mod 7) より 2^100 = (2^3)^33 × 2 ≡ 1 × 2 = 2 (mod 7)。日曜の2日後は火曜。")
    qb.add_ox(sid, uid, 2, "a ≡ b (mod m) かつ c ≡ d (mod m) のとき、a - c ≡ b - d (mod m) が常に成り立つ。", True,
              "合同式では両辺の和・差・積がそのまま成り立つ。")
    qb.add_ox(sid, uid, 3, "ac ≡ bc (mod m) ならば、c ≡ 0 でない限り常に a ≡ b (mod m) が成り立つ。", False,
              "c と m が互いに素でないと割れない（反例: 2×1 ≡ 2×4 (mod 6) だが 1 ≢ 4）。")

    # 5) 記数法・小数 (記述 5問 + 選択 3問 + ○× 1問) -> 計算しよう！
    # 現在数: (6+4+3=13) + (5+2=7) + (6+4=10) + (8+4+2=14) = 44問! あと11問で55問！
    base_writes = [
        ("101101", 2, 10, 1),
        ("2102", 3, 10, 2),
        ("45", 10, 2, 1),
        ("58", 10, 5, 2),
        ("123", 4, 10, 2),
    ]
    for s_val, b_from, b_to, diff in base_writes:
        dec = int(s_val, b_from)
        if b_to == 10:
            ans = str(dec)
            q = f"{b_from}進法で表された数 {s_val}_({b_from}) を10進法で表せ。"
            exp = f"各桁の重み {b_from}^k を掛けて足し合わせると 10進法で {ans} になる。"
        else:
            # 10進数 dec を b_to 進文字列へ
            tmp = dec
            digs = []
            while tmp > 0:
                digs.append(str(tmp % b_to))
                tmp //= b_to
            ans = "".join(reversed(digs)) if digs else "0"
            q = f"10進法の数 {dec} を {b_to}進法で表せ（数字列のみ記せ）。"
            exp = f"{dec} を {b_to} で割り続けて余りを下から並べると {ans} になる。"
        qb.add_write(sid, uid, diff, q, ans, exp)

    qb.add_write(sid, uid, 2, "2進法で表された 1011_(2) と 1101_(2) の和を 2進法で表せ（数字列のみ）。", "11000",
                 "10進法では 11 + 13 = 24 = 16 + 8 なので 2進法で 11000。")
    qb.add_write(sid, uid, 3, "0.21_(5)（5進法の小数）を10進法の既約分数で表せ。", "11/25",
                 "2×(1/5) + 1×(1/25) = 10/25 + 1/25 = 11/25。")

    qb.add_mc(sid, uid, 2, "次の既約分数のうち、10進法で「有限小数」になるものはどれか？", "7/40",
              ["5/12", "1/14", "11/30"], "分母の素因数が 2 と 5 のみのものが有限小数になる。40 = 2^3 × 5 なので 7/40 が有限小数。")
    qb.add_mc(sid, uid, 2, "10進法の 255 を 16進法で表すとどれになるか？", "FF",
              ["EE", "100", "FE"], "255 = 15×16 + 15。16進法では 15 を F と表すので FF。")
    qb.add_mc(sid, uid, 3, "10進法の分数 1/7 を小数で表したとき、小数第100位の数字は何か？", "8",
              ["1", "4", "2"], "1/7 = 0.142857142857... の循環節は6桁(142857)。100 = 6×16 + 4 なので4番目の数字 8。")
    qb.add_ox(sid, uid, 2, "10進法で有限小数となる既約分数は、分母を素因数分解したとき素因数が 2 と 5 のみ（片方だけ・なしも含む）である。", True,
              "分母を 2^a 5^b の形に揃えて分母を 10^k に通分できるため有限小数になる。")


# ============================================================
# 3. 数学Ⅱ (math2): 6単元 × 28問 = 168問
# ============================================================

def generate_math2(qb: QuestionBank) -> None:
    sid = "math2"

    # --- math2-u1: 式と証明 (28問) ---
    uid = "math2-u1"
    # 1) 二項定理・3次式の展開/因数分解 (記述 5問 + 選択 3問)
    binom_params = [
        (1, 2, 5, 3, 2),   # (x + 2)^5 の x^3 の係数
        (2, -1, 4, 2, 2),  # (2x - 1)^4 の x^2 の係数
        (1, -3, 5, 2, 2),  # (x - 3)^5 の x^2 の係数
        (3, 1, 4, 3, 2),   # (3x + 1)^4 の x^3 の係数
    ]
    for a, b, n, k, diff in binom_params:
        coef = math.comb(n, k) * (a ** k) * (b ** (n - k))
        expr = fmt_poly_terms([(a, "x"), (b, "")])
        q = f"({expr})^{n} を展開したときの x^{k} の係数は？"
        exp = f"一般項は {n}C{k} ({a}x)^{k} ({b})^{n-k} = {math.comb(n, k)} × {a**k} × ({b**(n-k)}) x^{k} = {coef}x^{k}。"
        qb.add_write(sid, uid, diff, q, str(coef), exp)

    qb.add_write(sid, uid, 1, "(x + 2)^3 を展開せよ。", "x^3 + 6x^2 + 12x + 8",
                 "公式 (a+b)^3 = a^3 + 3a^2b + 3ab^2 + b^3 より x^3 + 6x^2 + 12x + 8。",
                 alt=["x³+6x²+12x+8"])
    qb.add_mc(sid, uid, 2, "x^3 - 27 を因数分解すると？", "(x - 3)(x^2 + 3x + 9)",
              ["(x - 3)(x^2 - 3x + 9)", "(x + 3)(x^2 - 3x + 9)", "(x - 3)^3"],
              "a^3 - b^3 = (a - b)(a^2 + ab + b^2) に a=x, b=3 を適用する。")
    qb.add_mc(sid, uid, 3, "(x + 2/x)^5 の展開式における x の項の係数は？", "40",
              ["10", "20", "80"],
              "5Cr x^(5-r) (2/x)^r = 5Cr 2^r x^(5-2r)。5 - 2r = 1 より r = 2。5C2 × 2^2 = 10 × 4 = 40。")
    qb.add_mc(sid, uid, 2, "二項係数の和 nC0 + nC1 + nC2 + ... + nCn の値に等しいのは？", "2^n",
              ["2^(n-1)", "n!", "n^2"], "(1 + 1)^n を二項定理で展開すると Σ nCr = 2^n となる。")

    # 2) 整式の除法・分数式・恒等式 (記述 5問 + 選択 3問)
    qb.add_write(sid, uid, 1, "多項式 P(x) = x^3 + 2x^2 - x + 5 を x - 1 で割った余りは？", "7",
                 "剰余の定理（または割り算）より P(1) = 1 + 2 - 1 + 5 = 7。")
    qb.add_write(sid, uid, 2, "多項式 x^3 - 4x^2 + 5x + 1 を x^2 - 2x + 3 で割ったときの商を求めよ。", "x - 2",
                 "x^3 - 4x^2 + 5x + 1 = (x^2 - 2x + 3)(x - 2) + (-2x + 7) より商は x - 2。")
    qb.add_write(sid, uid, 2, "x / (x^2 - 1) - 1 / (x + 1) を約分して最も簡単な分数式で表せ（分母・分子の形で）。", "1 / (x^2 - 1)",
                 "通分すると (x - (x - 1)) / ((x - 1)(x + 1)) = 1 / (x^2 - 1)。",
                 alt=["1/(x-1)(x+1)", "1/((x-1)(x+1))", "1/(x²-1)"])
    qb.add_write(sid, uid, 2, "a(x - 1) + b(x + 2) = 5x + 1 が x についての恒等式となるとき、a の値は？", "3",
                 "(a+b)x + (-a+2b) = 5x + 1 より a+b=5, -a+2b=1。解くと b=2, a=3。")
    qb.add_write(sid, uid, 3, "a : b = 2 : 3 のとき、(2a + b) / (a + 3b) の値を既約分数で答えよ。", "7/11",
                 "a = 2k, b = 3k (k≠0) とおくと (4k + 3k)/(2k + 9k) = 7/11。")

    qb.add_mc(sid, uid, 2, "1 / (x(x+1)) を部分分数に分解した式として正しいのは？", "1/x - 1/(x+1)",
              ["1/x + 1/(x+1)", "1/(x+1) - 1/x", "2/x - 1/(x+1)"],
              "通分して確かめると 1/x - 1/(x+1) = (x+1-x)/(x(x+1)) = 1/(x(x+1))。")
    qb.add_mc(sid, uid, 2, "x + y + z = 0 のとき、x^3 + y^3 + z^3 と等しい式は？", "3xyz",
              ["0", "xyz", "-3xyz"],
              "公式 x^3+y^3+z^3 - 3xyz = (x+y+z)(x^2+y^2+z^2-xy-yz-zx) より、x+y+z=0 なら 3xyz。")
    qb.add_mc(sid, uid, 3, "a/(b+c) = b/(c+a) = c/(a+b) = k (a+b+c ≠ 0) のとき、比例式 k の値は？", "1/2",
              ["1", "1/3", "2"], "a=k(b+c), b=k(c+a), c=k(a+b) をすべて足すと a+b+c = 2k(a+b+c)。a+b+c≠0 より k=1/2。")

    # 3) 相加平均・相乗平均と不等式の証明 (記述 4問 + 選択 5問 + ○× 3問)
    amgm_writes = [
        (1, 9, 2, "x > 0 のとき、x + 9/x の最小値"),
        (4, 1, 2, "x > 0 のとき、4x + 1/x の最小値"),
        (2, 8, 2, "x > 0 のとき、2x + 8/x の最小値"),
        (3, 12, 3, "x > 1 のとき、3x + 12/(x - 1) の最小値"),
    ]
    for a, b, diff, prompt in amgm_writes:
        if "x - 1" in prompt:
            # 3(x-1) + 12/(x-1) + 3 >= 2*sqrt(36) + 3 = 15
            ans = int(2 * math.isqrt(a * b) + a)
            exp = f"{a}(x-1) + {b}/(x-1) + {a} と変形し相加・相乗平均の関係を使うと 2√({a}×{b}) + {a} = {ans}（等号は x=3）。"
        else:
            ans = int(2 * math.isqrt(a * b))
            exp = f"相加・相乗平均の関係より {a}x + {b}/x >= 2√({a}x × {b}/x) = {ans}（等号は {a}x = {b}/x のとき）。"
        qb.add_write(sid, uid, diff, f"{prompt}はいくらか？", str(ans), exp)

    qb.add_mc(sid, uid, 2, "a > 0, b > 0 のとき、(a + 4/b)(b + 9/a) の最小値は？", "25",
              ["12", "13", "24"], "展開すると ab + 36/(ab) + 13 >= 2√36 + 13 = 12 + 13 = 25。")
    qb.add_mc(sid, uid, 2, "実数 x, y について常に成り立つ不等式 A^2 - B^2 >= 0 の関係を利用しやすい不等式の証明は？",
              "|a| + |b| >= |a + b|",
              ["a^2 + b^2 >= 2ab", "a/b + b/a >= 2", "x^2 + y^2 + 1 > 0"],
              "絶対値を含む不等式の証明では、両辺が0以上のとき2乗の差 (|a|+|b|)^2 - |a+b|^2 = 2(|ab|-ab) >= 0 を計算する。")
    qb.add_mc(sid, uid, 3, "実数 a, b, x, y について常に成り立つコーシー・シュワルツの不等式はどれか？",
              "(a^2 + b^2)(x^2 + y^2) >= (ax + by)^2",
              ["(a^2 + b^2)(x^2 + y^2) <= (ax + by)^2", "(a + b)(x + y) >= (ax + by)^2", "a^2 + x^2 >= 2(ax + by)"],
              "差をとると (ay - bx)^2 >= 0 となるため常に成り立つ。")
    qb.add_mc(sid, uid, 2, "a > 0, b > 0 の相加平均と相乗平均の大小関係において、等号が成立するための条件は？", "a = b",
              ["a + b = 1", "ab = 1", "a = 2b"], "(a + b)/2 - √(ab) = (√a - √b)^2 / 2 = 0 より √a = √b すなわち a = b。")
    qb.add_mc(sid, uid, 3, "a + b > 0 かつ ab > 0 のとき、相加相乗平均をそのまま使って x + 1/x の最小値を求める際に見落としがちな必須の確認事項は？",
              "各項が正であることと等号成立条件を満たす実数 x の存在",
              ["x が整数であること", "x^2 の係数が 1 であること", "判別式 D > 0 であること"],
              "相加・相乗平均の定理は両数が正でなければ使えず、最小値の主張には等号を成り立たせる x の存在確認が必須。")

    qb.add_ox(sid, uid, 1, "任意の実数 x, y について、x^2 + y^2 >= 2xy が成り立つ。", True,
              "x^2 - 2xy + y^2 = (x - y)^2 >= 0 より常に成り立つ。")
    qb.add_ox(sid, uid, 2, "任意の 0 でない実数 x について、x + 1/x >= 2 が成り立つ。", False,
              "x < 0 のときは負の値をとるため偽（正しくは x > 0 のとき成り立つ）。")
    qb.add_ox(sid, uid, 2, "三角不等式 |a + b| <= |a| + |b| において、等号が成り立つのは ab >= 0 のときである。", True,
              "a と b が同符号または少なくとも一方が 0 のとき、|a+b| = |a|+|b| となる。")

    # --- math2-u2: 複素数と方程式 (28問) ---
    uid = "math2-u2"
    # 1) 複素数の計算・負数の平方根 (記述 4問 + 選択 3問 + ○× 3問)
    c_ops = [
        (2, 3, 4, -5, "add", 1),
        (3, 2, 1, -4, "mul", 1),
        (5, 1, 2, -1, "mul", 2),
    ]
    for r1, i1, r2, i2, op, diff in c_ops:
        z1, z2 = complex(r1, i1), complex(r2, i2)
        res = (z1 + z2) if op == "add" else (z1 * z2)
        op_str = "+" if op == "add" else ""
        z1_s, z2_s = fmt_complex(r1, i1), fmt_complex(r2, i2)
        ans = fmt_complex(int(res.real), int(res.imag))
        q = f"({z1_s}) {op_str} ({z2_s}) を計算して a + bi の形で答えよ。" if op == "add" else f"({z1_s})({z2_s}) を計算して a + bi の形で答えよ。"
        exp = f"i^2 = -1 を用いて実部と虚部を整理すると {ans}。"
        qb.add_write(sid, uid, diff, q, ans, exp)

    qb.add_write(sid, uid, 2, "(4 + 2i) / (1 - i) を計算して a + bi の形で表せ。", "1 + 3i",
                 "分母・分子に 1 + i を掛けると (4 + 6i + 2i^2) / (1 - i^2) = (2 + 6i)/2 = 1 + 3i。")

    qb.add_mc(sid, uid, 1, "虚数単位 i について i^2026 の値はどれか？", "-1",
              ["1", "i", "-i"], "i^4 = 1 より 2026 = 4×506 + 2 なので i^2026 = i^2 = -1。")
    qb.add_mc(sid, uid, 2, "√(-2) × √(-8) を正しく計算すると？", "-4",
              ["4", "4i", "-4i"], "√(-2) = √2 i, √(-8) = 2√2 i より積は 4 i^2 = -4。")
    qb.add_mc(sid, uid, 2, "実数 x, y が (2 + i)x + (1 - 3i)y = 5 + 6i を満たすとき、(x, y) は？", "(3, -1)",
              ["(2, 1)", "(-1, 3)", "(3, 1)"],
              "(2x+y) + (x-3y)i = 5 + 6i より 2x+y=5, x-3y=6。解くと x=3, y=-1。")

    qb.add_ox(sid, uid, 1, "複素数 3 - 4i の共役な複素数は 3 + 4i である。", True,
              "共役な複素数は虚部の符号を反転させる。")
    qb.add_ox(sid, uid, 2, "任意の負の実数 a, b に対して √a √b = √(ab) が成り立つ。", False,
              "a < 0, b < 0 のときは √a √b = -√(ab) となる。")
    qb.add_ox(sid, uid, 2, "2つの複素数 z_1 = 2 + 3i と z_2 = 2 + 4i の間には大小関係 z_1 < z_2 が成り立つ。", False,
              "実数以外の複素数には大小関係（順序）を定義できない。")

    # 2) 解と係数の関係・2次方程式 (記述 4問 + 選択 3問)
    # x^2 - Sx + P = 0
    vieta_cases = [
        (5, 3, "α^2 + β^2", 5**2 - 2 * 3, 2, "α+β=5, αβ=3 より (α+β)^2 - 2αβ = 25 - 6 = 19。"),
        (4, 2, "α^3 + β^3", 4**3 - 3 * 4 * 2, 3, "α+β=4, αβ=2 より (α+β)^3 - 3αβ(α+β) = 64 - 24 = 40。"),
        (6, 5, "(α - β)^2", 6**2 - 4 * 5, 2, "(α-β)^2 = (α+β)^2 - 4αβ = 36 - 20 = 16。"),
        (3, -2, "1/α + 1/β", None, 2, "(α+β)/(αβ) = 3/(-2) = -3/2。"),
    ]
    for s, p, expr, val, diff, exp in vieta_cases:
        eq = fmt_poly_terms([(1, "x^2"), (-s, "x"), (p, "")])
        ans = fmt_frac(Fraction(s, p)) if val is None else str(val)
        qb.add_write(sid, uid, diff, f"2次方程式 {eq} = 0 の2つの解を α, β とするとき、{expr} の値は？", ans, exp)

    qb.add_mc(sid, uid, 2, "2数 1 + √3i と 1 - √3i を解にもつ2次方程式の1つはどれか？", "x^2 - 2x + 4 = 0",
              ["x^2 + 2x + 4 = 0", "x^2 - 2x - 2 = 0", "x^2 - 2x + 2 = 0"],
              "和は 2、積は 1^2 - (√3i)^2 = 1 + 3 = 4。よって x^2 - 2x + 4 = 0。")
    qb.add_mc(sid, uid, 2, "2次方程式 x^2 + 2x + 5 = 0 の複素数解は？", "-1 ± 2i",
              ["1 ± 2i", "-1 ± 4i", "-2 ± 2i"], "解の公式より x = -1 ± √(1 - 5) = -1 ± 2i。")
    qb.add_mc(sid, uid, 3, "2次方程式 x^2 - 4x + k = 0 の1つの解が他の解の 3倍 であるとき、定数 k の値は？", "3",
              ["4", "2", "12"], "解を α, 3α とすると和 4α = 4 ⇒ α = 1。積 3α^2 = 3 = k。")

    # 3) 剰余の定理・因数定理・高次方程式・ω (記述 5問 + 選択 4問 + ○× 2問)
    qb.add_write(sid, uid, 1, "多項式 P(x) = 2x^3 - 3x^2 + x + 4 を x + 1 で割った余りは？", "-2",
                 "P(-1) = 2(-1) - 3(1) + (-1) + 4 = -2 - 3 - 1 + 4 = -2。")
    qb.add_write(sid, uid, 2, "多項式 P(x) = x^3 + ax^2 - 5x + 6 が x - 2 を因数にもつとき、定数 a の値は？", "-1",
                 "因数定理より P(2) = 8 + 4a - 10 + 6 = 4a + 4 = 0。よって a = -1。")
    qb.add_write(sid, uid, 2, "3次方程式 x^3 - 6x^2 + 11x - 6 = 0 の最大の解は？", "3",
                 "(x - 1)(x - 2)(x - 3) = 0 より解は 1, 2, 3。最大の解は 3。")
    qb.add_write(sid, uid, 3, "整式 P(x) を x - 1 で割ると 3 余り、x + 2 で割ると -3 余る。P(x) を (x - 1)(x + 2) で割った余りを ax + b とするとき、a + b は？", "3",
                 "R(x) = ax + b とおくと R(1) = a+b = 3, R(-2) = -2a+b = -3。問題が求めるのは a+b なので即 3（実際 a=2, b=1）。")
    qb.add_write(sid, uid, 3, "3次方程式 x^3 + 2x^2 - 5x + 7 = 0 の3つの解を α, β, γ とするとき、αβ + βγ + γα の値は？", "-5",
                 "3次方程式 ax^3+bx^2+cx+d=0 の解と係数の関係より αβ+βγ+γα = c/a = -5。")

    qb.add_mc(sid, uid, 2, "3次方程式 x^3 - 1 = 0 の虚数解の1つを ω とするとき、ω^2 + ω + 1 の値は？", "0",
              ["1", "-1", "3"], "x^3 - 1 = (x - 1)(x^2 + x + 1) = 0 かつ ω ≠ 1 より ω^2 + ω + 1 = 0。")
    qb.add_mc(sid, uid, 3, "実数係数の3次方程式 x^3 + ax^2 + bx + c = 0 が x = 1 + 2i を解にもつとき、必ずもつもう1つの解は？", "1 - 2i",
              ["-1 + 2i", "-1 - 2i", "2 - i"], "実数係数の方程式が虚数解 α をもつとき、その共役複素数 ᾱ も解になる。")
    qb.add_mc(sid, uid, 2, "3次方程式 x^3 - 4x^2 + x + 6 = 0 の3つの解は？", "-1, 2, 3",
              ["1, -2, 3", "-1, -2, 3", "1, 2, -3"], "P(-1) = -1 - 4 - 1 + 6 = 0 より (x + 1)(x^2 - 5x + 6) = (x+1)(x-2)(x-3) = 0。")
    qb.add_mc(sid, uid, 3, "4次方程式 x^4 - 3x^2 - 4 = 0 の実数解はいくつあるか？", "2個",
              ["4個", "0個", "1個"], "(x^2 - 4)(x^2 + 1) = 0 より x^2 = 4 (実数解 ±2) と x^2 = -1 (虚数解 ±i)。実数解は2個。")

    qb.add_ox(sid, uid, 2, "1の3乗根のうち虚数であるものの1つを ω とすると、ω^10 = ω である。", True,
              "ω^3 = 1 なので ω^10 = (ω^3)^3 × ω = ω。")
    qb.add_ox(sid, uid, 3, "複素数を係数とする2次方程式が 1 + i を解にもつとき、1 - i も必ず解になる。", False,
              "共役解が保証されるのは「実数係数」のときのみ。虚数係数の方程式では成り立つとは限らない。")

    # --- math2-u3: 図形と方程式 (28問) ---
    uid = "math2-u3"
    # 1) 座標・内分・外分・重心 (記述 4問 + 選択 2問)
    qb.add_write(sid, uid, 1, "2点 A(1, 2), B(4, 6) の間の距離は？", "5",
                 "√((4 - 1)^2 + (6 - 2)^2) = √(9 + 16) = 5。")
    qb.add_write(sid, uid, 1, "3点 A(1, 2), B(5, -4), C(3, 8) を頂点とする △ABC の重心の座標は？", "(3, 2)",
                 "((1+5+3)/3, (2-4+8)/3) = (9/3, 6/3) = (3, 2)。")
    qb.add_write(sid, uid, 2, "2点 A(-2, 1), B(6, 5) を結ぶ線分 AB を 3 : 1 に内分する点の座標は？", "(4, 4)",
                 "((1×(-2) + 3×6)/4, (1×1 + 3×5)/4) = (16/4, 16/4) = (4, 4)。")
    qb.add_write(sid, uid, 2, "点 P(3, -5) と直線 y = x に関して対称な点 Q の座標は？", "(-5, 3)",
                 "直線 y = x に関する対称点は x 座標と y 座標を入れ替えた (-5, 3)。")

    qb.add_mc(sid, uid, 2, "2点 A(1, 4), B(5, -2) を結ぶ線分 AB を 3 : 1 に外分する点の座標は？", "(7, -5)",
              ["(-1, 7)", "(4, -0.5)", "(3, 1)"],
              "((-1×1 + 3×5)/(3-1), (-1×4 + 3×(-2))/(3-1)) = (14/2, -10/2) = (7, -5)。")
    qb.add_mc(sid, uid, 3, "点 A(1, 3) の、点 P(4, 1) に関する対称点の座標は？", "(7, -1)",
              ["(5/2, 2)", "(-2, 5)", "(6, -1)"],
              "P が対称点 Q(x, y) と A の中点なので (1+x)/2 = 4, (3+y)/2 = 1 より x=7, y=-1。")

    # 2) 直線・点と直線の距離 (記述 5問 + 選択 3問)
    qb.add_write(sid, uid, 1, "2点 (1, 2), (3, 8) を通る直線の傾きは？", "3",
                 "(8 - 2) / (3 - 1) = 6 / 2 = 3。")
    qb.add_write(sid, uid, 2, "直線 2x + 3y - 5 = 0 に垂直で、原点を通る直線の傾きを既約分数で答えよ。", "3/2",
                 "元の直線の傾きは -2/3。垂直条件 m1 m2 = -1 より求める傾きは 3/2。")
    qb.add_write(sid, uid, 2, "点 (2, 1) と直線 3x + 4y - 25 = 0 の距離は？", "3",
                 "|3×2 + 4×1 - 25| / √(3^2 + 4^2) = |6 + 4 - 25| / 5 = 15 / 5 = 3。")
    qb.add_write(sid, uid, 2, "点 (1, -2) と直線 5x - 12y - 3 = 0 の距離は？", "2",
                 "|5×1 - 12×(-2) - 3| / √(5^2 + (-12)^2) = |5 + 24 - 3| / 13 = 26 / 13 = 2。")
    qb.add_write(sid, uid, 3, "2直線 ax + 2y - 1 = 0 と 3x - 6y + 4 = 0 が直交するとき、定数 a の値は？", "4",
                 "一般形 a1 x + b1 y + c1 = 0 との直交条件 a1 a2 + b1 b2 = 0 より 3a + 2×(-6) = 0 ⇒ a = 4。")

    qb.add_mc(sid, uid, 1, "x 切片が 2、y 切片が -3 である直線の方程式は？", "x/2 - y/3 = 1",
              ["x/2 + y/3 = 1", "3x + 2y = 6", "2x - 3y = 1"],
              "切片形 x/a + y/b = 1 に a=2, b=-3 を代入する。")
    qb.add_mc(sid, uid, 2, "平行な2直線 3x - 4y + 2 = 0 と 3x - 4y - 8 = 0 の間の距離は？", "2",
              ["10", "5", "6/5"], "1つ目の直線上の点 (2, 2) と2つ目の直線の距離は |3×2 - 4×2 - 8| / 5 = 10/5 = 2。")
    qb.add_mc(sid, uid, 3, "点 A(4, 3) の、直線 y = 2x に関する対称点 B の座標は？", "(0, 5)",
              ["(-4, 3)", "(3, 4)", "(2, 4)"],
              "A(4, 3) と B(0, 5) の中点 (2, 4) は直線 y = 2x 上にあり、線分 AB の傾き (5-3)/(0-4) = -1/2 は直線と垂直である。")

    # 3) 円の方程式・接線・位置関係 (記述 4問 + 選択 4問)
    qb.add_write(sid, uid, 1, "中心 (2, -3)、半径 4 の円の方程式 (x - a)^2 + (y - b)^2 = r^2 における r^2 の値は？", "16",
                 "半径 r = 4 より右辺は 4^2 = 16。")
    qb.add_write(sid, uid, 2, "円 x^2 + y^2 - 4x + 6y - 12 = 0 の半径は？", "5",
                 "平方完成すると (x - 2)^2 + (y + 3)^2 = 4 + 9 + 12 = 25。よって半径は √25 = 5。")
    qb.add_write(sid, uid, 2, "円 x^2 + y^2 = 25 上の点 (3, 4) における接線 3x + 4y = k の k の値は？", "25",
                 "円 x^2+y^2=r^2 上の点 (x0, y0) の接線は x0 x + y0 y = r^2 なので 3x + 4y = 25。")
    qb.add_write(sid, uid, 3, "円 x^2 + y^2 = 25 が直線 3x + 4y - 20 = 0 から切り取る弦の長さは？", "6",
                 "中心 (0, 0) と直線の距離 d = |-20|/5 = 4。半径 r = 5 より弦の長さは 2√(5^2 - 4^2) = 2×3 = 6。")

    qb.add_mc(sid, uid, 1, "円 (x + 1)^2 + (y - 5)^2 = 9 の中心の座標は？", "(-1, 5)",
              ["(1, -5)", "(1, 5)", "(-1, -5)"], "(x - a)^2 + (y - b)^2 = r^2 の形より中心は (-1, 5)。")
    qb.add_mc(sid, uid, 2, "直線 y = x + k が円 x^2 + y^2 = 8 に接するとき、正の定数 k の値は？", "4",
              ["2√2", "8", "2"], "中心と直線 x - y + k = 0 の距離 |k|/√2 = 2√2 より |k| = 4。正なので k = 4。")
    qb.add_mc(sid, uid, 3, "2点 A(1, 2), B(5, -4) を直径の両端とする円の中心と半径の組は？", "中心 (3, -1), 半径 √13",
              ["中心 (3, -1), 半径 2√13", "中心 (2, -3), 半径 √13", "中心 (3, 1), 半径 13"],
              "中心は AB の中点 (3, -1)、半径は中心と A の距離 √((3-1)^2 + (-1-2)^2) = √13。")
    qb.add_mc(sid, uid, 3, "2つの円 x^2 + y^2 = 4 と (x - 3)^2 + (y - 4)^2 = 9 の位置関係は？", "外接する",
              ["2点で交わる", "内接する", "離れている"],
              "中心間距離 d = √(3^2 + 4^2) = 5、半径の和 R + r = 2 + 3 = 5。d = R + r より外接する。")

    # 4) 軌跡と領域 (記述 2問 + 選択 2問 + ○× 2問) -> 8+8+8+6 = 30? 確認: 5+3=8, 5+3=8, 4+5+3=12? あれ上を数えよう:
    # u1: 5+3 + 5+3 + 4+5+3 = 28. OK!
    # u2: (4+3+3=10) + (4+3=7) + (5+4+2=11) = 28. OK!
    # u3: (4+2=6) + (5+3=8) + (4+4=8) + 残り6問 = 28!
    qb.add_write(sid, uid, 3, "x >= 0, y >= 0, x + y <= 4, 2x + y <= 6 を満たすとき、x + 2y の最大値は？", "8",
                 "領域の頂点は (0,0), (3,0), (2,2), (0,4)。k = x + 2y は (0, 4) で最大値 0 + 2×4 = 8 をとる。")
    qb.add_write(sid, uid, 3, "2点 A(-3, 0), B(3, 0) からの距離の比が AP : BP = 2 : 1 である点 P の軌跡（アポロニウスの円）の半径は？", "4",
                 "(x+3)^2+y^2 = 4((x-3)^2+y^2) を整理すると (x - 5)^2 + y^2 = 16。よって半径は 4。")

    qb.add_mc(sid, uid, 2, "2点 A(1, 2), B(5, 6) から等距離にある点 P の軌跡はどのような図形か？",
              "線分 AB の垂直二等分線 x + y = 7",
              ["線分 AB を直径とする円", "直線 y = x + 1", "点 (3, 4) のみ"],
              "PA = PB を満たす点の軌跡は線分 AB の垂直二等分線。中点 (3, 4)、AB の傾き 1 より傾き -1 の直線 x + y = 7。")
    qb.add_mc(sid, uid, 2, "不等式 y > x^2 - 2x が表す座標平面上の領域は、放物線 y = x^2 - 2x のどちら側か？",
              "上側（境界線を含まない）",
              ["下側（境界線を含まない）", "上側（境界線を含む）", "下側（境界線を含む）"],
              "y > f(x) は境界線の上側を表し、等号がないため境界線は含まない。")

    qb.add_ox(sid, uid, 2, "不等式 (x - y)(x + y - 2) < 0 の表す領域には、原点 (0, 0) が含まれる。", False,
              "(0, 0) を代入すると (0)(-2) = 0 となり < 0 を満たさない。")
    qb.add_ox(sid, uid, 2, "点 (x, y) が円 (x - 1)^2 + (y - 2)^2 = 4 の周および内部を動くとき、原点からの距離の最大値は √5 + 2 である。", True,
              "中心 (1, 2) と原点の距離が √5 なので、最大値は中心までの距離＋半径 = √5 + 2。")

    # --- math2-u4: 三角関数 (28問) ---
    uid = "math2-u4"
    # 1) 弧度法・扇形 (記述 4問 + 選択 2問)
    qb.add_write(sid, uid, 1, "弧度法 5π/6 [rad] を度数法で表すと何度か（数値のみ）？", "150",
                 "π = 180° より 5 × 180° / 6 = 150°。", alt=["150°"])
    qb.add_write(sid, uid, 1, "半径 6、中心角 π/3 の扇形の弧の長さ l を π を用いて表せ（例: 2π）。", "2π",
                 "l = rθ = 6 × (π/3) = 2π。", alt=["2pi"])
    qb.add_write(sid, uid, 2, "半径 4、中心角 π/4 の扇形の面積 S を π を用いて表せ。", "2π",
                 "S = (1/2) r^2 θ = (1/2) × 16 × (π/4) = 2π。", alt=["2pi"])
    qb.add_write(sid, uid, 2, "半径 5、弧の長さ 4π の扇形の面積は？（π を用いて表せ）", "10π",
                 "S = (1/2) r l = (1/2) × 5 × 4π = 10π。", alt=["10pi"])

    qb.add_mc(sid, uid, 1, "240° を弧度法で表すと？", "4π/3",
              ["3π/4", "5π/3", "7π/6"], "240° × (π / 180°) = 4π/3。")
    qb.add_mc(sid, uid, 2, "次のうち、一般角として π/6 と動径が同じ位置を表す角は？", "13π/6",
              ["7π/6", "5π/6", "-π/6"], "π/6 + 2π = 13π/6（2π の整数倍の差は同じ動径）。")

    # 2) 一般角の三角関数・性質 (選択 5問 + ○× 3問)
    qb.add_mc(sid, uid, 1, "sin(7π/6) の値は？", "-1/2", ["1/2", "-√3/2", "√3/2"],
              "7π/6 = π + π/6 は第3象限の角なので sin は負で -sin(π/6) = -1/2。")
    qb.add_mc(sid, uid, 1, "cos(5π/4) の値は？", "-√2/2", ["√2/2", "-1/2", "-√3/2"],
              "5π/4 = π + π/4 は第3象限なので -cos(π/4) = -√2/2。")
    qb.add_mc(sid, uid, 2, "tan(-π/3) の値は？", "-√3", ["√3", "-1/√3", "1/√3"],
              "tan(-θ) = -tanθ より -tan(π/3) = -√3。")
    qb.add_mc(sid, uid, 2, "関数 y = sin 2x の周期はいくらか？", "π",
              ["2π", "π/2", "4π"], "y = sin kx の周期は 2π / |k| = 2π / 2 = π。")
    qb.add_mc(sid, uid, 2, "sin(θ + π/2) と常に等しいものはどれか？", "cosθ",
              ["-cosθ", "sinθ", "-sinθ"], "y = sinθ のグラフを左に π/2 平行移動すると y = cosθ に重なる。")

    qb.add_ox(sid, uid, 1, "関数 y = cosθ は偶関数であり、cos(-θ) = cosθ が成り立つ。", True,
              "y 軸対称なグラフをもつため cos(-θ) = cosθ。")
    qb.add_ox(sid, uid, 2, "関数 y = tanθ の周期は 2π であり、π より小さい周期は存在しない。", False,
              "y = tanθ の周期は π である。")
    qb.add_ox(sid, uid, 2, "関数 y = 3 sin(2x - π/3) の最大値は 3、最小値は -3 である。", True,
              "-1 <= sin(...) <= 1 なので 3倍すると [-3, 3] をとる。")

    # 3) 加法定理 (選択 4問 + 記述 2問)
    qb.add_mc(sid, uid, 2, "加法定理を用いて sin 75° の値を求めると？", "(√6 + √2)/4",
              ["(√6 - √2)/4", "(√3 + 1)/2", "(√6 + √2)/2"],
              "sin(45°+30°) = sin45°cos30° + cos45°sin30° = (√2/2)(√3/2) + (√2/2)(1/2) = (√6+√2)/4。")
    qb.add_mc(sid, uid, 2, "加法定理を用いて cos 15° の値を求めると？", "(√6 + √2)/4",
              ["(√6 - √2)/4", "(√3 - 1)/4", "(√6 - √2)/2"],
              "cos(45°-30°) = cos45°cos30° + sin45°sin30° = (√6 + √2)/4。")
    qb.add_mc(sid, uid, 3, "tan 15° の値を求めると？", "2 - √3",
              ["2 + √3", "√3 - 1", "1 / (2 - √3)"],
              "tan(45°-30°) = (1 - 1/√3)/(1 + 1/√3) = (√3 - 1)/(√3 + 1) = (4 - 2√3)/2 = 2 - √3。")
    qb.add_mc(sid, uid, 3, "2直線 y = 2x と y = -3x のなす鋭角は？（tanθ の加法定理を利用）", "45°",
              ["30°", "60°", "90°"],
              "傾き m1=2, m2=-3 のとき m1 m2 = -6 ≠ -1。tanθ = |(2 - (-3)) / (1 + 2(-3))| = |5 / -5| = 1 より θ = 45°。")

    qb.add_write(sid, uid, 2, "sinα = 3/5, cosβ = 12/13 (α, β はともに鋭角) のとき、sin(α + β) の値を既約分数で答えよ。", "56/65",
                 "cosα = 4/5, sinβ = 5/13。sin(α+β) = (3/5)(12/13) + (4/5)(5/13) = (36 + 20)/65 = 56/65。")
    qb.add_write(sid, uid, 3, "tanα = 1/2, tanβ = 1/3 (α, β は鋭角) のとき、α + β は何度か（数値のみ）？", "45",
                 "tan(α+β) = (1/2 + 1/3)/(1 - 1/6) = (5/6)/(5/6) = 1。0 < α+β < π より 45°。", alt=["45°"])

    # 4) 2倍角・半角・合成・方程式 (記述 3問 + 選択 3問 + ○× 2問) -> 6+8+6+8 = 28問!
    qb.add_write(sid, uid, 2, "sinα = 3/5 (0 < α < π/2) のとき、sin 2α の値を既約分数で答えよ。", "24/25",
                 "cosα = 4/5 より sin2α = 2 sinα cosα = 2 × (3/5) × (4/5) = 24/25。")
    qb.add_write(sid, uid, 2, "cosθ = 1/3 のとき、cos 2θ の値を既約分数で答えよ。", "-7/9",
                 "cos 2θ = 2 cos^2θ - 1 = 2(1/9) - 1 = -7/9。")
    qb.add_write(sid, uid, 2, "関数 y = 3 sinθ + 4 cosθ (0 <= θ < 2π) の最大値は？", "5",
                 "三角関数の合成により √(3^2 + 4^2) sin(θ + α) = 5 sin(θ + α)。よって最大値は 5。")

    qb.add_mc(sid, uid, 2, "半角の公式 sin^2(θ/2) を cosθ で表すと？", "(1 - cosθ)/2",
              ["(1 + cosθ)/2", "(1 - cos2θ)/2", "1 - cosθ"],
              "2倍角の公式 cosθ = 1 - 2 sin^2(θ/2) を変形して得る。")
    qb.add_mc(sid, uid, 2, "√3 sinθ - cosθ を r sin(θ - α) (r > 0, 0 <= α < 2π) の形に合成すると？", "2 sin(θ - π/6)",
              ["2 sin(θ - π/3)", "2 sin(θ + π/6)", "2 cos(θ - π/3)"],
              "r = √(3+1) = 2。cosα = √3/2, sinα = 1/2 となるのは α = π/6 なので 2 sin(θ - π/6)。")
    qb.add_mc(sid, uid, 3, "0 <= θ < 2π において方程式 cos 2θ + cosθ = 0 の解の個数は？", "3個",
              ["2個", "4個", "1個"],
              "2cos^2θ + cosθ - 1 = (2cosθ - 1)(cosθ + 1) = 0 より cosθ = 1/2 (解2個: π/3, 5π/3) または cosθ = -1 (解1個: π) の計3個。")

    qb.add_ox(sid, uid, 2, "0 <= θ < 2π で sinθ = 1/2 を満たす θ は θ = π/6, 5π/6 の2つである。", True,
              "y = 1/2 となる単位円上の点は第1象限と第2象限にある。")
    qb.add_ox(sid, uid, 3, "y = sinθ + cosθ の最大値は 2 である。", False,
              "合成すると √2 sin(θ + π/4) となるため、最大値は 2 ではなく √2 である。")

    # --- math2-u5: 指数関数と対数関数 (28問) ---
    uid = "math2-u5"
    # 1) 累乗根・指数計算 (記述 5問 + 選択 2問)
    exp_writes = [
        ("8^(2/3)", "4", 1, "8 = 2^3 より (2^3)^(2/3) = 2^2 = 4。"),
        ("27^(-2/3)", "1/9", 2, "27 = 3^3 より (3^3)^(-2/3) = 3^(-2) = 1/9。"),
        ("16^(3/4)", "8", 1, "16 = 2^4 より 2^3 = 8。"),
        ("2^(1/2) × 2^(3/2)", "4", 1, "指数法則より 2^(1/2 + 3/2) = 2^2 = 4。"),
        ("9^(3/2) ÷ 27^(1/3)", "9", 2, "3^3 ÷ 3^1 = 3^2 = 9。"),
    ]
    for expr, ans, diff, exp in exp_writes:
        qb.add_write(sid, uid, diff, f"{expr} の値を求めよ。", ans, exp)

    qb.add_mc(sid, uid, 2, "3乗根 √[3]{-64} の値はどれか？", "-4",
              ["4", "8", "-8"], "(-4)^3 = -64 なので実数の3乗根は -4。")
    qb.add_mc(sid, uid, 3, "4^(3/2), 8^(2/3), 2^(5/2) を小さい順に並べたものは？", "8^(2/3) < 2^(5/2) < 4^(3/2)",
              ["2^(5/2) < 8^(2/3) < 4^(3/2)", "8^(2/3) < 4^(3/2) < 2^(5/2)", "4^(3/2) < 8^(2/3) < 2^(5/2)"],
              "底を2に揃えると 4^(3/2)=2^3, 8^(2/3)=2^2, 2^(5/2)=2^2.5。指数を比較して 2 < 2.5 < 3。")

    # 2) 対数の計算 (記述 6問 + 選択 3問)
    log_writes = [
        ("log_2(16)", "4", 1, "2^4 = 16 より 4。"),
        ("log_3(1/27)", "-3", 1, "27 = 3^3 より 1/27 = 3^(-3)、よって -3。"),
        ("log_2(12) - log_2(3)", "2", 1, "log_2(12/3) = log_2(4) = 2。"),
        ("log_6(4) + log_6(9)", "2", 2, "log_6(4×9) = log_6(36) = 2。"),
        ("log_2(3) × log_3(8)", "3", 2, "底の変換公式より (log 3 / log 2) × (log 8 / log 3) = log_2(8) = 3。"),
        ("2^(log_2(7))", "7", 2, "対数の定義 a^(log_a(M)) = M より 7。"),
    ]
    for expr, ans, diff, exp in log_writes:
        qb.add_write(sid, uid, diff, f"{expr} の値は？", ans, exp)

    qb.add_mc(sid, uid, 2, "log_4(8) の値はどれか？", "3/2",
              ["2", "2/3", "3"], "底を2に変換すると log_2(8)/log_2(4) = 3/2。")
    qb.add_mc(sid, uid, 2, "対数 log_a(M) が定義されるための底 a と真数 M の条件は？",
              "a > 0, a ≠ 1 かつ M > 0",
              ["a > 0 かつ M > 0", "a > 1 かつ M > 0", "a ≠ 0 かつ M >= 0"],
              "底は1でない正の数、真数は正の数（真数条件 M > 0）でなければならない。")
    qb.add_mc(sid, uid, 3, "(log_2(9) + log_4(3)) × log_3(4) の値は？", "5",
              ["4", "6", "9/2"], "log_2(9)=2 log_2(3), log_4(3)=(1/2)log_2(3) より合計 (5/2)log_2(3)。これに 2 log_3(2) を掛けて 5。")

    # 3) 方程式・不等式・グラフ (記述 3問 + 選択 3問 + ○× 3問)
    qb.add_write(sid, uid, 1, "指数方程式 4^x = 32 の解 x を分数で答えよ。", "5/2",
                 "2^(2x) = 2^5 より 2x = 5、よって x = 5/2。")
    qb.add_write(sid, uid, 2, "対数方程式 log_2(x - 1) = 3 の解 x は？", "9",
                 "真数条件 x > 1。x - 1 = 2^3 = 8 より x = 9。")
    qb.add_write(sid, uid, 3, "方程式 4^x - 6・2^x + 8 = 0 の2つの解の和は？", "3",
                 "t = 2^x (> 0) とおくと t^2 - 6t + 8 = (t-2)(t-4) = 0。t=2, 4 より x=1, 2。和は 1+2 = 3。")

    qb.add_mc(sid, uid, 2, "不等式 (1/2)^x > 8 の解は？", "x < -3",
              ["x > -3", "x > 3", "x < 3"], "(1/2)^x > (1/2)^(-3)。底 1/2 < 1 なので不等号が逆転し x < -3。")
    qb.add_mc(sid, uid, 2, "不等式 log_{1/3}(x - 2) >= -1 の解は？", "2 < x <= 5",
              ["x <= 5", "x >= 5", "2 <= x <= 5"], "真数条件 x > 2。底 1/3 < 1 より x - 2 <= (1/3)^(-1) = 3、よって 2 < x <= 5。")
    qb.add_mc(sid, uid, 3, "方程式 log_2(x) + log_2(x - 2) = 3 の解 x は？", "4",
              ["-2 と 4", "2", "6"], "真数条件 x > 2。x(x - 2) = 8 より (x-4)(x+2)=0。x > 2 より x = 4 のみ。")

    qb.add_ox(sid, uid, 1, "指数関数 y = a^x (a > 0, a ≠ 1) のグラフは、底 a の値にかかわらず必ず点 (0, 1) を通る。", True,
              "x = 0 のとき a^0 = 1 となるため必ず (0, 1) を通る。")
    qb.add_ox(sid, uid, 2, "対数関数 y = log_{0.5}(x) は x > 0 で単調増加する関数である。", False,
              "底 0.5 が 0 < a < 1 の範囲にあるため単調減少関数である。")
    qb.add_ox(sid, uid, 2, "指数関数 y = 2^x のグラフと対数関数 y = log_2(x) のグラフは、直線 y = x に関して対称である。", True,
              "互いに逆関数の関係にあるため直線 y = x に関して対称になる。")

    # 4) 常用対数 (記述 2問 + 選択 1問) -> 7+9+9+3 = 28問!
    d250 = math.floor(50 * 0.3010) + 1  # 16桁
    qb.add_write(sid, uid, 2, "log10(2) = 0.3010 とするとき、2^50 は何桁の整数か？（整数のみで答えよ）", str(d250),
                 f"log10(2^50) = 50 × 0.3010 = 15.05。15 <= log10(2^50) < 16 より {d250}桁。", alt=[f"{d250}桁"])
    # (1/2)^20 の小数第何位: 20 * 0.3010 = 6.02 -> -7 <= -6.02 < -6 -> 小数第7位!
    qb.add_write(sid, uid, 3, "log10(2) = 0.3010 とするとき、(1/2)^20 を小数で表すと小数第何位に初めて0でない数字が現れるか（整数のみ）？", "7",
                 "log10((1/2)^20) = -20 × 0.3010 = -6.02。-7 <= -6.02 < -6 より小数第7位。", alt=["第7位", "7位"])
    qb.add_mc(sid, uid, 3, "log10(2) = 0.3010, log10(3) = 0.4771 とするとき、6^20 の最高位の数字はどれか？", "3",
              ["1", "2", "6"],
              "log10(6^20) = 20(0.3010 + 0.4771) = 20 × 0.7781 = 15.562。小数部分 0.562 について log10(3)=0.4771 < 0.562 < log10(4)=0.6020 より最高位は 3。")

    # --- math2-u6: 微分法と積分法 (28問) ---
    uid = "math2-u6"
    # 1) 極限・微分係数・接線 (記述 4問 + 選択 2問)
    qb.add_write(sid, uid, 1, "極限値 lim_{x→2} (x^2 - 4) / (x - 2) の値は？", "4",
                 "(x - 2)(x + 2)/(x - 2) = x + 2 → 2 + 2 = 4。")
    qb.add_write(sid, uid, 1, "関数 f(x) = x^3 - 2x において、x = 2 における微分係数 f'(2) は？", "10",
                 "f'(x) = 3x^2 - 2 より f'(2) = 3(4) - 2 = 10。")
    qb.add_write(sid, uid, 2, "放物線 y = x^2 上の点 (3, 9) における接線の傾きは？", "6",
                 "y' = 2x より x = 3 のときの接線の傾きは 2×3 = 6。")
    qb.add_write(sid, uid, 3, "極限値 lim_{h→0} (f(1 + 2h) - f(1)) / h を f'(1) を用いて表すと何倍の f'(1) か？（数値のみ）", "2",
                 "2 × lim_{h→0} (f(1 + 2h) - f(1)) / (2h) = 2 f'(1)。")

    qb.add_mc(sid, uid, 2, "曲線 y = x^3 - 3x 上の点 (2, 2) における接線の方程式は？", "y = 9x - 16",
              ["y = 9x - 2", "y = 3x - 4", "y = 9x + 16"],
              "y' = 3x^2 - 3 より傾きは 3(4) - 3 = 9。よって y - 2 = 9(x - 2) ⇒ y = 9x - 16。")
    qb.add_mc(sid, uid, 3, "点 (0, -4) から放物線 y = x^2 に引いた接線の接点の x 座標として正しい組は？", "x = ±2",
              ["x = ±1", "x = ±4", "x = 2 のみ"],
              "接点 (t, t^2) での接線 y = 2tx - t^2 が (0, -4) を通るより -t^2 = -4 ⇒ t = ±2。")

    # 2) 導関数・極値・増減 (記述 5問 + 選択 3問 + ○× 2問)
    # 綺麗な整数極値になる3次関数: f'(x) = 3(x-a)(x-b) -> a, b 同偶奇なら整数になりやすい
    cubic_specs = [
        # f'(x) = 3x^2 - 12 = 3(x-2)(x+2) -> f(x) = x^3 - 12x + 5, 極大 x=-2 (21), 極小 x=2 (-11)
        (1, 0, -12, 5, "極小値", -11, 2),
        (1, 0, -12, 5, "極大値", 21, 2),
        # f'(x) = 6x^2 - 24x + 18 = 6(x-1)(x-3) -> f(x) = 2x^3 - 12x^2 + 18x + 1 -> 極大 x=1 (9), 極小 x=3 (1)
        (2, -12, 18, 1, "極大値", 9, 2),
        (2, -12, 18, 1, "極小値", 1, 2),
    ]
    for a3, a2, a1, a0, target, ans_v, diff in cubic_specs:
        f_str = fmt_poly_terms([(a3, "x^3"), (a2, "x^2"), (a1, "x"), (a0, "")])
        df_str = fmt_poly_terms([(3 * a3, "x^2"), (2 * a2, "x"), (a1, "")])
        qb.add_write(sid, uid, diff, f"3次関数 f(x) = {f_str} の{target}は？", str(ans_v),
                     f"f'(x) = {df_str} = 0 を解いて増減表を作ると、{target}は {ans_v}。")

    qb.add_write(sid, uid, 2, "f(x) = 2x^3 - 3x^2 + 5x - 1 の導関数 f'(x) を求めよ。", "6x^2 - 6x + 5",
                 "各項を微分すると 6x^2 - 6x + 5。", alt=["6x²-6x+5"])

    qb.add_mc(sid, uid, 2, "3次関数 f(x) = x^3 + kx^2 + 3x + 1 が極値をもたないような定数 k の値の範囲は？",
              "-3 <= k <= 3", ["k < -3, 3 < k", "-3 < k < 3", "k = ±3 のみ"],
              "f'(x) = 3x^2 + 2kx + 3 >= 0 が常に成り立つ条件は D/4 = k^2 - 9 <= 0、すなわち -3 <= k <= 3。")
    qb.add_mc(sid, uid, 3, "方程式 x^3 - 3x + k = 0 が異なる3つの実数解をもつような定数 k の範囲は？",
              "-2 < k < 2", ["k < -2, 2 < k", "-2 <= k <= 2", "0 < k < 4"],
              "f(x) = x^3 - 3x の極大値は f(-1)=2、極小値は f(1)=-2。y = -k がその間にあるとき3解なので -2 < k < 2。")
    qb.add_mc(sid, uid, 2, "関数 f(x) = x^3 - 3x^2 - 9x + 2 の区間 [-2, 4] における最大値は？", "7",
              ["2", "10", "-25"], "f'(x)=3(x+1)(x-3)。候補は端点 f(-2)=0, f(4)=-18 と極大 f(-1)=7 より最大値は 7。")

    qb.add_ox(sid, uid, 2, "関数 f(x) において f'(a) = 0 ならば、f(x) は x = a で必ず極値をとる。", False,
              "反例: f(x) = x^3 では f'(0) = 0 だが単調増加で x = 0 で極値をとらない。前後の符号変化が必要。")
    qb.add_ox(sid, uid, 2, "3次関数 f(x) = ax^3 + bx^2 + cx + d (a ≠ 0) は、極値を1つだけ持つことはあり得ない。", True,
              "f'(x) は2次関数なので、符号変化が2回起きる（極大・極小両方ある）か0回（極値なし）のどちらかになる。")

    # 3) 積分計算・定積分 (記述 5問 + 選択 2問)
    qb.add_write(sid, uid, 1, "定積分 ∫_0^2 (3x^2 + 2x + 1) dx の値は？", "14",
                 "[x^3 + x^2 + x]_0^2 = 8 + 4 + 2 = 14。")
    qb.add_write(sid, uid, 2, "定積分 ∫_{-2}^2 (5x^3 - 3x^2 + 4x - 1) dx の値は？", "-20",
                 "奇関数(x^3, x)の対称区間積分は0。2∫_0^2 (-3x^2 - 1) dx = 2[-x^3 - x]_0^2 = 2(-8 - 2) = -20。")
    qb.add_write(sid, uid, 2, "不定積分 ∫ (6x^2 - 4x + 3) dx (積分定数は C とする) を求めよ。", "2x^3 - 2x^2 + 3x + C",
                 "各項を積分して定数項 C を加えると 2x^3 - 2x^2 + 3x + C。", alt=["2x³-2x²+3x+C"])
    qb.add_write(sid, uid, 3, "関数 f(x) = 3x^2 + ∫_0^2 f(t) dt を満たすとき、f(0) の値は？", "-8",
                 "定積分 ∫_0^2 f(t) dt = k とおくと f(x) = 3x^2 + k。k = [t^3 + kt]_0^2 = 8 + 2k より k = -8。よって f(0) = -8。")
    qb.add_write(sid, uid, 2, "d/dx ∫_1^x (t^2 - 3t + 5) dt について、x = 2 におけるこの導関数の値は？", "3",
                 "微積分学の基本定理より d/dx ∫_a^x f(t) dt = f(x) なので x^2 - 3x + 5。x=2 で 4 - 6 + 5 = 3。")

    qb.add_mc(sid, uid, 2, "F'(x) = 3x^2 - 4x で F(1) = 2 を満たす関数 F(x) は？", "x^3 - 2x^2 + 3",
              ["x^3 - 2x^2 + 2", "x^3 - 4x^2 + 5", "x^3 - 2x^2 - 1"],
              "F(x) = x^3 - 2x^2 + C。F(1) = 1 - 2 + C = 2 より C = 3。")
    qb.add_mc(sid, uid, 3, "∫_1^3 (x - 1)(x - 3) dx の値は？（1/6公式を利用）", "-4/3",
              ["4/3", "-8/3", "-2/3"], "∫_α^β (x-α)(x-β) dx = -(1/6)(β-α)^3 = -(1/6)×2^3 = -4/3。")

    # 4) 面積 (記述 3問 + 選択 2問) -> 6+10+7+5 = 28問!
    qb.add_write(sid, uid, 2, "放物線 y = x^2 - 4x + 3 と x 軸で囲まれた部分の面積を既約分数で答えよ。", "4/3",
                 "x 軸との交点は x = 1, 3。1/6 公式より (1/6)(3 - 1)^3 = 8/6 = 4/3。")
    qb.add_write(sid, uid, 2, "放物線 y = x^2 と直線 y = 2x + 3 で囲まれた部分の面積を既約分数で答えよ。", "32/3",
                 "交点は x^2 - 2x - 3 = 0 より x = -1, 3。面積は (1/6)(3 - (-1))^3 = 64/6 = 32/3。")
    qb.add_write(sid, uid, 3, "2つの放物線 y = x^2 と y = -x^2 + 8 で囲まれた部分の面積を既約分数で答えよ。", "64/3",
                 "2x^2 - 8 = 0 より交点は x = ±2。面積は (|1 - (-1)|/6)(2 - (-2))^3 = (2/6)×64 = 64/3。")

    qb.add_mc(sid, uid, 2, "曲線 y = x^2 (0 <= x <= 3) と x 軸および直線 x = 3 で囲まれた図形の面積は？", "9",
              ["27", "9/2", "3"], "∫_0^3 x^2 dx = [x^3 / 3]_0^3 = 27 / 3 = 9。")
    qb.add_mc(sid, uid, 3, "3次曲線 y = x^3 - x と x 軸で囲まれた2つの部分の面積の和は？", "1/2",
              ["0", "1/4", "1"], "交点は x = -1, 0, 1。対称性より 2 ∫_0^1 (x - x^3) dx = 2 [x^2/2 - x^4/4]_0^1 = 2(1/4) = 1/2。")


# ============================================================
# 4. 数学B (mathB): 2単元 × 85問 = 170問
# ============================================================

def generate_mathB(qb: QuestionBank) -> None:
    sid = "mathB"

    # --- mathB-u1: 数列 (85問) ---
    uid = "mathB-u1"
    # 1) 等差数列 (記述 10問 + 選択 6問 = 16問)
    arith_term_params = [
        (3, 4, 10, 1), (5, -2, 12, 1), (-7, 3, 15, 1), (2, 7, 20, 1), (10, -5, 9, 2),
    ]
    for a, d, n, diff in arith_term_params:
        ans = a + (n - 1) * d
        qb.add_write(sid, uid, diff, f"初項 {a}、公差 {d} の等差数列の第 {n} 項を求めよ。", str(ans),
                     f"一般項 a_n = {a} + (n - 1)({d})。n = {n} を代入すると {a} + {n-1}×({d}) = {ans}。")

    arith_sum_params = [
        (2, 3, 10, 1), (1, 2, 20, 1), (100, -4, 15, 2), (-5, 3, 12, 2), (4, 6, 11, 2),
    ]
    for a, d, n, diff in arith_sum_params:
        s_val = n * (2 * a + (n - 1) * d) // 2
        qb.add_write(sid, uid, diff, f"初項 {a}、公差 {d} の等差数列の初項から第 {n} 項までの和は？", str(s_val),
                     f"S_n = (1/2)×{n}×(2×{a} + {n-1}×({d})) = {s_val}。")

    qb.add_mc(sid, uid, 1, "第3項が 11、第7項が 23 である等差数列の公差は？", "3",
              ["4", "2", "6"], "a_7 - a_3 = 4d = 23 - 11 = 12 より d = 3。")
    qb.add_mc(sid, uid, 2, "3つの数 2, x, 14 がこの順に等差数列をなすとき、x の値は？", "8",
              ["6", "7", "10"], "等差中項より 2x = 2 + 14 = 16、よって x = 8。")
    qb.add_mc(sid, uid, 2, "初項 25、公差 -3 の等差数列において、初めて負になるのは第何項か？", "第10項",
              ["第9項", "第8項", "第11項"], "a_n = 28 - 3n < 0 ⇒ n > 28/3 = 9.33... よって第10項。")
    qb.add_mc(sid, uid, 3, "初項 31、公差 -4 の等差数列の初項から第 n 項までの和 S_n が最大になるのは n がいくつのときか？", "8",
              ["7", "9", "10"], "a_n = 35 - 4n > 0 となるのは n <= 8 まで（a_8=3, a_9=-1）。正の項まで足した n=8 で最大。")
    qb.add_mc(sid, uid, 2, "1 から 100 までの自然数のうち、3 の倍数の総和は？", "1683",
              ["1650", "1716", "1584"], "初項 3、末項 99、項数 33 の等差数列。S = 33×(3+99)/2 = 33×51 = 1683。")
    qb.add_mc(sid, uid, 3, "第5項が 14、第10項が 29 の等差数列において、初項から第10項までの和は？", "155",
              ["145", "160", "135"], "5d = 15 より d = 3、初項 a_1 = 14 - 4×3 = 2。S_10 = 10×(2 + 29)/2 = 155。")

    # 2) 等比数列 (記述 8問 + 選択 6問 = 14問)
    geom_term_params = [
        (3, 2, 6, 1), (2, 3, 5, 1), (5, -2, 5, 2), (64, Fraction(1, 2), 6, 2), (81, Fraction(-1, 3), 5, 2),
    ]
    for a, r, n, diff in geom_term_params:
        val = Fraction(a) * (Fraction(r) ** (n - 1))
        r_str = fmt_frac(r) if isinstance(r, Fraction) else str(r)
        qb.add_write(sid, uid, diff, f"初項 {a}、公比 {r_str} の等比数列の第 {n} 項を求めよ。", fmt_frac(val),
                     f"a_{n} = {a} × ({r_str})^{n-1} = {fmt_frac(val)}。")

    geom_sum_params = [
        (2, 2, 6, 1), (1, 3, 5, 2), (3, -2, 5, 2),
    ]
    for a, r, n, diff in geom_sum_params:
        s_val = a * (r ** n - 1) // (r - 1)
        qb.add_write(sid, uid, diff, f"初項 {a}、公比 {r} の等比数列の初項から第 {n} 項までの和は？", str(s_val),
                     f"S_{n} = {a}(({r})^{n} - 1) / ({r} - 1) = {s_val}。")

    qb.add_mc(sid, uid, 1, "初項 5、公比 1 の等比数列の初項から第 10 項までの和は？", "50",
              ["5", "10", "5^10"], "r = 1 のとき和の公式 1-r では分母が0になるため使えず、同じ値 5 を 10回足して 50。")
    qb.add_mc(sid, uid, 2, "3つの正の数 3, x, 27 がこの順に等比数列をなすとき、x の値は？", "9",
              ["15", "±9", "12"], "等比中項より x^2 = 3×27 = 81。x > 0 より x = 9。")
    qb.add_mc(sid, uid, 2, "第2項が 6、第5項が 48 である実数の等比数列の公比は？", "2",
              ["3", "4", "-2"], "r^3 = 48 / 6 = 8 より実数公比は r = 2。")
    qb.add_mc(sid, uid, 2, "初項 16、公比 1/2 の等比数列の初項から第 5 項までの和は？", "31",
              ["32", "63/2", "30"], "16(1 - (1/2)^5)/(1 - 1/2) = 32(31/32) = 31。")
    qb.add_mc(sid, uid, 3, "等比数列 2, -6, 18, -54, ... の初項から第 n 項までの和は？", "(1 - (-3)^n) / 2",
              ["(1 - 3^n) / 2", "(3^n - 1) / 2", "2(1 - (-3)^n)"],
              "初項 2、公比 -3 より 2(1 - (-3)^n)/(1 - (-3)) = (1 - (-3)^n)/2。")
    qb.add_mc(sid, uid, 3, "等比数列の和 S_n について、S_3 = 14、S_6 = 126 のとき、この等比数列の公比は？（公比は実数）", "2",
              ["3", "4", "-2"], "S_6 = S_3(1 + r^3) より 126 = 14(1 + r^3) ⇒ 1 + r^3 = 9 ⇒ r^3 = 8 ⇒ r = 2。")

    # 3) Σ計算・部分分数・等差×等比 (記述 10問 + 選択 6問 = 16問)
    sigma_writes = [
        (10, "k", sum(range(1, 11)), 1, "10×11/2 = 55"),
        (6, "k^2", sum(k * k for k in range(1, 7)), 1, "6×7×13/6 = 91"),
        (5, "k^3", sum(k ** 3 for k in range(1, 6)), 2, "(5×6/2)^2 = 15^2 = 225"),
        (8, "(2k - 1)", sum(2 * k - 1 for k in range(1, 9)), 1, "奇数の和 = 8^2 = 64"),
        (10, "(3k + 2)", sum(3 * k + 2 for k in range(1, 11)), 2, "3×55 + 2×10 = 185"),
        (6, "2^(k-1)", sum(2 ** (k - 1) for k in range(1, 7)), 2, "2^6 - 1 = 63"),
        (5, "(k^2 + k)", sum(k * k + k for k in range(1, 6)), 2, "55 + 15 = 70"),
    ]
    for N, body, ans, diff, exp_str in sigma_writes:
        qb.add_write(sid, uid, diff, f"和 Σ_(k=1)^{N} {body} の値を計算せよ。", str(ans),
                     f"Σ公式を適用すると {exp_str}。")

    # 部分分数分解など 記述3問
    qb.add_write(sid, uid, 2, "Σ_(k=1)^9 1 / (k(k + 1)) の値を既約分数で答えよ。", "9/10",
                 "1/(k(k+1)) = 1/k - 1/(k+1) として望遠鏡和をとると 1 - 1/10 = 9/10。")
    qb.add_write(sid, uid, 3, "Σ_(k=1)^15 1 / (√k + √(k + 1)) の値は？", "3",
                 "分母を有理化すると √(k+1) - √k。和は √16 - √1 = 4 - 1 = 3。")
    qb.add_write(sid, uid, 3, "和 S = Σ_(k=1)^5 k・2^k の値を求めよ。", "258",
                 "S - 2S を計算するか各項を足すと 1×2 + 2×4 + 3×8 + 4×16 + 5×32 = 2 + 8 + 24 + 64 + 160 = 258。")

    qb.add_mc(sid, uid, 1, "和 Σ_(k=1)^n c（c は k に関係ない定数）の値は？", "nc",
              ["c", "n(n+1)c/2", "c^n"], "定数 c を n 個足し合わせるため nc となる。")
    qb.add_mc(sid, uid, 2, "Σ_(k=1)^n k(k + 1) を n の式で表すと？", "n(n + 1)(n + 2)/3",
              ["n(n + 1)(2n + 1)/6", "n(n + 1)/2", "n(n - 1)(n + 1)/3"],
              "Σ(k^2 + k) = n(n+1)(2n+1)/6 + n(n+1)/2 = n(n+1)(n+2)/3。")
    qb.add_mc(sid, uid, 2, "Σ_(k=1)^n (3k^2 - 1) の計算において、結果の式として正しいのは？", "n(n + 1)(2n + 1)/2 - n",
              ["n(n + 1)(2n + 1)/2 - 1", "3n(n + 1)/2 - n", "n^3 - n"],
              "3 × n(n+1)(2n+1)/6 - n = n(n+1)(2n+1)/2 - n。")
    qb.add_mc(sid, uid, 3, "Σ_(k=1)^n 1 / (k(k + 2)) を計算すると？", "(3/4) - (2n + 3)/(2(n + 1)(n + 2))",
              ["1 - 1/(n + 2)", "1/2 - 1/(n + 2)", "3/2 - 1/(n + 1) - 1/(n + 2)"],
              "(1/2)(1/k - 1/(k+2)) の和は (1/2)(1 + 1/2 - 1/(n+1) - 1/(n+2)) = 3/4 - (2n+3)/(2(n+1)(n+2))。")
    qb.add_mc(sid, uid, 3, "和 S = 1 + 2x + 3x^2 + ... + nx^(n-1) (x ≠ 1) を求めるときに使う標準的な手法は？",
              "S - xS を計算して等比数列の和に帰着させる",
              ["部分分数分解を行う", "数学的帰納法だけで直接計算する", "対数をとる"],
              "(等差)×(等比)型の和は公比 x を掛けた式を引くことで等比数列の和に変換する。")
    qb.add_mc(sid, uid, 2, "Σ_(k=1)^n (2k + 1) の値と等しいものは？", "n^2 + 2n",
              ["n^2", "(n + 1)^2", "n^2 + n"], "n(n + 1) + n = n^2 + 2n。")

    # 4) 階差数列 (記述 6問 + 選択 4問 = 10問)
    # a_1 と階差 b_k を使って Python で a_n を生成
    diff_seq_cases = [
        ("b_k = 2k", 1, lambda k: 2 * k, 6, 1),
        ("b_k = 3k + 1", 2, lambda k: 3 * k + 1, 5, 2),
        ("b_k = 2^k", 1, lambda k: 2 ** k, 6, 2),
        ("b_k = k^2", 3, lambda k: k * k, 5, 2),
        ("b_k = 4k - 1", 5, lambda k: 4 * k - 1, 6, 2),
        ("b_k = 3^(k-1)", 2, lambda k: 3 ** (k - 1), 5, 3),
    ]
    for b_desc, a1, b_fn, target_n, diff in diff_seq_cases:
        val = a1 + sum(b_fn(k) for k in range(1, target_n))
        seq_preview = [a1]
        for k in range(1, 5):
            seq_preview.append(seq_preview[-1] + b_fn(k))
        seq_str = ", ".join(map(str, seq_preview))
        qb.add_write(sid, uid, diff, f"階差数列が {b_desc} である数列 {seq_str}, ... の第 {target_n} 項は？", str(val),
                     f"a_{target_n} = a_1 + Σ_(k=1)^{target_n - 1} b_k = {a1} + {val - a1} = {val}。")

    qb.add_mc(sid, uid, 1, "数列 {a_n} の階差数列 {b_n} を用いて a_n = a_1 + Σ_(k=1)^(n-1) b_k と表せるとき、この式がそのまま成り立つのは？",
              "n >= 2 のとき", ["n >= 1 のとき", "n >= 3 のとき", "n が偶数のときのみ"],
              "Σの上端が n - 1 >= 1 である必要があるため、まず n >= 2 で求め、n = 1 で一致するか別途確認する。")
    qb.add_mc(sid, uid, 2, "数列 2, 3, 5, 8, 12, 17, ... の一般項 a_n は？", "(n^2 - n + 4) / 2",
              ["(n^2 + n + 2) / 2", "n^2 - n + 2", "(n^2 - 3n + 6) / 2"],
              "階差数列は 1, 2, 3, 4, 5, ... (b_k = k)。a_n = 2 + (n-1)n/2 = (n^2 - n + 4)/2。")
    qb.add_mc(sid, uid, 2, "数列 1, 2, 5, 14, 41, ... の一般項 a_n は？", "(3^(n-1) + 1) / 2",
              ["3^(n-1)", "(3^n - 1) / 2", "2^(n-1) + 1"],
              "階差数列は 1, 3, 9, 27, ... (b_k = 3^(k-1))。a_n = 1 + (3^(n-1) - 1)/(3 - 1) = (3^(n-1) + 1)/2。")
    qb.add_mc(sid, uid, 3, "数列 1, 5, 12, 22, 35, ...（五角数）の第 10 項は？", "145",
              ["117", "176", "120"],
              "階差が 4, 7, 10, 13 (b_k = 3k + 1)。a_10 = 1 + Σ_(k=1)^9 (3k+1) = 1 + 3×45 + 9 = 145。")

    # 5) 和 S_n と一般項 a_n (記述 5問 + 選択 3問 + ○× 3問 = 11問)
    sn_cases = [
        ("n^2 + 2n", lambda n: n * n + 2 * n, 8, 1),
        ("2n^2 - n", lambda n: 2 * n * n - n, 7, 2),
        ("n^2 + 3n + 1", lambda n: n * n + 3 * n + 1, 1, 2),
        ("n^2 + 3n + 1", lambda n: n * n + 3 * n + 1, 5, 2),
        ("3^n - 1", lambda n: 3 ** n - 1, 4, 2),
    ]
    for s_desc, s_fn, target_n, diff in sn_cases:
        val = s_fn(1) if target_n == 1 else s_fn(target_n) - s_fn(target_n - 1)
        exp = f"a_1 = S_1 = {val}。" if target_n == 1 else f"a_{target_n} = S_{target_n} - S_{target_n-1} = {s_fn(target_n)} - {s_fn(target_n-1)} = {val}。"
        qb.add_write(sid, uid, diff, f"初項から第 n 項までの和 S_n が S_n = {s_desc} で表される数列の第 {target_n} 項は？", str(val), exp)

    qb.add_mc(sid, uid, 2, "S_n = n^2 + 2n + 3 のとき、この数列の一般項 a_n の表し方として正しいのは？",
              "a_1 = 6, a_n = 2n + 1 (n >= 2)",
              ["すべての n で a_n = 2n + 1", "すべての n で a_n = 2n + 3", "a_1 = 3, a_n = 2n + 1 (n >= 2)"],
              "n >= 2 で S_n - S_(n-1) = 2n + 1 だが、n=1 のとき S_1 = 6 ≠ 3 なので分けて書く必要がある。")
    qb.add_mc(sid, uid, 2, "S_n = 2^n - 1 で表される数列の一般項 a_n は？", "2^(n - 1)",
              ["2^n", "2^(n - 1) - 1", "2^n - 1"],
              "S_1 = 1。n >= 2 で (2^n - 1) - (2^(n-1) - 1) = 2^(n-1)。n=1 も 2^0 = 1 で一致する。")
    qb.add_mc(sid, uid, 3, "S_n = 2 a_n - 3 を満たす数列の初項 a_1 と公比 r は？", "a_1 = 3, r = 2",
              ["a_1 = 3, r = 1/2", "a_1 = -3, r = 2", "a_1 = 6, r = 2"],
              "n=1 で a_1 = 2a_1 - 3 ⇒ a_1 = 3。n>=2 で a_n = S_n - S_(n-1) = 2a_n - 2a_(n-1) ⇒ a_n = 2a_(n-1)。")

    qb.add_ox(sid, uid, 1, "どのような数列でも、初項は和 S_1 に等しい（a_1 = S_1）。", True, "第1項までの和は第1項そのものである。")
    qb.add_ox(sid, uid, 2, "S_n が n の2次式（定数項あり）S_n = an^2 + bn + c (c ≠ 0) で表されるとき、n=1 の項も n>=2 の一般項の式と一致する。", False,
              "定数項 c ≠ 0 があると S_1 = a+b+c となり、2n 系の一般項に n=1 を代入した値と c だけズレる。")
    qb.add_ox(sid, uid, 2, "数列 {a_n} のすべての項について a_n = S_n - S_(n-1) が成り立つ。", False,
              "S_0 が定義されないため、この式は n >= 2 の範囲でのみ成り立つ。")

    # 6) 漸化式 (記述 8問 + 選択 5問 = 13問)
    rec_cases = [
        ("a_1 = 2, a_(n+1) = a_n + 5", lambda a: a + 5, 2, 7, 1, "公差 5 の等差数列"),
        ("a_1 = 3, a_(n+1) = 2 a_n", lambda a: 2 * a, 3, 6, 1, "公比 2 の等比数列"),
        ("a_1 = 1, a_(n+1) = 2 a_n + 1", lambda a: 2 * a + 1, 1, 6, 2, "a_(n+1) + 1 = 2(a_n + 1) より a_n = 2^n - 1"),
        ("a_1 = 4, a_(n+1) = 3 a_n - 2", lambda a: 3 * a - 2, 4, 5, 2, "a_(n+1) - 1 = 3(a_n - 1) より a_n = 3^n + 1"),
        ("a_1 = 5, a_(n+1) = -2 a_n + 9", lambda a: -2 * a + 9, 5, 5, 3, "a_(n+1) - 3 = -2(a_n - 3) より a_n = 2(-2)^(n-1) + 3"),
        ("a_1 = 1, a_(n+1) = a_n + 3n", None, 1, 5, 2, "階差型 b_n = 3n"),
        ("a_1 = 1, a_2 = 1, a_(n+2) = a_(n+1) + a_n", None, 1, 8, 2, "フィボナッチ数列"),
        ("a_1 = 1, a_(n+1) = a_n / (2 a_n + 1)", None, 1, 5, 3, "逆数 b_n = 1/a_n とおくと b_(n+1) = b_n + 2"),
    ]
    for desc, fn, a1, target_n, diff, hint in rec_cases:
        if "3n" in desc:
            cur = a1
            for n_i in range(1, target_n):
                cur += 3 * n_i
            ans_str = str(cur)
        elif "フィボナッチ" in hint:
            seq = [1, 1]
            while len(seq) < target_n:
                seq.append(seq[-1] + seq[-2])
            ans_str = str(seq[target_n - 1])
        elif "逆数" in hint:
            cur_f = Fraction(1, 1)
            for _ in range(1, target_n):
                cur_f = cur_f / (2 * cur_f + 1)
            ans_str = fmt_frac(cur_f)
        else:
            cur = a1
            for _ in range(1, target_n):
                cur = fn(cur)
            ans_str = str(cur)
        qb.add_write(sid, uid, diff, f"漸化式 {desc} で定められる数列の第 {target_n} 項は？", ans_str,
                     f"{hint}。順次または一般項から計算すると第 {target_n} 項は {ans_str}。")

    qb.add_mc(sid, uid, 2, "漸化式 a_(n+1) = 4 a_n - 6 を解くときの特性方程式はどれか？", "α = 4α - 6",
              ["α^2 = 4α - 6", "α + 1 = 4α - 6", "4α + 6 = 0"],
              "a_(n+1) と a_n をともに α に置き換えた特性方程式 α = 4α - 6 より α = 2 を得る。")
    qb.add_mc(sid, uid, 2, "a_1 = 1, a_(n+1) = a_n + 2^n で定義される数列の一般項は？", "2^n - 1",
              ["2^(n-1)", "2^n + 1", "2^(n+1) - 3"],
              "階差数列が 2^n なので a_n = 1 + Σ_(k=1)^(n-1) 2^k = 1 + (2^n - 2) = 2^n - 1。")
    qb.add_mc(sid, uid, 3, "a_1 = 1, a_2 = 5, a_(n+2) - 5 a_(n+1) + 6 a_n = 0 の特性方程式の解は？", "x = 2, 3",
              ["x = -2, -3", "x = 1, 6", "x = -1, 6"], "x^2 - 5x + 6 = (x - 2)(x - 3) = 0 より x = 2, 3。")
    qb.add_mc(sid, uid, 3, "a_1 = 2, a_(n+1) = 3 a_n + 2^(n+1) を解くために両辺を何で割ると解きやすいか？", "2^(n + 1)（または 3^(n + 1)）",
              ["n + 1", "a_n", "2^n + 1"],
              "両辺を 2^(n+1) で割って b_n = a_n / 2^n とおくと b_(n+1) = (3/2)b_n + 1 の形に帰着できる。")
    qb.add_mc(sid, uid, 3, "a_1 = 2, a_(n+1) = 2 a_n^2 (a_n > 0) のような積・べき乗を含む漸化式を解く有効な変形は？",
              "両辺の対数（底2など）をとる",
              ["両辺の逆数をとる", "階差数列をとる", "平方完成する"],
              "log_2(a_(n+1)) = 2 log_2(a_n) + 1 となり、b_n = log_2(a_n) についての1次漸化式に変形できる。")

    # 7) 数学的帰納法・群数列・その他応用 (選択 2問 + ○× 3問 = 5問? 合計を数えよう!)
    # 今まで: 16 + 14 + 16 + 10 + 11 + 13 = 80問! あと5問でぴったり 85問！
    qb.add_mc(sid, uid, 2, "群数列 1 | 2, 3 | 4, 5, 6 | 7, 8, 9, 10 | ... で、第 10 群の最初の数は？", "46",
              ["45", "55", "37"], "第 9 群までに含まれる項数は 1+2+...+9 = 45個。よって第 10 群の最初は 46。")
    qb.add_mc(sid, uid, 2, "数学的帰納法で「すべての自然数 n について命題 P(n) が成り立つ」ことを示す2段階として正しいのは？",
              "(i) n=1 で成り立つことを示し、(ii) n=k での成立を仮定して n=k+1 での成立を示す",
              ["(i) n=1, 2, 3 で示し、(ii) n=k から n=k+2 を示す", "(i) n=k で成り立つと結論し、(ii) n=1 を示す", "(i) n=1 での成立を示し、(ii) n=k+1 から n=k を導く"],
              "ドミノ倒しのように、最初のドミノ(n=1)と、k番目が倒れれば k+1番目が倒れること(k→k+1)を示す。")

    qb.add_ox(sid, uid, 1, "数学的帰納法において、「n = k のとき成り立つと仮定する」部分は証明の結論ではなく途中の仮定として使ってよい。", True,
              "「P(k) が真ならば P(k+1) も真である」という条件文を示すため、P(k) を仮定して議論する。")
    qb.add_ox(sid, uid, 2, "「1以上のすべての自然数 n について成り立つ」ことを示す際、n=1 の確認を省略しても (k → k+1) だけで証明は完了する。", False,
              "たとえば「n = n + 1」のような偽の命題でも k→k+1 は成り立ってしまうため、起点 n=1 の確認が絶対必要。")
    qb.add_ox(sid, uid, 3, "「すべての自然数 n について a_(n+2) を決める命題」を帰納法で示す場合、n = 1 だけでなく n = 2 の確認と「n=k, k+1 の2つを仮定」が有効なことがある。", True,
              "隣接3項間漸化式などでは直前2項を使うため、n=1, 2 を示し k, k+1 から k+2 を示す方法が定石である。")

    # --- mathB-u2: 統計的な推測 (85問) ---
    uid = "mathB-u2"
    # 1) 確率分布・期待値・分散・標準偏差 (記述 12問 + 選択 6問 = 18問)
    dist_tables = [
        ([(0, Fraction(1, 4)), (2, Fraction(1, 2)), (4, Fraction(1, 4))], 1),
        ([(1, Fraction(1, 6)), (2, Fraction(1, 3)), (4, Fraction(1, 2))], 2),
        ([(0, Fraction(1, 2)), (3, Fraction(1, 3)), (6, Fraction(1, 6))], 2),
        ([(-2, Fraction(1, 4)), (0, Fraction(1, 2)), (2, Fraction(1, 4))], 2),
        ([(1, Fraction(1, 5)), (3, Fraction(2, 5)), (5, Fraction(2, 5))], 2),
        ([(2, Fraction(1, 2)), (4, Fraction(1, 4)), (8, Fraction(1, 4))], 2),
    ]
    for tbl, diff in dist_tables:
        ex = sum(x * p for x, p in tbl)
        ex2 = sum(x * x * p for x, p in tbl)
        vx = ex2 - ex * ex
        tbl_str = ", ".join(f"P(X={x})={fmt_frac(p)}" for x, p in tbl)
        qb.add_write(sid, uid, diff, f"確率変数 X の確率分布が {tbl_str} のとき、期待値 E(X) は？", fmt_frac(ex),
                     f"E(X) = Σ x_i p_i = {fmt_frac(ex)}。")
        qb.add_write(sid, uid, diff + (1 if diff == 1 else 0), f"確率変数 X の確率分布が {tbl_str} のとき、分散 V(X) は？", fmt_frac(vx),
                     f"E(X) = {fmt_frac(ex)}, E(X^2) = {fmt_frac(ex2)} より V(X) = E(X^2) - {{E(X)}}^2 = {fmt_frac(vx)}。")

    qb.add_mc(sid, uid, 1, "確率変数 X が値 1, 2, 3 をそれぞれ確率 p, 1/2, 1/3 でとるとき、定数 p の値は？", "1/6",
              ["1/3", "1/4", "2/3"], "確率の総和は 1 なので p + 1/2 + 1/3 = 1 ⇒ p = 1 - 5/6 = 1/6。")
    qb.add_mc(sid, uid, 2, "分散 V(X) = 9/4 のとき、標準偏差 σ(X) は？", "3/2",
              ["9/4", "81/16", "2/3"], "標準偏差は分散の正の平方根なので σ(X) = √(9/4) = 3/2。")
    qb.add_mc(sid, uid, 2, "1個のさいころを1回投げるとき、出る目 X の期待値 E(X) は？", "7/2",
              ["3", "4", "7"], "(1+2+3+4+5+6)/6 = 21/6 = 7/2。")
    qb.add_mc(sid, uid, 3, "1から4までの番号が書かれた4枚のカードから同時に2枚引くとき、大きい方の数 X の期待値 E(X) は？", "10/3",
              ["3", "7/2", "11/3"], "全6通りのうち X=2 が1通り, X=3 が2通り, X=4 が3通り。E(X) = (2×1 + 3×2 + 4×3)/6 = 20/6 = 10/3。")
    qb.add_mc(sid, uid, 2, "分散を求める公式 V(X) = E(X^2) - {E(X)}^2 において、E(X)=3, E(X^2)=13 のとき σ(X) は？", "2",
              ["4", "10", "√10"], "V(X) = 13 - 3^2 = 4 より σ(X) = √4 = 2。")
    qb.add_mc(sid, uid, 3, "赤玉3個、白玉2個から同時に2個取り出すとき、取り出す赤玉の個数 X の期待値 E(X) は？", "6/5",
              ["1", "3/2", "4/5"], "各回で赤が出る期待値 3/5 を2回分足しても同じ、E(X) = 2 × (3/5) = 6/5。")

    # 2) 確率変数の変換・和の期待値・独立 (記述 10問 + 選択 5問 + ○× 4問 = 19問? いや 15問にしてバランス調整しよう)
    # 計画見直し: 18 + 15 + 14 + 14 + 12 + 12 = 85問！なのでここは 15問にしよう (記述7 + 選択5 + ○×3 = 15)
    trans_writes = [
        ("E(X)=5 のとき、Y = 3X + 4 の期待値 E(Y)", "19", 1, "E(3X+4) = 3E(X) + 4 = 15 + 4 = 19。"),
        ("V(X)=4 のとき、Y = 2X - 5 の分散 V(Y)", "16", 1, "V(2X-5) = 2^2 V(X) = 4×4 = 16。"),
        ("σ(X)=6 のとき、Y = -3X + 10 の標準偏差 σ(Y)", "18", 2, "σ(-3X+10) = |-3| σ(X) = 3×6 = 18。"),
        ("E(X)=2, E(Y)=5 のとき、E(4X - 3Y + 1)", "-6", 2, "4E(X) - 3E(Y) + 1 = 8 - 15 + 1 = -6。"),
        ("X と Y が互いに独立で V(X)=3, V(Y)=4 のとき、V(X + Y)", "7", 2, "独立なので V(X+Y) = V(X) + V(Y) = 3 + 4 = 7。"),
        ("X と Y が互いに独立で V(X)=2, V(Y)=3 のとき、V(2X - 3Y)", "35", 3, "V(2X - 3Y) = 4V(X) + (-3)^2 V(Y) = 4×2 + 9×3 = 8 + 27 = 35。"),
        ("X と Y が互いに独立で E(X)=4, E(Y)=5 のとき、積 XY の期待値 E(XY)", "20", 2, "独立な2変数では E(XY) = E(X)E(Y) = 4×5 = 20。"),
    ]
    for prompt, ans, diff, exp in trans_writes:
        qb.add_write(sid, uid, diff, f"{prompt} の値は？", ans, exp)

    qb.add_mc(sid, uid, 2, "確率変数 X に対して標準化 Z = (X - E(X)) / σ(X) を行ったとき、(E(Z), V(Z)) はどうなるか？", "(0, 1)",
              ["(1, 0)", "(0, 0)", "(1, 1)"], "平均を引くと期待値が0、標準偏差で割ると分散・標準偏差が1になる。")
    qb.add_mc(sid, uid, 2, "2つの確率変数 X, Y の和の期待値 E(X + Y) = E(X) + E(Y) が成り立つ条件は？",
              "X と Y が独立であるかどうかに関わらず常に成り立つ",
              ["X と Y が互いに独立であるときのみ成り立つ", "X と Y の分散が等しいときのみ成り立つ", "正規分布に従うときのみ成り立つ"],
              "期待値の線形性 E(X+Y) = E(X)+E(Y) は独立性を仮定しなくても常に成立する。")
    qb.add_mc(sid, uid, 3, "独立な確率変数 X, Y について V(X - Y) に等しいのはどれか？", "V(X) + V(Y)",
              ["V(X) - V(Y)", "|V(X) - V(Y)|", "0"],
              "V(X + (-1)Y) = V(X) + (-1)^2 V(Y) = V(X) + V(Y)（差でも分散は足し算になる）。")
    qb.add_mc(sid, uid, 2, "E(X) = 10, V(X) = 4 のとき、E(X^2) の値は？", "104",
              ["96", "14", "116"], "V(X) = E(X^2) - {E(X)}^2 より E(X^2) = V(X) + {E(X)}^2 = 4 + 100 = 104。")
    qb.add_mc(sid, uid, 3, "硬貨を1枚ずつ投げて表を1点、裏を0点とする試行を独立に4回行う。合計点 S の分散 V(S) は？", "1",
              ["2", "1/2", "4"], "1回の分散は E(X^2) - E(X)^2 = 1/2 - 1/4 = 1/4。4回分の独立和より 4 × (1/4) = 1。")

    qb.add_ox(sid, uid, 1, "定数 c に対して、V(X + c) = V(X) が常に成り立つ。", True,
              "すべての値が c だけズレても散らばり具合（分散）は変わらない。")
    qb.add_ox(sid, uid, 2, "2つの確率変数 X, Y が独立でなくても、分散について V(X + Y) = V(X) + V(Y) が常に成り立つ。", False,
              "一般には V(X+Y) = V(X) + V(Y) + 2Cov(X, Y) であり、独立（または無相関）のときのみ和になる。")
    qb.add_ox(sid, uid, 2, "確率変数 X と Y が互いに独立ならば、E(XY) = E(X)E(Y) が成り立つ。", True,
              "独立な確率変数では同時確率が積 P(X=x, Y=y)=P(X=x)P(Y=y) になるため積の期待値も分解できる。")

    # 3) 二項分布 B(n, p) (記述 8問 + 選択 6問 = 14問)
    binom_dist_cases = [
        (100, Fraction(1, 5), "E(X)", 1),
        (100, Fraction(1, 5), "V(X)", 1),
        (400, Fraction(1, 5), "σ(X)", 2),
        (72, Fraction(1, 6), "E(X)", 1),
        (72, Fraction(1, 6), "V(X)", 2),
        (180, Fraction(1, 6), "σ(X)", 2),
        (60, Fraction(1, 3), "E(X)", 1),
        (90, Fraction(1, 3), "V(X)", 2),
    ]
    for n, p, metric, diff in binom_dist_cases:
        q_prob = 1 - p
        if metric == "E(X)":
            ans_f = n * p
            exp = f"二項分布 B(n, p) の期待値は np = {n} × {fmt_frac(p)} = {fmt_frac(ans_f)}。"
        elif metric == "V(X)":
            ans_f = n * p * q_prob
            exp = f"分散は np(1-p) = {n} × {fmt_frac(p)} × {fmt_frac(q_prob)} = {fmt_frac(ans_f)}。"
        else:
            vx = n * p * q_prob
            ans_f = Fraction(math.isqrt(vx.numerator), math.isqrt(vx.denominator))
            exp = f"分散は {fmt_frac(vx)} なので標準偏差 σ(X) = √({fmt_frac(vx)}) = {fmt_frac(ans_f)}。"
        qb.add_write(sid, uid, diff, f"確率変数 X が二項分布 B({n}, {fmt_frac(p)}) に従うとき、{metric} の値は？", fmt_frac(ans_f), exp)

    qb.add_mc(sid, uid, 1, "確率変数 X が二項分布 B(4, 1/2) に従うとき、P(X = 2) の値は？", "3/8",
              ["1/4", "1/2", "1/16"], "4C2 × (1/2)^2 × (1/2)^2 = 6 / 16 = 3/8。")
    qb.add_mc(sid, uid, 2, "確率変数 X が二項分布 B(n, p) に従うとき、期待値 E(X) と分散 V(X) の大小関係として常に成り立つのは？",
              "V(X) <= E(X)", ["V(X) >= E(X)", "V(X) = E(X)", "大小は常に n による"],
              "0 <= 1 - p <= 1 より V(X) = np(1 - p) <= np = E(X) が常に成り立つ。")
    qb.add_mc(sid, uid, 2, "二項分布 B(n, p) の標準偏差 σ(X) が最大になるのは、同じ n に対して p がいくつのときか？", "1/2",
              ["1", "0", "1/4"], "p(1 - p) = -(p - 1/2)^2 + 1/4 より p = 1/2 のとき最大になる。")
    qb.add_mc(sid, uid, 2, "1個のさいころを 180 回投げるとき、1の目が出る回数 X が従う分布はどれか？", "B(180, 1/6)",
              ["B(180, 5/6)", "B(6, 1/180)", "N(30, 1/6)"], "成功確率 1/6 の独立なベルヌーイ試行を 180回繰り返すため B(180, 1/6)。")
    qb.add_mc(sid, uid, 3, "期待値が 12、分散が 8 である二項分布 B(n, p) のパラメータ (n, p) は？", "(36, 1/3)",
              ["(24, 1/2)", "(18, 2/3)", "(48, 1/4)"], "np = 12, np(1-p) = 8 より 1 - p = 8/12 = 2/3 ⇒ p = 1/3、よって n = 36。")
    qb.add_mc(sid, uid, 3, "X ~ B(3, 1/3) のとき、P(X >= 1) の値は？", "19/27",
              ["8/27", "2/3", "26/27"], "余事象 P(X=0) = (2/3)^3 = 8/27 より 1 - 8/27 = 19/27。")

    # 4) 正規分布 N(m, σ^2) と標準化 (選択 6問 + 記述 4問 + ○× 4問 = 14問)
    qb.add_write(sid, uid, 1, "確率変数 X が正規分布 N(50, 10^2) に従うとき、X = 65 を標準化した値 Z = (X - m)/σ を小数で答えよ。", "1.5",
                 "Z = (65 - 50) / 10 = 15 / 10 = 1.5。", alt=["3/2"])
    qb.add_write(sid, uid, 2, "X が N(100, 15^2) に従い、標準正規分布で P(0 <= Z <= 1) = 0.3413 とする。P(85 <= X <= 115) を小数で答えよ。", "0.6826",
                 "85 と 115 はそれぞれ Z = -1 と Z = 1 に対応。対称性より 2 × 0.3413 = 0.6826。")
    qb.add_write(sid, uid, 2, "X が N(60, 8^2) に従い、P(0 <= Z <= 1.5) = 0.4332 とする。P(X >= 72) を小数で答えよ。", "0.0668",
                 "Z = (72 - 60)/8 = 1.5。P(Z >= 1.5) = 0.5 - P(0 <= Z <= 1.5) = 0.5 - 0.4332 = 0.0668。")
    qb.add_write(sid, uid, 3, "二項分布 B(400, 1/5) に従う X を正規分布で近似するとき、平均 m と標準偏差 σ の和 m + σ は？", "88",
                 "m = 400×(1/5) = 80, σ = √(400×(1/5)×(4/5)) = √64 = 8。よって m + σ = 88。")

    qb.add_mc(sid, uid, 1, "正規分布 N(m, σ^2) の確率密度曲線が最も高くなる（対称軸となる）x の値は？", "m",
              ["0", "σ", "σ^2"], "正規分布の確率密度関数は x = m に関して左右対称であり、x = m で最大値をとる。")
    qb.add_mc(sid, uid, 2, "標準正規分布 N(0, 1) に従う確率変数 Z について、P(-1.96 <= Z <= 1.96) の値に最も近いものは？", "0.95",
              ["0.68", "0.99", "0.90"], "z = 1.96 は両側 95% 点として知られ、P(|Z| <= 1.96) ≈ 0.9500。")
    qb.add_mc(sid, uid, 2, "テストの点数が N(55, 10^2) に従うとき、上位約 2.28% に入るための点数の目安は？（P(0 <= Z <= 2) = 0.4772）", "75点以上",
              ["65点以上", "85点以上", "70点以上"], "P(Z >= 2) = 0.5 - 0.4772 = 0.0228 (2.28%)。よって 55 + 2×10 = 75点以上。")
    qb.add_mc(sid, uid, 2, "ある工場の製品の重さが N(200, 5^2) に従うとき、重さが 195g 以上 210g 以下である確率は？（p(1)=0.3413, p(2)=0.4772）", "0.8185",
              ["0.1359", "0.6826", "0.9544"], "Z = -1 から Z = 2 までの確率なので 0.3413 + 0.4772 = 0.8185。")
    qb.add_mc(sid, uid, 3, "B(900, 1/10) に従う X を正規分布で近似し、P(X >= 108) を求めるのに使う標準化変数 Z の境界値は？（p(2)=0.4772）", "2",
              ["1.5", "3", "1.8"], "m = 90, σ = √(900×0.1×0.9) = √81 = 9。よって Z = (108 - 90)/9 = 2。")
    qb.add_mc(sid, uid, 3, "正規分布 N(m, σ^2) で標準偏差 σ が大きくなると、確率密度曲線はどのように変化するか？",
              "山が低く、横に広がる", ["山が高く、横に狭まる", "右方向に平行移動する", "非対称に歪む"],
              "σ が大きいほどデータのばらつきが大きくなるため、中心付近の高さが下がり裾野が広がる。")

    qb.add_ox(sid, uid, 1, "標準正規分布は、平均 0、分散 1 の正規分布 N(0, 1) である。", True, "標準正規分布の定義そのものである。")
    qb.add_ox(sid, uid, 1, "正規分布の確率密度曲線と x 軸の間の面積は、平均や標準偏差の値によらず常に 1 である。", True,
              "全事象の確率の総和は常に 1 になる。")
    qb.add_ox(sid, uid, 2, "連続型確率変数 X が正規分布に従うとき、ちょうど1点 P(X = m) の確率は 0.5 である。", False,
              "連続型確率変数では任意の1点での確率は常に 0 である（P(X >= m) = 0.5 とは区別する）。")
    qb.add_ox(sid, uid, 2, "二項分布 B(n, p) は、n が十分大きいとき正規分布 N(np, np(1-p)) で近似できる。", True,
              "ド・モアブル=ラプラスの定理により n が大きくなると正規分布に近づく。")

    # 5) 母集団と標本・大数の法則・中心極限定理 (記述 6問 + 選択 3問 + ○× 3問 = 12問)
    qb.add_write(sid, uid, 1, "母平均 60、母標準偏差 12 の母集団から大きさ 16 の無作為標本を抽出したとき、標本平均 X̄ の期待値は？", "60",
                 "標本平均の期待値 E(X̄) は母平均 m に等しいため 60。")
    qb.add_write(sid, uid, 1, "母平均 60、母標準偏差 12 の母集団から大きさ 16 の無作為標本を抽出したとき、標本平均 X̄ の標準偏差は？", "3",
                 "σ(X̄) = σ / √n = 12 / √16 = 12 / 4 = 3。")
    qb.add_write(sid, uid, 2, "母分散 100 の母集団から大きさ 25 の標本を抽出するとき、標本平均 X̄ の分散 V(X̄) は？", "4",
                 "V(X̄) = σ^2 / n = 100 / 25 = 4。")
    qb.add_write(sid, uid, 2, "母比率 p = 0.2 の母集団から大きさ n = 100 の標本を抽出するとき、標本比率 R の標準偏差を小数で答えよ。", "0.04",
                 "σ(R) = √(p(1-p)/n) = √(0.2×0.8/100) = √0.0016 = 0.04。")
    qb.add_write(sid, uid, 3, "標本平均の標準偏差を元の半分 (1/2倍) にするためには、標本の大きさ n を何倍にする必要があるか？", "4",
                 "σ / √n を 1/2 にするには √n を 2倍、すなわち n を 2^2 = 4倍にする必要がある。", alt=["4倍"])
    qb.add_write(sid, uid, 2, "1, 3, 5, 7 の4枚のカードが入った母集団の母平均は？", "4",
                 "(1 + 3 + 5 + 7) / 4 = 16 / 4 = 4。")

    qb.add_mc(sid, uid, 1, "製品を壊して寿命を測る検査や、全国の有権者の意識を調べる場合に必ず用いられる調査方法は？", "標本調査",
              ["全数調査", "悉皆調査", "二重盲検法"],
              "破壊検査や対象が膨大な場合はすべてを調べられないため標本調査を行う。")
    qb.add_mc(sid, uid, 2, "標本の大きさ n を大きくすると、標本平均 X̄ が母平均 m の近くからほとんど外れなくなる性質を何というか？", "大数の法則",
              ["中心極限定理", "無作為抽出", "最尤法"],
              "n → ∞ で標本平均が母平均に近づく法則を大数の法則という。")
    qb.add_mc(sid, uid, 3, "母集団の分布が正規分布でなくても、標本の大きさ n が大きいとき標本平均 X̄ の分布が近似的に正規分布に従うという定理は？", "中心極限定理",
              ["大数の法則", "チェビシェフの不等式", "ベイズの定理"],
              "中心極限定理により、どのような母分布でも n が大きければ標本平均は N(m, σ^2/n) に近づく。")

    qb.add_ox(sid, uid, 1, "無作為抽出とは、母集団のどの要素も同じ確率で選ばれるように標本を抜き出す方法である。", True,
              "偏り（バイアス）をなくすため乱数表やくじなどを用いて公平に抽出する。")
    qb.add_ox(sid, uid, 2, "標本平均 X̄ の期待値は、標本の大きさ n が大きくなるにつれて母平均 m に近づく（n が小さいときは m と異なる）。", False,
              "E(X̄) = m は標本の大きさ n に関わらず常に厳密に一致する（不偏性）。n で小さくなるのは標準偏差である。")
    qb.add_ox(sid, uid, 2, "同じ母集団から復元抽出を行っても非復元抽出を行っても、標本平均 X̄ の期待値は常に母平均 m に等しい。", True,
              "復元・非復元のどちらでも E(X̄) = m が成り立つ。")

    # 6) 推定（信頼区間）と仮説検定 (記述 4問 + 選択 5問 + ○× 3問 = 12問 -> 18+15+14+14+12+12 = 85問!)
    qb.add_write(sid, uid, 2, "母標準偏差 σ = 10 の母集団から大きさ n = 25 の標本を抽出し、標本平均 x̄ = 72 を得た。母平均の 95% 信頼区間の上限を小数で答えよ（z = 1.96）。", "75.92",
                 "72 + 1.96 × (10 / √25) = 72 + 1.96 × 2 = 72 + 3.92 = 75.92。")
    qb.add_write(sid, uid, 2, "上の設定（σ=10, n=25, x̄=72, z=1.96）において、95% 信頼区間の「幅（上限 - 下限）」を小数で答えよ。", "7.84",
                 "幅は 2 × 1.96 × (10 / 5) = 2 × 3.92 = 7.84。")
    qb.add_write(sid, uid, 3, "母標準偏差 σ = 5 のとき、母平均の 95% 信頼区間の幅を 1.96 以下にするために必要な最小の標本サイズ n は？", "100",
                 "2 × 1.96 × (5 / √n) <= 1.96 より 10 / √n <= 1、すなわち √n >= 10 ⇒ n >= 100。")
    qb.add_write(sid, uid, 2, "n = 400 の標本で標本比率 r = 0.5 を得た。母比率 p の 95% 信頼区間 r ± 1.96√(r(1-r)/n) の誤差（±の後の値）を小数で答えよ。", "0.049",
                 "1.96 × √(0.5×0.5 / 400) = 1.96 × (0.5 / 20) = 1.96 × 0.025 = 0.049。")

    qb.add_mc(sid, uid, 2, "母平均 m の信頼区間について、信頼度を 95% から 99% に引き上げたとき、同じ標本に対して信頼区間の幅はどうなるか？",
              "広くなる", ["狭くなる", "変わらない", "半分になる"],
              "信頼度を上げるには z 値を 1.96 から 2.58 に増やす必要があるため、区間幅は広くなる。")
    qb.add_mc(sid, uid, 2, "仮説検定において、「差がない」「効果がない」「コインは歪んでいない」などの最初に立てる仮説を何というか？", "帰無仮説",
              ["対立仮説", "有意水準", "棄却域"],
              "検証によって否定（棄却）することを目指す基準の仮説を帰無仮説 H_0 という。")
    qb.add_mc(sid, uid, 2, "コインを 100回投げて表が 60回以上出たため「このコインは表が出やすい」と片側検定（有意水準 5%）で判定したい。m=50, σ=5 で Z=(60-50)/5 = 2.0 となった。P(Z>=1.645)=0.05 のとき結論は？",
              "帰無仮説を棄却し、表が出やすいと判断できる",
              ["帰無仮説は棄却できず、表が出やすいとは言えない", "標本が不足しているため検定不能", "コインは確実に公正であると証明された"],
              "Z = 2.0 > 1.645 であり棄却域に入るため、有意水準 5% で帰無仮説「p = 1/2」は棄却される。")
    qb.add_mc(sid, uid, 3, "仮説検定における「第1種の過誤（αエラー）」とはどのような誤りか？",
              "帰無仮説が本当は正しいのに、誤って棄却してしまう誤り",
              ["帰無仮説が本当は誤っているのに、棄却しない誤り", "標本サイズ n を数え間違える誤り", "標準偏差ではなく分散を使う誤り"],
              "正しい帰無仮説を誤って棄却する確率の上限が有意水準 α に対応する。")
    qb.add_mc(sid, uid, 3, "両側検定において有意水準を 5% (0.05) に設定した場合、標準正規分布の棄却域の境界となる z の絶対値は？", "1.96",
              ["1.645", "2.58", "2.33"], "両側合計で 0.05 なので片側 0.025 となる z = 1.96 が境界になる。")

    qb.add_ox(sid, uid, 2, "「母平均 m の 95% 信頼区間が [68.1, 75.9] である」とは、「真の母平均 m が 68.1 と 75.9 の間に存在する確率が 95% である」という意味である。", False,
              "真の母平均 m は定数であり確率変数ではない。正しくは「同じ方法で信頼区間を作る試行を繰り返すと 95% の割合でその区間が母平均を含む」という意味である。")
    qb.add_ox(sid, uid, 2, "仮説検定で帰無仮説が棄却されなかった場合、「帰無仮説が正しいことが証明された」と結論づけてよい。", False,
              "「棄却するだけの十分な証拠が得られなかった」という意味であり、帰無仮説が真であると積極的に証明されたわけではない。")
    qb.add_ox(sid, uid, 2, "有意水準を 5% から 1% に厳しくすると、帰無仮説は棄却されにくくなる。", True,
              "棄却域が狭くなるため、より極端な結果が出ないと帰無仮説を棄却できなくなる。")


# ============================================================
# 5. 数学C (mathC): 2単元 × 85問 = 170問
# ============================================================

def generate_mathC(qb: QuestionBank) -> None:
    sid = "mathC"

    # --- mathC-u1: ベクトル (85問) ---
    uid = "mathC-u1"
    # 1) 平面ベクトルの基本演算・大きさ・平行・1次結合 (記述 12問 + 選択 6問 + ○× 3問 = 21問)
    vec_lin_params = [
        ((2, 3), (-1, 4), 2, 3, 1),
        ((3, -1), (2, 5), 1, -2, 1),
        ((-2, 5), (4, -3), 3, 2, 1),
        ((1, -4), (-3, 2), 4, -1, 2),
        ((5, 2), (-1, -3), 2, 5, 2),
    ]
    for (x1, y1), (x2, y2), k1, k2, diff in vec_lin_params:
        rx, ry = k1 * x1 + k2 * x2, k1 * y1 + k2 * y2
        expr = fmt_poly_terms([(k1, "a"), (k2, "b")])
        q = f"ベクトル a = ({x1}, {y1}), b = ({x2}, {y2}) のとき、{expr} を成分で表せ。"
        exp = f"成分ごとに計算すると ({k1}×({x1}) + ({k2})×({x2}), {k1}×({y1}) + ({k2})×({y2})) = ({rx}, {ry})。"
        qb.add_write(sid, uid, diff, q, fmt_vec(rx, ry), exp)

    mag_params = [(3, -4, 1), (-5, 12, 1), (8, -15, 2), (-6, 8, 1)]
    for x, y, diff in mag_params:
        m = math.isqrt(x * x + y * y)
        qb.add_write(sid, uid, diff, f"ベクトル a = ({x}, {y}) の大きさ |a| を求めよ。", str(m),
                     f"|a| = √(({x})^2 + ({y})^2) = √{x*x + y*y} = {m}。")

    # 平行条件 (記述 3問)
    par_cases = [(2, -3, 6, 1), (3, 4, -9, 2), (-4, 5, 8, 2)]
    for x1, y1, x2, diff in par_cases:
        y2 = (y1 * x2) // x1
        qb.add_write(sid, uid, diff, f"2つのベクトル a = ({x1}, {y1}) と b = ({x2}, k) が平行になるとき、実数 k の値は？", str(y2),
                     f"平行条件 x1 y2 - x2 y1 = 0 より {x1}k - ({x2})×({y1}) = 0 ⇒ k = {y2}。")

    qb.add_mc(sid, uid, 1, "ベクトル a = (3, 4) と同じ向きの単位ベクトル e は？", "(3/5, 4/5)",
              ["(3, 4)", "(-3/5, -4/5)", "(4/5, 3/5)"],
              "|a| = √(9+16) = 5。同じ向きの単位ベクトルは a / |a| = (3/5, 4/5)。")
    qb.add_mc(sid, uid, 2, "a = (1, 2), b = (3, -1), c = (7, 0) について c = s a + t b と表すとき、(s, t) は？", "(1, 2)",
              ["(2, 1)", "(-1, 2)", "(2, -1)"],
              "s + 3t = 7 かつ 2s - t = 0 より t = 2s ⇒ 7s = 7 ⇒ s = 1, t = 2。")
    qb.add_mc(sid, uid, 2, "2点 A(2, -1), B(5, 3) に対して、有向線分が表すベクトル AB の成分と大きさ |AB| の組は？", "(3, 4), 5",
              ["(-3, -4), 5", "(7, 2), √53", "(3, 4), 25"],
              "AB = OB - OA = (5-2, 3-(-1)) = (3, 4)、大きさは √(3^2+4^2) = 5。")
    qb.add_mc(sid, uid, 2, "正六角形 ABCDEF において AB = a, AF = b とするとき、対角線 AD を a, b で表すと？", "2a + 2b",
              ["a + b", "2a + b", "a + 2b"],
              "中心を O とすると AO = AB + AF = a + b。よって AD = 2 AO = 2a + 2b。")
    qb.add_mc(sid, uid, 3, "a = (2, 1), b = (-1, 3) のとき、a + t b がベクトル c = (1, 1) と平行になる t の値は？", "1/4",
              ["-1/4", "1/2", "4"],
              "a + tb = (2-t, 1+3t) が (1, 1) と平行 ⇒ 2 - t = 1 + 3t ⇒ 4t = 1 ⇒ t = 1/4。")
    qb.add_mc(sid, uid, 1, "点 A, B, C に対してベクトル AB + BC + CA は何になるか？", "0（零ベクトル）",
              ["2 AB", "AC", "2 CA"], "始点と終点が一致して戻るため和は零ベクトル 0 になる。")

    qb.add_ox(sid, uid, 1, "零ベクトル 0 の大きさは 0 であり、向きは考えない。", True,
              "大きさが 0 で向きは定まらない（任意とみなす）のが零ベクトルである。")
    qb.add_ox(sid, uid, 2, "2つの零でないベクトル a, b が平行であるとは、ある実数 k に対して b = k a と表せることをいう。", True,
              "k > 0 なら同じ向き、k < 0 なら逆向きに平行であることを表す。")
    qb.add_ox(sid, uid, 2, "単位ベクトルとは、すべての成分が 1 であるベクトルのことを指す。", False,
              "単位ベクトルとは「大きさ（長さ）が 1 であるベクトル」のことであり、例えば (1, 1) の大きさは √2 で単位ベクトルではない。")

    # 2) 内積・なす角・垂直条件・面積 (記述 12問 + 選択 7問 + ○× 3問 = 22問)
    dot_params = [
        ((2, 3), (4, -1), 1), ((5, -2), (3, 4), 1), ((-3, 4), (-2, -5), 2),
        ((6, 1), (-1, 6), 1), ((4, -3), (2, 7), 2),
    ]
    for (x1, y1), (x2, y2), diff in dot_params:
        d_val = x1 * x2 + y1 * y2
        qb.add_write(sid, uid, diff, f"ベクトル a = ({x1}, {y1}), b = ({x2}, {y2}) の内積 a・b を求めよ。", str(d_val),
                     f"a・b = ({x1})×({x2}) + ({y1})×({y2}) = {d_val}。")

    perp_params = [(3, 4, 8, 1), (2, -5, 10, 2), (-4, 3, 6, 2)]
    for x1, y1, x2, diff in perp_params:
        y2 = -(x1 * x2) // y1
        qb.add_write(sid, uid, diff, f"2つのベクトル a = ({x1}, {y1}) と b = ({x2}, k) が垂直であるとき、k の値は？", str(y2),
                     f"垂直条件 a・b = 0 より {x1}×({x2}) + ({y1})k = 0 ⇒ k = {y2}。")

    # 大きさとなす角からの内積・面積 (記述 4問)
    qb.add_write(sid, uid, 1, "|a| = 4, |b| = 3 で、a と b のなす角が 60° のとき、内積 a・b の値は？", "6",
                 "a・b = |a||b|cos60° = 4 × 3 × (1/2) = 6。")
    qb.add_write(sid, uid, 2, "|a| = 5, |b| = 4 で、a と b のなす角が 120° のとき、内積 a・b の値は？", "-10",
                 "a・b = 5 × 4 × cos120° = 20 × (-1/2) = -10。")
    qb.add_write(sid, uid, 2, "|a| = 3, |b| = 4, a・b = 2 のとき、|a + b|^2 の値は？", "29",
                 "|a + b|^2 = |a|^2 + 2(a・b) + |b|^2 = 9 + 4 + 16 = 29。")
    qb.add_write(sid, uid, 3, "OA = (3, 1), OB = (1, 5) のとき、△OAB の面積 S は？", "7",
                 "成分による面積公式 S = (1/2)|x1 y2 - x2 y1| = (1/2)|3×5 - 1×1| = 14/2 = 7。")

    qb.add_mc(sid, uid, 2, "ベクトル a = (1, √3) と b = (√3, 1) のなす角 θ (0° <= θ <= 180°) は？", "30°",
              ["45°", "60°", "90°"],
              "|a|=2, |b|=2, a・b = 2√3 より cosθ = (2√3)/(2×2) = √3/2。よって θ = 30°。")
    qb.add_mc(sid, uid, 2, "|a| = 2, |b| = 3, |a - b| = √7 のとき、a と b のなす角は？", "60°",
              ["30°", "120°", "90°"],
              "7 = |a|^2 - 2a・b + |b|^2 = 4 - 2a・b + 9 ⇒ a・b = 3。cosθ = 3/(2×3) = 1/2 ⇒ θ = 60°。")
    qb.add_mc(sid, uid, 2, "a = (1, 2), b = (2, -1) のとき、|a + t b| が最小になる実数 t の値とその最小値の組は？",
              "t = 0, 最小値 √5",
              ["t = 1, 最小値 √10", "t = -1, 最小値 2", "t = 1/2, 最小値 2"],
              "a・b = 2 - 2 = 0 (直交) なので |a+tb|^2 = |a|^2 + t^2|b|^2 = 5 + 5t^2。t=0 で最小値 √5。")
    qb.add_mc(sid, uid, 3, "|a| = 2, |b| = 1, a・b = -1 のとき、|a + t b| の最小値は？", "√3",
              ["1", "√5", "2"],
              "|a+tb|^2 = 4 - 2t + t^2 = (t - 1)^2 + 3。t = 1 で最小値 √3。")
    qb.add_mc(sid, uid, 2, "ベクトル a = (2, -3) に垂直な単位ベクトルの1つは？", "(3/√13, 2/√13)",
              ["(2/√13, -3/√13)", "(3/√13, -2/√13)", "(3, 2)"],
              "(3, 2) との内積は 2×3 + (-3)×2 = 0。大きさ √13 で割って (3/√13, 2/√13)。")
    qb.add_mc(sid, uid, 3, "△ABC で AB=c, AC=b, 内積 AB・AC = d とするとき、面積 S の公式として正しいのは？",
              "(1/2) √(|AB|^2 |AC|^2 - (AB・AC)^2)",
              ["(1/2) √(|AB|^2 |AC|^2 + (AB・AC)^2)", "(1/2) (AB・AC)", "√(|AB|^2 |AC|^2 - (AB・AC)^2)"],
              "S = (1/2)|AB||AC|sinθ と sin^2θ = 1 - cos^2θ から導かれる重要な公式。")
    qb.add_mc(sid, uid, 3, "a + b + c = 0 かつ |a|=3, |b|=4, |c|=5 のとき、内積 a・b の値は？", "0",
              ["12", "-12", "25"],
              "c = -(a + b) より |c|^2 = |a|^2 + 2a・b + |b|^2 ⇒ 25 = 9 + 2a・b + 16 ⇒ a・b = 0（直角三角形）。")

    qb.add_ox(sid, uid, 1, "2つの零でないベクトル a, b の内積 a・b は、ベクトルではなくスカラー（実数）である。", True,
              "内積はスカラー積とも呼ばれ、実数値を返す演算である。")
    qb.add_ox(sid, uid, 2, "3つのベクトル a, b, c について (a・b)c = a(b・c) の結合法則が常に成り立つ。", False,
              "(a・b)c は c の定数倍、a(b・c) は a の定数倍なので一般には向きが異なり成り立たない。")
    qb.add_ox(sid, uid, 2, "任意の2つのベクトル a, b について |a・b| <= |a||b|（コーシー・シュワルツの不等式）が成り立つ。", True,
              "|cosθ| <= 1 より |a・b| = |a||b||cosθ| <= |a||b|。")

    # 3) 位置ベクトル・共線・ベクトル方程式 (記述 9問 + 選択 7問 + ○× 3問 = 19問)
    qb.add_write(sid, uid, 1, "2点 A(a), B(b) を結ぶ線分 AB を 2 : 3 に内分する点 P の位置ベクトル p を (ma + nb)/5 と表すとき、m の値は？", "3",
                 "クロスに掛けて p = (3a + 2b)/(2+3) なので a の係数 m = 3。")
    qb.add_write(sid, uid, 2, "3点 A(1, 2), B(3, 6), C(5, k) が一直線上にあるとき、k の値は？", "10",
                 "AB = (2, 4), AC = (4, k - 2)。AC = 2 AB より k - 2 = 8 ⇒ k = 10。")
    qb.add_write(sid, uid, 2, "△OAB において辺 OA を 2:1 に内分する点を C、辺 OB の中点を D とし、AD と BC の交点を P とする。OP = s OA + t OB と表すとき、s + t を既約分数で答えよ。", "3/4",
                 "OP = s a + t b で C(2/3 a) より OP = (3/2)s OC + t b ⇒ (3/2)s + t = 1。また D(1/2 b) より s + 2t = 1。解くと s=1/2, t=1/4 ⇒ s+t = 3/4。")
    qb.add_write(sid, uid, 2, "点 (2, 3) を通り、方向ベクトル d = (4, -1) に平行な直線上の点 P(x, y) を x + ky = m で表すとき、k の値は？", "4",
                 "x = 2 + 4t, y = 3 - t から t = 3 - y を代入すると x = 2 + 4(3 - y) ⇒ x + 4y = 14。よって k = 4。")
    qb.add_write(sid, uid, 2, "点 (1, -2) を通り、法線ベクトル n = (3, 4) に垂直な直線の方程式 3x + 4y + c = 0 における c の値は？", "5",
                 "n・(p - a) = 0 より 3(x - 1) + 4(y + 2) = 0 ⇒ 3x + 4y + 5 = 0。よって c = 5。")
    qb.add_write(sid, uid, 3, "点 A(1, 1), B(5, 3) に対して、ベクトル方程式 AP・BP = 0 を満たす点 P が描く円の中心の x 座標は？", "3",
                 "AP・BP = 0 は線分 AB を直径とする円。中心は中点 ((1+5)/2, (1+3)/2) = (3, 2) なので x 座標は 3。")
    qb.add_write(sid, uid, 3, "△ABC において 2 PA + 3 PB + PC = 0 を満たす点 P があるとき、△PBC と △ABC の面積比は 1 : m である。m の値は？", "3",
                 "P を位置ベクトルで整理すると AP = (3 AB + AC)/6 = (4/6)((3AB+AC)/4)。辺BCを1:3に内分する点Dに対し AP:PD=4:2=2:1 ⇒ △PBC = (1/3)△ABC。あるいは係数和 2+3+1=6 より P の対辺 A 側比率は 2/6 = 1/3 なので m = 3。")
    qb.add_write(sid, uid, 2, "△OAB で OP = s OA + t OB が s + t = 1, s >= 0, t >= 0 を満たしながら動くとき、点 P の存在範囲は何になるか？（線分/直線/三角形で言えば）", "線分AB",
                 "s + t = 1 かつ s >= 0, t >= 0 は、2点 A, B を結ぶ線分 AB 上全体を表す。", alt=["線分 AB"])
    qb.add_write(sid, uid, 3, "△OAB で OP = s OA + t OB が s + 2t = 1, s >= 0, t >= 0 を満たすとき、点 P は点 A とどの点を結ぶ線分上を動くか？（OBの中点をMとする）", "M",
                 "s + 2t = 1 ⇒ s OA + (2t)((1/2)OB) = s OA + (2t) OM。s + 2t = 1 より線分 AM。点 A と結ぶ点は M。", alt=["点M", "OBの中点", "辺OBの中点"])

    qb.add_mc(sid, uid, 2, "△OAB において点 P が OP = s OA + t OB (0 <= s+t <= 1, s >= 0, t >= 0) を満たすとき、点 P の存在範囲は？",
              "△OAB の周および内部",
              ["線分 AB 上", "△OAB の外部", "O を中心とする平行四辺形全体"],
              "s+t=k (0<=k<=1) とおくと線分 AB を O 中心に k 倍縮小した線分を掃くため、△OAB の周と内部になる。")
    qb.add_mc(sid, uid, 2, "中心 c の位置ベクトル、半径 r の円のベクトル方程式はどれか？", "|p - c| = r",
              ["p・c = r", "|p + c| = r", "(p - c)・c = 0"],
              "中心 C から点 P までの距離 CP = |p - c| が一定値 r に等しいという式。")
    qb.add_mc(sid, uid, 2, "異なる2点 A(a), B(b) を通る直線のベクトル方程式として正しいのは？（t は実数）", "p = (1 - t)a + t b",
              ["p = t a + t b", "p = (1 + t)a + t b", "(p - a)・(p - b) = 0"],
              "p = a + t(b - a) = (1 - t)a + t b と整理できる。")
    qb.add_mc(sid, uid, 3, "直線 2x - 5y + 3 = 0 の法線ベクトルの1つとして正しいのは？", "(2, -5)",
              ["(5, 2)", "(-2, -5)", "(2, 5)"],
              "直線 ax + by + c = 0 において、x, y の係数を並べた (a, b) = (2, -5) が法線ベクトルである。")
    qb.add_mc(sid, uid, 3, "ベクトル方程式 |p - a| = |p - b| を満たす点 P(p) 全体が描く図形は？", "線分 AB の垂直二等分線",
              ["線分 AB を直径とする円", "直線 AB", "点 A, B の中点のみ"],
              "PA = PB を満たす点の集合は、線分 AB の垂直二等分線になる。")
    qb.add_mc(sid, uid, 2, "3点 A(a), B(b), C(c) が一直線上にあるための共線条件（A≠B）は？",
              "AC = k AB を満たす実数 k が存在する",
              ["AB・AC = 0 が成り立つ", "a + b + c = 0 が成り立つ", "|AB| = |AC| が成り立つ"],
              "A を始点とする2つのベクトルが平行であることが共線条件である。")
    qb.add_mc(sid, uid, 3, "c・(p - a) = 0 (c ≠ 0) で表される図形はどのような図形か？",
              "点 A を通り、ベクトル c に垂直な直線",
              ["点 A を通り、ベクトル c に平行な直線", "点 A を中心とし半径 |c| の円", "原点を通る直線"],
              "AP と c の内積が 0 すなわち AP ⊥ c なので、A を通り c に垂直な直線を表す。")

    qb.add_ox(sid, uid, 1, "点 P の位置ベクトルが p = (a + b + c)/3 で与えられるとき、P は △ABC の重心である。", True,
              "三角形の重心の位置ベクトルは3頂点の位置ベクトルの平均である。")
    qb.add_ox(sid, uid, 2, "平面上の直線 ax + by + c = 0 において、方向ベクトルの1つは (a, b) である。", False,
              "(a, b) は法線ベクトル。方向ベクトルは (-b, a) や (b, -a) である。")
    qb.add_ox(sid, uid, 2, "中心 C(c)、半径 r の円の接点 P_0(p_0) における接線のベクトル方程式は (p_0 - c)・(p - c) = r^2 である。", True,
              "CP_0 ⊥ P_0P より (p_0 - c)・(p - p_0) = 0 を変形すると (p_0 - c)・(p - c) = |p_0 - c|^2 = r^2。")

    # 4) 空間ベクトル・球面・平面 (記述 12問 + 選択 8問 + ○× 3問 = 23問 -> 21+22+19+23 = 85問!)
    qb.add_write(sid, uid, 1, "空間の2点 A(1, 2, -1), B(3, 0, 1) の間の距離は？", "2√3",
                 "√((3-1)^2 + (0-2)^2 + (1-(-1))^2) = √(4 + 4 + 4) = √12 = 2√3。", alt=["2sqrt(3)"])
    qb.add_write(sid, uid, 1, "空間ベクトル a = (1, 2, 2), b = (3, -1, 4) の内積 a・b は？", "9",
                 "1×3 + 2×(-1) + 2×4 = 3 - 2 + 8 = 9。")
    qb.add_write(sid, uid, 1, "空間ベクトル a = (2, -3, 6) の大きさ |a| は？", "7",
                 "√(2^2 + (-3)^2 + 6^2) = √(4 + 9 + 36) = √49 = 7。")
    qb.add_write(sid, uid, 2, "空間の2つのベクトル a = (1, 2, -3) と b = (4, k, 2) が直交するとき、k の値は？", "1",
                 "a・b = 4 + 2k - 6 = 2k - 2 = 0 より k = 1。")
    qb.add_write(sid, uid, 2, "点 P(3, -4, 5) と xy 平面に関して対称な点 Q(x, y, z) の z 座標は？", "-5",
                 "xy 平面対称では z 座標の符号のみ反転し (3, -4, -5) となるため -5。")
    qb.add_write(sid, uid, 2, "4点 A(1, 0, 0), B(0, 2, 0), C(0, 0, 3), D(0, 0, 0) を頂点とする四面体の体積は？", "1",
                 "底面積 (1/2)×1×2 = 1、高さ 3 の三角錐なので V = (1/3)×1×3 = 1。")
    qb.add_write(sid, uid, 2, "中心 (2, -1, 3)、半径 5 の球面の方程式 (x-2)^2 + (y+1)^2 + (z-3)^2 = R における R の値は？", "25",
                 "右辺は半径の2乗 r^2 = 5^2 = 25。")
    qb.add_write(sid, uid, 2, "球面 x^2 + y^2 + z^2 - 4x + 2y - 6z - 2 = 0 の半径は？", "4",
                 "平方完成すると (x-2)^2 + (y+1)^2 + (z-3)^2 = 4 + 1 + 9 + 2 = 16。よって半径は √16 = 4。")
    qb.add_write(sid, uid, 3, "点 A(3, 4, 12) を中心とし、原点 O を通る球面の半径は？", "13",
                 "中心 A と原点 O の距離が半径なので √(3^2 + 4^2 + 12^2) = √(9+16+144) = √169 = 13。")
    qb.add_write(sid, uid, 3, "3点 A(1, 0, 0), B(0, 1, 0), C(0, 0, 1) を通る平面 x + y + z = 1 と原点 O(0, 0, 0) の距離は？", "√3/3",
                 "法線ベクトル n = (1, 1, 1)。点と平面の距離は |0+0+0-1| / √(1+1+1) = 1/√3 = √3/3。", alt=["1/√3", "sqrt(3)/3"])
    qb.add_write(sid, uid, 2, "3点 A(1, 2, 3), B(2, 1, 0), C(0, 4, 2) を頂点とする △ABC の重心 G の3座標の和 (x + y + z) は？", "5",
                 "重心 G の座標の和は3点の座標総和の 1/3 に等しいため (1+2+3 + 2+1+0 + 0+4+2) / 3 = 15 / 3 = 5。")
    qb.add_write(sid, uid, 3, "平面 2x + y - 2z - 6 = 0 上に点 H があり OH が平面に垂直であるとき、線分 OH の長さは？", "2",
                 "原点から平面への距離は |-6| / √(2^2 + 1^2 + (-2)^2) = 6 / √9 = 2。")

    qb.add_mc(sid, uid, 1, "点 P(2, -3, 4) と y 軸に関して対称な点 Q の座標は？", "(-2, -3, -4)",
              ["(-2, 3, -4)", "(2, 3, 4)", "(-2, -3, 4)"],
              "y 軸対称では y 座標だけがそのままで、x 座標と z 座標の符号が反転する。")
    qb.add_mc(sid, uid, 2, "中心 (3, -4, 5) の球面が xy 平面に接するとき、この球面の半径は？", "5",
              ["3", "4", "√50"],
              "xy 平面 (z = 0) までの距離は |z 座標| = 5 なので、接するための半径は 5。")
    qb.add_mc(sid, uid, 2, "空間において、1次独立な2つのベクトル a, b と同じ平面上にある点 P の位置条件（共面条件）は？",
              "OP = s a + t b となる実数 s, t が存在する",
              ["OP・(a + b) = 0 となる", "OP = s a となる実数 s が存在する", "|OP| = |a| + |b| となる"],
              "4点 O, A, B, P が同一平面上にあることは、OP が OA と OB の1次結合で表せることと同値である。")
    qb.add_mc(sid, uid, 3, "4点 O(0,0,0), A(1,2,0), B(2,1,1), C(3,3,t) が同一平面上にあるとき、t の値は？", "1",
              ["2", "0", "-1"],
              "OC = s OA + u OB より 3 = s+2u, 3 = 2s+u ⇒ s=1, u=1。z成分より t = 0×1 + 1×1 = 1。")
    qb.add_mc(sid, uid, 2, "空間ベクトル a = (1, 1, 0), b = (0, 1, 1) のなす角 θ は？", "60°",
              ["30°", "45°", "90°"],
              "|a| = √2, |b| = √2, a・b = 1。cosθ = 1 / (√2×√2) = 1/2 より θ = 60°。")
    qb.add_mc(sid, uid, 3, "点 A(1, 0, 2) を通り、ベクトル n = (2, -1, 3) を法線ベクトルとする平面の方程式は？",
              "2x - y + 3z - 8 = 0",
              ["2x - y + 3z + 8 = 0", "x + 2z - 7 = 0", "2x - y + 3z - 7 = 0"],
              "2(x - 1) - 1(y - 0) + 3(z - 2) = 0 より 2x - y + 3z - 8 = 0。")
    qb.add_mc(sid, uid, 3, "空間内の異なる3点を通る平面に点 P から垂線 PH を下ろすとき、点 H を定める連立条件は？",
              "PH ⊥ AB かつ PH ⊥ AC（かつ H は平面 ABC 上）",
              ["PH // AB かつ PH // AC", "PH・AB = 1 かつ PH・AC = 1", "PA = PB = PC"],
              "平面上の1次独立な2本のベクトル AB, AC の両方に垂直であることが平面に垂直であることの条件。")
    qb.add_mc(sid, uid, 2, "球面 x^2 + y^2 + z^2 = 25 と平面 z = 3 が交わってできる円の半径は？", "4",
              ["5", "3", "√34"], "z = 3 を代入すると x^2 + y^2 = 25 - 9 = 16 となるため、断面の円の半径は 4。")

    qb.add_ox(sid, uid, 1, "空間の点 P(a, b, c) から zx 平面に下ろした垂線の足の座標は (a, 0, c) である。", True,
              "zx 平面は y = 0 なので、y 座標のみを 0 にした点が垂線の足になる。")
    qb.add_ox(sid, uid, 2, "空間において、1つの直線に垂直な2つの直線は必ず互いに平行である。", False,
              "空間ではねじれの位置にある直交直線（例: x軸とy軸はともにz軸に垂直だが平行でない）が存在するため偽。")
    qb.add_ox(sid, uid, 2, "空間の2つのベクトル a = (x1, y1, z1) と b = (x2, y2, z2) が両方とも零でないとき、a・b = 0 ⇔ a ⊥ b である。", True,
              "平面の場合と同様に、内積が 0 であることが垂直であるための必要十分条件になる。")

    # --- mathC-u2: 平面上の曲線と複素数平面 (85問) ---
    uid = "mathC-u2"
    # 1) 放物線 (記述 6問 + 選択 6問 + ○× 2問 = 14問)
    parab_writes = [
        ("y^2 = 12x", "焦点の x 座標", "3", 1, "4p = 12 より p = 3。焦点は (3, 0) なので x 座標は 3。"),
        ("y^2 = 8x", "準線の方程式 x = k の k の値", "-2", 1, "4p = 8 より p = 2。準線は x = -p = -2。"),
        ("x^2 = 16y", "焦点の y 座標", "4", 1, "4p = 16 より p = 4。焦点は (0, 4) なので y 座標は 4。"),
        ("y^2 = -20x", "焦点の x 座標", "-5", 2, "4p = -20 より p = -5。焦点は (-5, 0)。"),
        ("(y - 2)^2 = 8(x - 1)", "焦点の x 座標", "3", 2, "y^2=8x (焦点 (2,0)) を x軸に1、y軸に2移動すると焦点は (3, 2)。"),
        ("y^2 = 4x", "点 (1, 2) における接線の傾き", "1", 3, "接線は y0 y = 2p(x + x0) ⇒ 2y = 2(x + 1) ⇒ y = x + 1。傾きは 1。"),
    ]
    for eq, ask, ans, diff, exp in parab_writes:
        qb.add_write(sid, uid, diff, f"放物線 {eq} について、{ask}は？", ans, exp)

    qb.add_mc(sid, uid, 1, "焦点 F(2, 0)、準線 x = -2 である放物線の方程式は？", "y^2 = 8x",
              ["y^2 = 4x", "x^2 = 8y", "y^2 = 2x"], "y^2 = 4px に p = 2 を代入して y^2 = 8x。")
    qb.add_mc(sid, uid, 2, "放物線とは、定点 F と F を通らない定直線 l からのどのような点の軌跡か？",
              "F からの距離と l からの距離が等しい点の軌跡",
              ["F からの距離の和が一定な点の軌跡", "F からの距離が常に 1 の点の軌跡", "l からの距離が F からの距離の2倍の点の軌跡"],
              "離心率 e = 1 に相当し、PF = PH（Hは準線への垂線の足）が放物線の定義。")
    qb.add_mc(sid, uid, 2, "放物線 x^2 = -12y の準線の方程式は？", "y = 3",
              ["y = -3", "x = 3", "x = -3"], "4p = -12 ⇒ p = -3。準線は y = -p = 3。")
    qb.add_mc(sid, uid, 2, "放物線 y^2 = 12x 上の点 P(3, 6) と焦点 F(3, 0) の間の距離 PF は？", "6",
              ["3", "3√5", "12"], "定義より PF は準線 x = -3 との距離に等しいため 3 - (-3) = 6。")
    qb.add_mc(sid, uid, 3, "放物線 y^2 = 8x 上の点 (2, 4) における接線の方程式は？", "x - y + 2 = 0",
              ["x + y - 6 = 0", "2x - y = 0", "4y = 4x + 8"], "公式 y0 y = 2p(x + x0) より 4y = 4(x + 2) ⇒ y = x + 2 ⇒ x - y + 2 = 0。")
    qb.add_mc(sid, uid, 3, "放物線 y^2 = 4px (p > 0) 上の任意の点から引いた光線が、焦点を通る軸に平行に入射して反射するとどう進むか？",
              "すべて焦点 (p, 0) を通るように反射する",
              ["すべて原点 (0, 0) に向かう", "準線に平行に反射する", "入射方向そのまま通過する"],
              "パラボラアンテナが電波を焦点に集める原理（放物線の光学的性質）である。")

    qb.add_ox(sid, uid, 1, "放物線 y^2 = 4x のグラフは x 軸に関して対称である。", True,
              "y を -y に置き換えても式が変わらないため x 軸対称である。")
    qb.add_ox(sid, uid, 2, "放物線 y^2 = 4px において、p の値が大きいほど放物線の開き方は狭くなる（尖る）。", False,
              "x = y^2 / (4p) より p が大きいほど同じ y に対する x が小さくなり、開き方は広く（緩やかに）なる。")

    # 2) 楕円 (記述 7問 + 選択 7問 + ○× 2問 = 16問)
    ell_writes = [
        ("x^2/25 + y^2/9 = 1", "長軸の長さ", "10", 1, "a^2 = 25 より a = 5。長軸の長さは 2a = 10。"),
        ("x^2/25 + y^2/9 = 1", "短軸の長さ", "6", 1, "b^2 = 9 より b = 3。短軸の長さは 2b = 6。"),
        ("x^2/25 + y^2/9 = 1", "正の側の焦点の x 座標", "4", 1, "c = √(25 - 9) = √16 = 4。"),
        ("x^2/169 + y^2/144 = 1", "2つの焦点間の距離", "10", 2, "c = √(169 - 144) = 5。焦点は (±5, 0) なので距離は 2c = 10。"),
        ("x^2/9 + y^2/25 = 1", "正の側の焦点の y 座標", "4", 2, "b > a なので焦点は y 軸上にあり、c = √(25 - 9) = 4。"),
        ("x^2/36 + y^2/20 = 1", "楕円上の任意の点 P から2つの焦点までの距離の和", "12", 2, "2焦点からの距離の和は長軸の長さ 2a = 2×6 = 12 に等しい。"),
        ("x^2/9 + y^2/4 = 1", "囲まれる面積を π を用いて表したもの（例: 2π）", "6π", 3, "楕円 x^2/a^2 + y^2/b^2 = 1 の面積は πab = π×3×2 = 6π。"),
    ]
    for eq, ask, ans, diff, exp in ell_writes:
        alt_l = [ans.replace("π", "pi")] if "π" in ans else None
        qb.add_write(sid, uid, diff, f"楕円 {eq} について、{ask}は？", ans, exp, alt=alt_l)

    qb.add_mc(sid, uid, 1, "2つの焦点 (-3, 0), (3, 0) からの距離の和が 10 である楕円の方程式は？", "x^2/25 + y^2/16 = 1",
              ["x^2/25 + y^2/9 = 1", "x^2/100 + y^2/91 = 1", "x^2/16 + y^2/25 = 1"],
              "2a = 10 ⇒ a = 5。c = 3 より b^2 = a^2 - c^2 = 25 - 9 = 16。よって x^2/25 + y^2/16 = 1。")
    qb.add_mc(sid, uid, 2, "円 x^2 + y^2 = 16 を y 軸方向に 1/2 倍に縮小して得られる楕円の方程式は？", "x^2/16 + y^2/4 = 1",
              ["x^2/4 + y^2/16 = 1", "x^2/16 + y^2/8 = 1", "x^2/64 + y^2/16 = 1"],
              "変換前の点を (X, Y)、変換後を (x, y) とおくと X=x, Y=2y。x^2 + (2y)^2 = 16 ⇒ x^2/16 + y^2/4 = 1。")
    qb.add_mc(sid, uid, 2, "楕円 (x - 2)^2 / 9 + (y + 1)^2 / 4 = 1 の中心の座標は？", "(2, -1)",
              ["(-2, 1)", "(3, 2)", "(2, 1)"], "x^2/9 + y^2/4 = 1 を (2, -1) だけ平行移動した楕円なので中心は (2, -1)。")
    qb.add_mc(sid, uid, 2, "楕円 x^2/16 + y^2/9 = 1 上の点 (2, 3√3/2) における接線の方程式は？", "x/8 + (√3/6)y = 1",
              ["x/4 + y/3 = 1", "2x + 3y = 1", "x/16 + y/9 = 1"],
              "接線公式 x0 x / a^2 + y0 y / b^2 = 1 に代入すると 2x/16 + (3√3/2)y/9 = 1 ⇒ x/8 + (√3/6)y = 1。")
    qb.add_mc(sid, uid, 3, "楕円 x^2/a^2 + y^2/b^2 = 1 (a > b > 0) の離心率 e = c / a のとり得る範囲は？", "0 < e < 1",
              ["e = 1", "e > 1", "-1 < e < 1"], "0 < c = √(a^2-b^2) < a なので、楕円の離心率は 0 < e < 1 となる（円は e = 0）。")
    qb.add_mc(sid, uid, 3, "長軸が y 軸上にあり、2焦点 (0, ±4)、短軸の長さが 6 である楕円の方程式は？", "x^2/9 + y^2/25 = 1",
              ["x^2/25 + y^2/9 = 1", "x^2/36 + y^2/16 = 1", "x^2/9 + y^2/16 = 1"],
              "a = 3, c = 4 より b^2 = a^2 + c^2 = 9 + 16 = 25。よって x^2/9 + y^2/25 = 1。")
    qb.add_mc(sid, uid, 2, "楕円 4x^2 + 9y^2 = 36 の長軸の長さと短軸の長さの和は？", "10",
              ["5", "13", "6"], "両辺を 36 で割ると x^2/9 + y^2/4 = 1。a=3, b=2 より 2a + 2b = 6 + 4 = 10。")

    qb.add_ox(sid, uid, 1, "楕円上の任意の点から2つの焦点までの距離の和は常に一定で、長軸の長さに等しい。", True,
              "楕円の幾何学的定義そのものである。")
    qb.add_ox(sid, uid, 2, "楕円 x^2/9 + y^2/25 = 1 の焦点は x 軸上にある。", False,
              "25 > 9 より y 軸方向に長いため、焦点は y 軸上の (0, ±4) にある。")

    # 3) 双曲線 (記述 6問 + 選択 7問 + ○× 2問 = 15問)
    hyp_writes = [
        ("x^2/9 - y^2/16 = 1", "正の側の焦点の x 座標", "5", 1, "c = √(9 + 16) = √25 = 5。"),
        ("x^2/25 - y^2/144 = 1", "正の側の焦点の x 座標", "13", 2, "c = √(25 + 144) = √169 = 13。"),
        ("x^2/16 - y^2/9 = 1", "2つの頂点間の距離", "8", 1, "頂点は (±4, 0) なので距離は 2a = 8。"),
        ("x^2/4 - y^2/9 = 1", "漸近線 y = ±(m/n)x の正の傾き（既約分数）", "3/2", 2, "y/3 = ±x/2 より傾きは ±b/a = ±3/2。"),
        ("x^2/9 - y^2/7 = 1", "双曲線上の点 P から2焦点までの距離の差の絶対値", "6", 2, "|PF - PF'| = 2a = 2×3 = 6。"),
        ("x^2/9 - y^2/16 = -1", "正の側の焦点の y 座標", "5", 2, "右辺が -1 のとき焦点は y 軸上にあり、c = √(9 + 16) = 5。"),
    ]
    for eq, ask, ans, diff, exp in hyp_writes:
        qb.add_write(sid, uid, diff, f"双曲線 {eq} について、{ask}は？", ans, exp)

    qb.add_mc(sid, uid, 1, "2つの焦点 (-5, 0), (5, 0) からの距離の差が 6 である双曲線の方程式は？", "x^2/9 - y^2/16 = 1",
              ["x^2/16 - y^2/9 = 1", "x^2/9 + y^2/16 = 1", "x^2/36 - y^2/25 = 1"],
              "2a = 6 ⇒ a = 3。c = 5 より b^2 = c^2 - a^2 = 25 - 9 = 16。")
    qb.add_mc(sid, uid, 2, "双曲線 x^2/4 - y^2/25 = 1 の漸近線の方程式は？", "y = ±(5/2)x",
              ["y = ±(2/5)x", "y = ±(25/4)x", "y = ±(4/25)x"], "x/2 ± y/5 = 0 より y = ±(5/2)x。")
    qb.add_mc(sid, uid, 2, "双曲線 x^2 - y^2 = 4 のように2本の漸近線が直交する双曲線を何と呼ぶか？", "直角双曲線",
              ["正双曲線", "共役双曲線", "対称双曲線"], "漸近線 y = ±x が直交するため直角双曲線と呼ぶ（反比例 y = k/x も45°回転したもの）。")
    qb.add_mc(sid, uid, 3, "漸近線が y = ±2x で、頂点が (±3, 0) である双曲線の方程式は？", "x^2/9 - y^2/36 = 1",
              ["x^2/36 - y^2/9 = 1", "x^2/9 - y^2/4 = 1", "x^2/9 - y^2/36 = -1"],
              "a = 3、漸近線の傾き b/a = 2 より b = 6。よって x^2/9 - y^2/36 = 1。")
    qb.add_mc(sid, uid, 3, "双曲線 x^2/9 - y^2/16 = 1 上の点 P(5, 16/3) における接線の方程式は？", "5x/9 - y/3 = 1",
              ["5x/9 + y/3 = 1", "3x - 4y = 1", "5x/16 - y/9 = 1"],
              "接線公式 x0 x / a^2 - y0 y / b^2 = 1 より 5x/9 - (16/3)y/16 = 1 ⇒ 5x/9 - y/3 = 1。")
    qb.add_mc(sid, uid, 2, "反比例のグラフ y = 2 / x は、どのような2次曲線か？", "双曲線（直角双曲線）",
              ["放物線", "楕円", "カージオイド"], "xy = 2 は双曲線 x^2 - y^2 = 4 を原点周りに 45° 回転した直角双曲線である。")
    qb.add_mc(sid, uid, 3, "双曲線 x^2/a^2 - y^2/b^2 = 1 の離心率 e = c / a のとり得る値の範囲は？", "e > 1",
              ["0 < e < 1", "e = 1", "0 < e <= 1"], "c = √(a^2 + b^2) > a なので離心率 e = c/a > 1 となる。")

    qb.add_ox(sid, uid, 1, "双曲線は2つの漸近線に限りなく近づくが、漸近線と交わることはない。", True,
              "x^2/a^2 - y^2/b^2 = 1 と y = ±(b/a)x を連立すると 0 = 1 となり共有点をもたない。")
    qb.add_ox(sid, uid, 2, "双曲線 x^2/4 - y^2/9 = -1 の頂点は (±2, 0) である。", False,
              "右辺が -1 なので y 軸との交点 (0, ±3) が頂点になる。")

    # 4) 媒介変数表示・極座標・極方程式 (記述 6問 + 選択 6問 + ○× 2問 = 14問)
    qb.add_write(sid, uid, 1, "極座標 (4, π/3) で表される点の直交座標 (x, y) のうち、x 座標の値は？", "2",
                 "x = r cosθ = 4 cos(π/3) = 4 × (1/2) = 2。")
    qb.add_write(sid, uid, 1, "直交座標 (-3, 3) の点を極座標 (r, θ) (r > 0, 0 <= θ < 2π) で表すとき、r の値を √ を用いて表せ。", "3√2",
                 "r = √((-3)^2 + 3^2) = √18 = 3√2。", alt=["3sqrt(2)"])
    qb.add_write(sid, uid, 2, "媒介変数表示 x = 2t + 1, y = 4t - 3 から t を消去した直線の方程式 2x - y = c の c の値は？", "5",
                 "2x - y = 2(2t+1) - (4t-3) = 4t + 2 - 4t + 3 = 5。")
    qb.add_write(sid, uid, 2, "媒介変数表示 x = 3 cosθ, y = 3 sinθ が表す円の面積を π を用いて表せ。", "9π",
                 "x^2 + y^2 = 9 なので半径 3 の円。面積は 9π。", alt=["9pi"])
    qb.add_write(sid, uid, 3, "極方程式 r = 6 cosθ を直交座標の方程式に直したとき、円の半径は？", "3",
                 "両辺に r を掛けると r^2 = 6 r cosθ ⇒ x^2 + y^2 = 6x ⇒ (x-3)^2 + y^2 = 9。半径は 3。")
    qb.add_write(sid, uid, 3, "極方程式 r cosθ = 4 を直交座標 (x, y) の方程式で表せ。", "x = 4",
                 "x = r cosθ なのでそのまま x = 4。")

    qb.add_mc(sid, uid, 1, "直交座標 (1, √3) の点を極座標 (r, θ) (r > 0, 0 <= θ < 2π) で表すと？", "(2, π/3)",
              ["(2, π/6)", "(√2, π/3)", "(2, 2π/3)"], "r = √(1+3) = 2, cosθ = 1/2, sinθ = √3/2 より θ = π/3。")
    qb.add_mc(sid, uid, 2, "媒介変数表示 x = 4 cosθ, y = 3 sinθ (0 <= θ < 2π) が表す曲線はどれか？", "楕円 x^2/16 + y^2/9 = 1",
              ["円 x^2 + y^2 = 7", "双曲線 x^2/16 - y^2/9 = 1", "楕円 x^2/9 + y^2/16 = 1"],
              "(x/4)^2 + (y/3)^2 = cos^2θ + sin^2θ = 1 より楕円 x^2/16 + y^2/9 = 1。")
    qb.add_mc(sid, uid, 2, "極方程式 r = 5 が表す曲線は何か？", "極を中心とする半径 5 の円",
              ["x = 5 の直線", "点 (5, 0) を通る半直線", "原点を通る直線"],
              "r = √(x^2 + y^2) = 5 より x^2 + y^2 = 25（中心が極、半径 5 の円）。")
    qb.add_mc(sid, uid, 2, "極方程式 θ = π/4（r は全実数）が表す図形は？", "極を通り始線との角が π/4 の直線 y = x",
              ["半径 π/4 の円", "原点から第1象限に伸びる半直線のみ", "直線 y = -x"],
              "r が負の値も許される場合、反対側の第3象限も含めた直線全体を表す。")
    qb.add_mc(sid, uid, 3, "半径 a の円が x 軸上を滑らずに回転するとき、円周上の1点が描く曲線「サイクロイド」の媒介変数表示は？",
              "x = a(θ - sinθ), y = a(1 - cosθ)",
              ["x = a(θ + sinθ), y = a(1 + cosθ)", "x = a cos^3θ, y = a sin^3θ", "x = a(1 - cosθ), y = a(θ - sinθ)"],
              "原点から回転角 θ だけ回ったときの円の中心は (aθ, a) であり、点の相対位置 (-a sinθ, -a cosθ) を加えて得る。")
    qb.add_mc(sid, uid, 3, "2次曲線の極方程式 r = l / (1 + e cosθ) において、e = 1/2 のときこの曲線は何を表すか？", "楕円",
              ["放物線", "双曲線", "直線"], "離心率 e について 0 < e < 1 なら楕円、e = 1 なら放物線、e > 1 なら双曲線。")

    qb.add_ox(sid, uid, 1, "極座標における極 O の表現では、r = 0 ならば偏角 θ はどんな値でもよい。", True,
              "極 (原点) の距離 r = 0 なので θ は任意に定めることができる。")
    qb.add_ox(sid, uid, 2, "媒介変数表示 x = t^2, y = 2t (t は全実数) は、y 軸を軸とする放物線 y = x^2 を表す。", False,
              "t = y/2 を x = t^2 に代入すると x = y^2 / 4、すなわち y^2 = 4x であり、x 軸を軸とする放物線である。")

    # 5) 複素数平面の基本・極形式・ド・モアブル・図形 (記述 10問 + 選択 12問 + ○× 4問 = 26問 -> 14+16+15+14+26 = 85問!)
    qb.add_write(sid, uid, 1, "複素数 z = 3 - 4i の絶対値 |z| は？", "5",
                 "|3 - 4i| = √(3^2 + (-4)^2) = √(9 + 16) = 5。")
    qb.add_write(sid, uid, 1, "2点 α = 1 + 2i, β = 4 - 2i の間の距離 |β - α| は？", "5",
                 "β - α = 3 - 4i なので距離は |3 - 4i| = √(9 + 16) = 5。")
    qb.add_write(sid, uid, 2, "複素数 z = 1 + i を極形式 r(cosθ + i sinθ) (0 <= θ < 2π) で表すとき、偏角 θ を π を用いて答えよ。", "π/4",
                 "r = √2, cosθ = 1/√2, sinθ = 1/√2 より θ = π/4。", alt=["pi/4"])
    qb.add_write(sid, uid, 2, "複素数 z = -1 + √3i を極形式 r(cosθ + i sinθ) (0 <= θ < 2π) で表すとき、r の値は？", "2",
                 "r = |z| = √((-1)^2 + (√3)^2) = √(1 + 3) = 2。")
    qb.add_write(sid, uid, 2, "複素数 z = cos(π/6) + i sin(π/6) について、ド・モアブルの定理により z^6 の値を計算せよ。", "-1",
                 "z^6 = cos(6×π/6) + i sin(6×π/6) = cosπ + i sinπ = -1。")
    qb.add_write(sid, uid, 3, "(1 + i)^8 を計算して最も簡単な数値（実数または a+bi）で表せ。", "16",
                 "1 + i = √2(cos(π/4) + i sin(π/4))。8乗すると (√2)^8 (cos2π + i sin2π) = 16×1 = 16。")
    qb.add_write(sid, uid, 3, "(1 - √3 i)^3 を計算せよ。", "-8",
                 "1 - √3 i = 2(cos(-π/3) + i sin(-π/3))。3乗すると 2^3 (cos(-π) + i sin(-π)) = 8(-1) = -8。")
    qb.add_write(sid, uid, 2, "点 z = 2 + 3i を原点の周りに反時計回りに π/2 だけ回転した点を表す複素数は？", "-3 + 2i",
                 "π/2 の回転は i を掛けることに対応するため、i(2 + 3i) = 2i + 3i^2 = -3 + 2i。")
    qb.add_write(sid, uid, 2, "方程式 |z - (2 + 3i)| = 4 を満たす点 z が複素数平面上に描く円の半径は？", "4",
                 "中心 2 + 3i、半径 4 の円を表すため半径は 4。")
    qb.add_write(sid, uid, 3, "複素数平面上で点 z = 3 + 4i と共役な点 z̄ の中点が表す実数は？", "3",
                 "(z + z̄)/2 = ((3+4i) + (3-4i))/2 = 3。")

    qb.add_mc(sid, uid, 1, "複素数平面上で点 z = 2 - 5i と実軸に関して対称な点は？", "2 + 5i",
              ["-2 + 5i", "-2 - 5i", "5 - 2i"], "実軸対称は虚部の符号反転すなわち共役複素数 z̄ = 2 + 5i。")
    qb.add_mc(sid, uid, 1, "複素数平面上で点 z = 3 + 2i と虚軸に関して対称な点は？", "-3 + 2i",
              ["3 - 2i", "-3 - 2i", "2 + 3i"], "虚軸対称では実部の符号のみが反転し -z̄ = -3 + 2i になる。")
    qb.add_mc(sid, uid, 2, "z_1 = 2(cos(π/3) + i sin(π/3)), z_2 = 3(cos(π/6) + i sin(π/6)) の積 z_1 z_2 は？",
              "6i", ["6", "-6i", "5i"],
              "絶対値は積 2×3=6、偏角は和 π/3 + π/6 = π/2。6(cos(π/2) + i sin(π/2)) = 6i。")
    qb.add_mc(sid, uid, 2, "z_1 / z_2 の幾何的な意味として、点 z_1 は点 z_2 を原点周りにどうしたものに対応するか？（arg(z_1) と arg(z_2)）",
              "原点の周りに -arg(z_2) だけ回転し、大きさを 1/|z_2| 倍する",
              ["原点の周りに arg(z_2) だけ回転し、|z_2| 倍する", "z_2 だけ平行移動する", "実軸で対称移動する"],
              "商の絶対値は |z_1|/|z_2|、偏角は arg(z_1) - arg(z_2) となる。")
    qb.add_mc(sid, uid, 2, "0 でない複素数 z が「純虚数」であるための条件（z̄ を共役とする）は？",
              "z + z̄ = 0 かつ z ≠ 0", ["z - z̄ = 0", "z z̄ = 1", "z = z̄"],
              "z = x + yi のとき z + z̄ = 2x = 0 より実部 x = 0（z ≠ 0 より y ≠ 0）。")
    qb.add_mc(sid, uid, 3, "方程式 z^4 = 1 の 4つの解を複素数平面上にプロットするとどのような図形をなすか？",
              "原点を中心とする単位円に内接する正方形",
              ["実軸上の4点", "正三角形と原点", "半径4の円上のひし形"],
              "解は 1, i, -1, -i であり、偏角 0, π/2, π, 3π/2 の位置にあるため単位円に内接する正方形。")
    qb.add_mc(sid, uid, 3, "方程式 |z - 1| = |z - i| を満たす点 z の集合は、複素数平面上でどのような図形か？",
              "直線 y = x（2点 1 と i を結ぶ線分の垂直二等分線）",
              ["直線 y = -x", "中心 1 + i の円", "実軸"],
              "点 (1, 0) と点 (0, 1) から等距離にある点の軌跡なので垂直二等分線 y = x になる。")
    qb.add_mc(sid, uid, 3, "異なる3点 α, β, γ について、線分 AB と AC が垂直（∠BAC = 90°）であるための条件は？",
              "(γ - α) / (β - α) が純虚数",
              ["(γ - α) / (β - α) が実数", "γ - α = β - α", "(γ - α)(β - α) = 1"],
              "arg((γ-α)/(β-α)) = ±π/2 であることは、その商が純虚数であることと同値である。")
    qb.add_mc(sid, uid, 3, "異なる3点 α, β, γ が一直線上にあるための条件は？",
              "(γ - α) / (β - α) が実数",
              ["(γ - α) / (β - α) が純虚数", "|γ - α| = |β - α|", "α + β + γ = 0"],
              "偏角の差 arg((γ-α)/(β-α)) が 0 または π であることは、その商が実数であることと同値。")
    qb.add_mc(sid, uid, 2, "w = (1 + √3i) z は、点 z を原点の周りにどのように変換した点か？",
              "反時計回りに π/3 回転し、原点からの距離を 2倍にした点",
              ["時計回りに π/3 回転し、2倍にした点", "反時計回りに π/6 回転し、2倍にした点", "反時計回りに π/3 回転し、√3倍にした点"],
              "1 + √3 i = 2(cos(π/3) + i sin(π/3)) を掛けることは、偏角 +π/3 の回転と 2倍の拡大に対応する。")
    qb.add_mc(sid, uid, 3, "複素数 z が |z - 2| = 2|z + 1| を満たすとき、点 z が描く図形（アポロニウスの円）の半径は？", "2",
              ["1", "3", "4"],
              "2点 2 と -1 の距離は 3。比 2:1 の内分点 0 と外分点 -4 を直径の両端とする円なので直径 4 ⇒ 半径 2。")
    qb.add_mc(sid, uid, 3, "1の3乗根のうち虚数である ω = cos(2π/3) + i sin(2π/3) について、1, ω, ω^2 の3点が作る三角形は？",
              "正三角形", ["直角二等辺三角形", "鈍角二等辺三角形", "一直線になり三角形を作らない"],
              "単位円上の偏角 0, 2π/3, 4π/3 の3点なので正三角形をなす。")

    qb.add_ox(sid, uid, 1, "複素数 z とその共役複素数 z̄ について、z・z̄ = |z|^2 が常に成り立つ。", True,
              "(a+bi)(a-bi) = a^2 + b^2 = |z|^2。")
    qb.add_ox(sid, uid, 2, "複素数 z が実数であるための必要十分条件は z = z̄ である。", True,
              "z = x + yi と z̄ = x - yi が等しい ⇔ y = 0 ⇔ z は実数。")
    qb.add_ox(sid, uid, 2, "複素数 z = r(cosθ - i sinθ) (r > 0) は、そのまま z の極形式である。", False,
              "極形式は r(cosθ + i sinθ)（+ 符号）の形であり、cos(-θ) + i sin(-θ) に直して偏角 -θ とする必要がある。")
    qb.add_ox(sid, uid, 3, "複素数平面上の点 z を点 α の周りに角 θ だけ回転させた点 w は w - α = (cosθ + i sinθ)(z - α) で与えられる。", True,
              "α を原点に平行移動して回転し、再び α だけ平行移動して戻した式である。")


# ============================================================
# 6. 化学基礎 (kagaku): 3単元 × 56問 = 168問
# ============================================================

def generate_kagaku(qb: QuestionBank) -> None:
    sid = "kagaku"

    # --- kagaku-u1: 物質の構成 (56問) ---
    uid = "kagaku-u1"
    # 1) 純物質/混合物・単体/化合物・分離法・同素体・炎色反応 (選択・記述・○×)
    k1_mc = [
        (1, "次の物質のうち、「純物質」に分類されるものはどれか？", "蒸留水", ["空気", "海水", "塩酸"],
         "空気（N2, O2等）、海水（水と塩類）、塩酸（HCl水溶液）は混合物。蒸留水は H2O のみの純物質。"),
        (1, "次の物質のうち、「単体」に分類されるものはどれか？", "オゾン", ["水", "二酸化炭素", "アンモニア"],
         "オゾン (O3) は酸素元素1種類のみからできている単体である。他は2種類以上の元素からなる化合物。"),
        (1, "塩酸に溶けない泥を含んだ食塩水から、泥だけを取り除くのに最も適した分離法は？", "ろ過",
         ["蒸留", "分留", "再結晶"], "液体と不溶性の固体を分離するにはろ紙を用いた「ろ過」を行う。"),
        (1, "原油を沸点の差を利用してガソリン・灯油・軽油などに分離する方法を何というか？", "分留",
         ["抽出", "昇華法", "クロマトグラフィー"], "互いに溶け合う複数の液体の混合物を沸点の差で分ける操作を分留（分別蒸留）という。"),
        (2, "少量の食塩を含む硝酸カリウムの混合物から、温度による溶解度の差を利用して純粋な硝酸カリウムを得る方法は？", "再結晶",
         ["蒸留", "昇華法", "抽出"], "硝酸カリウムは温度変化による溶解度の差が非常に大きいため再結晶で精製できる。"),
        (2, "ヨウ素の水溶液（ヨウ素水）にヘキサンを加えて振り混ぜ、ヨウ素をヘキサン層へ移動させて分離する方法は？", "抽出",
         ["ろ過", "再結晶", "分留"], "特定の溶媒への溶けやすさの差を利用して成分を取り出す操作を抽出という。"),
        (2, "物質の吸着力の差（移動速度の差）を利用して色素などを分離する方法は？", "クロマトグラフィー",
         ["再結晶", "蒸留", "抽出"], "ろ紙やシリカゲルなどの固定相と溶媒（移動相）の相互作用の差を利用するのがクロマトグラフィー。"),
        (1, "次の元素の組合せのうち、同素体が存在する元素「SCOP」に含まれないものはどれか？", "窒素 (N)",
         ["硫黄 (S)", "炭素 (C)", "リン (P)"], "同素体をもつ代表的な元素は S(硫黄), C(炭素), O(酸素), P(リン) の4つ。"),
        (2, "炭素の同素体のうち、正六角形の網目構造が層をなし、電気伝導性をもつものはどれか？", "黒鉛（グラファイト）",
         ["ダイヤモンド", "フラーレン C60", "非晶質炭素"], "黒鉛は平面上の3つの価電子で共有結合し、残りの1個が自由電子のように動くため電気を通す。"),
        (2, "黄リンと赤リンの性質の違いとして正しい記述はどれか？", "黄リンは自然発火しやすいため水中に保存する",
         ["赤リンは猛毒で空気中で自然発火する", "黄リンはマッチ箱の側面に塗られている", "両者は原子番号が異なる別の元素である"],
         "黄リンは発火点が低く猛毒のため水中保存し、安定な赤リンはマッチ箱の側薬に使われる。"),
        (1, "次の元素と炎色反応の色の組合せのうち、正しいものはどれか？", "ナトリウム：黄色",
         ["カリウム：青緑色", "銅：赤紫色", "カルシウム：黄色"],
         "Li(赤), Na(黄), K(赤紫), Cu(青緑), Ca(橙赤), Ba(黄緑)。"),
        (2, "炎色反応で「青緑色」を示す元素はどれか？", "銅 (Cu)",
         ["バリウム (Ba)", "リチウム (Li)", "ストロンチウム (Sr)"], "銅は青緑色、バリウムは黄緑色、リチウムは赤色、ストロンチウムは深赤（紅）色。"),
        (1, "液体が気体にならず、固体から直接気体に変化する現象を何というか？", "昇華",
         ["融解", "蒸発", "凝縮"], "ドライアイスやヨウ素、ナフタレンなどが固体から直接気体になる現象を昇華という。"),
        (2, "物質が固体から液体へ状態変化している間（融解中）、外部から熱を加え続けても温度が一定に保たれる理由は？",
         "加えた熱エネルギーが粒子間の結合を切る（融解熱）ために使われるから",
         ["温度計が壊れるから", "熱がすべて空気中に逃げるから", "化学反応が起きて吸熱するから"],
         "状態変化の際には粒子の熱運動の激しさ（温度）ではなく配置を変えるポテンシャルエネルギーの増加に熱が使われる。"),
        (2, "次のうち、二酸化炭素 (CO2) の検出に用いられる定番の試薬・変化は？", "石灰水に通じると白く濁る",
         ["塩化コバルト紙が赤変する", "硝酸銀水溶液で白色沈殿が生じる", "湿らせた赤色リトマス紙が青変する"],
         "石灰水（Ca(OH)2 水溶液）は CO2 を通じると炭酸カルシウム (CaCO3) の白色沈殿を生じて白濁する。"),
        (1, "原子の中心にある原子核を構成している2種類の粒子は？", "陽子と中性子",
         ["陽子と電子", "中性子と電子", "電子と光子"], "原子核は正電荷の陽子と電荷をもたない中性子からなり、周囲を負電荷の電子が回る。"),
        (1, "原子番号を決定している粒子の数はどれか？", "陽子の数",
         ["中性子の数", "質量数", "価電子の数"], "原子番号 = 陽子の数 = 中性原子における電子の数 である。"),
        (2, "同位体（アイソトープ）の説明として正しいものはどれか？", "原子番号（陽子数）が同じで、質量数（中性子数）が異なる原子同士",
         ["質量数が同じで、原子番号が異なる原子同士", "同じ元素からなる単体で性質が異なるもの", "電子の数が異なる同じ原子のイオン"],
         "同位体は陽子数が同じで中性子数が異なる（例: 12C, 13C, 14C）。同素体との混同に注意。"),
        (2, "放射線を放出して別の原子に変わる性質をもつ同位体（例: 14C）を何というか？", "放射性同位体（ラジオアイソトープ）",
         ["安定同位体", "同素体", "遷移元素"], "年代測定などに用いられる 14C のように原子核が崩壊して放射線を出すものを放射性同位体という。"),
        (2, "電子殻のうち、内側から3番目の殻である「M殻」に収容できる電子の最大数は何個か？", "18個",
         ["2個", "8個", "32個"], "n番目の電子殻の最大収容数は 2n^2 個なので、M殻 (n=3) は 2×3^2 = 18個。"),
        (2, "18族の貴ガス（希ガス）元素であるヘリウム (He) やネオン (Ne) の「価電子の数」はいくつか？", "0",
         ["2", "8", "18"], "貴ガスは電子配置が極めて安定で他原子と結合・反応しにくいため、価電子の数は 0 とする（最外殻電子は He=2, Ne=8）。"),
        (2, "周期表の縦の列「族」について、化学的性質が互いに似た元素が同じ列に並ぶ主な理由は？", "価電子の数が同じだから",
         ["質量数が同じだから", "電子殻の数が同じだから", "中性子の数が同じだから"],
         "同じ族の典型元素は価電子の数が等しいため、陽イオン・陰イオンのなりやすさや結合の手の数が似る。"),
        (2, "1族元素のうち、水素 (H) を除く Li, Na, K などの総称は？", "アルカリ金属",
         ["アルカリ土類金属", "ハロゲン", "遷移元素"], "1族の金属元素をアルカリ金属といい、水と激しく反応して塩基性を示す。"),
        (2, "17族に属する F, Cl, Br, I などの非金属元素の総称は？", "ハロゲン",
         ["貴ガス", "アルカリ土類金属", "典型金属"], "17族は価電子7個で1価の陰イオンになりやすく、塩を作りやすいことからハロゲンと呼ばれる。"),
        (3, "原子から電子を1個取り去って1価の陽イオンにするのに必要な最小のエネルギーを何というか？", "第一イオン化エネルギー",
         ["電子親和力", "電気陰性度", "活性化エネルギー"],
         "イオン化エネルギーが小さい元素ほど電子を放出して陽イオンになりやすい（アルカリ金属で最小）。"),
        (3, "同じ周期で比較したとき、一般に「第一イオン化エネルギー」が最も大きいのはどの族の元素か？", "18族（貴ガス）",
         ["1族（アルカリ金属）", "2族（アルカリ土類金属）", "17族（ハロゲン）"],
         "貴ガスは閉殻・オクテット構造で電子が非常に安定しているため、電子を引き剥がすのに最大のエネルギーを要する。"),
        (3, "次の粒子の中で、電子の総数がネオン原子 (10Ne) と異なるものはどれか？", "S^2-",
         ["Na+", "F-", "Mg^2+"], "10Ne の電子数は 10。Na+(11-1=10), F-(9+1=10), Mg^2+(12-2=10) だが、S^2-(16+2=18) は Ar 型。"),
        (3, "同族（同じ縦の列）の原子番号が大きい元素ほど、第一イオン化エネルギーが小さくなる傾向がある理由は？",
         "最外殻電子が原子核から遠くなり、静電気的な引力が弱まるから",
         ["原子核の陽子数が減るから", "電子殻の数が減るから", "中性子が電子を押し出すから"],
         "周期が下に行くほど電子殻が増えて原子半径が大きくなり、外側の電子を引き剥がしやすくなる。"),
    ]
    for diff, q, ans, dist, exp in k1_mc:
        qb.add_mc(sid, uid, diff, q, ans, dist, exp)

    # 計算・知識記述 (16問)
    k1_writes = [
        (1, "固体から液体に変化することを何というか？", "融解", "固体が熱を吸収して液体になる状態変化を融解という。", None),
        (1, "ヨウ素やドライアイスなどの分離に用いられる、固体から直接気体になる性質を利用した分離法は？", "昇華法", "昇華する物質のみを気化・再凝固させて分離する方法を昇華法という。", ["昇華"]),
        (1, "砂（水に溶けない）と塩化ナトリウムの混合物を水に加えてかき混ぜ、ろ紙で分離する操作の名称は？", "ろ過", "不溶性の固体を液体から分離する操作をろ過という。", None),
        (1, "酸素 (O2) とオゾン (O3) のような、同じ元素からなる単体で性質が異なる物質同士の関係を何というか？", "同素体", "同じ元素の単体同士の異なる構造のものを同素体という。", None),
        (1, "リチウム (Li) を含む化合物を炎の中に入れたときに見られる炎色反応の色は？（漢字2字または1字で）", "赤色", "Li は赤色（深紅色）を示す。", ["赤", "深赤"]),
        (1, "窒素 (N) の元素記号は N である。では塩素の元素記号を半角英字で答えよ。", "Cl", "塩素（Chlorine）の元素記号は Cl。", None),
        (1, "カリウムの元素記号を半角英字で答えよ。", "K", "カリウム（Kalium）の元素記号は K。", None),
        (2, "原子番号 17、質量数 35 の塩素原子 (35_17 Cl) に含まれる「中性子」の数は何個か？", "18", "中性子数 = 質量数 - 原子番号 = 35 - 17 = 18個。", ["18個"]),
        (2, "原子番号 11、質量数 23 のナトリウム原子 (23_11 Na) の電子の数は何個か？", "11", "中性原子の電子数は陽子数（原子番号）と等しく 11個。", ["11個"]),
        (2, "原子番号 13 のアルミニウムイオン (Al^3+) がもつ電子の数は何個か？", "10", "Al 原子の電子 13個から 3個失って 3価の陽イオンになるため 13 - 3 = 10個。", ["10個"]),
        (2, "原子番号 16 の硫化物イオン (S^2-) がもつ電子の数は何個か？", "18", "S 原子の電子 16個に 2個受け取るため 16 + 2 = 18個。", ["18個"]),
        (2, "塩素原子 (原子番号 17) の最外殻（M殻）にある電子の数は何個か？", "7", "K殻に2個、L殻に8個、残る 17 - 10 = 7個が M殻に入る。", ["7個"]),
        (2, "カルシウム原子 (原子番号 20) の電子配置で、K殻・L殻・M殻・N殻に入る電子数は順に 2, 8, x, 2 である。x はいくつか？", "8", "M殻は最大18個入るが、19・20番目の電子は8個で安定な枠を作ったあと先に N殻に入るため 2, 8, 8, 2。", None),
        (2, "原子が電子を1個受け取って1価の陰イオンになるときに放出されるエネルギーを何というか？", "電子親和力", "電子を受け取る際のエネルギー変化の大きさ（安定化の度合い）を電子親和力という。", None),
        (3, "天然の塩素には質量数 35 (存在比 75%) と質量数 37 (存在比 25%) の2種類の同位体がある。これらから算出される塩素の原子量は？（小数第1位まで）", "35.5",
         "35×0.75 + 37×0.25 = 26.25 + 9.25 = 35.5。", None),
        (3, "陽子数 26、中性子数 30 の鉄原子の質量数はいくらか？", "56", "質量数 = 陽子数 + 中性子数 = 26 + 30 = 56。", None),
    ]
    for diff, q, ans, exp, alt in k1_writes:
        qb.add_write(sid, uid, diff, q, ans, exp, alt=alt)

    # ○× (12問) -> 28 + 16 + 12 = 56問!
    k1_ox = [
        (1, "食塩水は、塩化ナトリウムと水という2種類の純物質が混ざった「混合物」である。", True, "組成が一定でなく、物理的な操作（蒸留など）で分離できるため混合物。"),
        (1, "空気中で約 78% を占めている気体は酸素である。", False, "空気の約 78% は窒素 (N2) で、酸素 (O2) は約 21% である。"),
        (1, "ドライアイスは二酸化炭素の固体であり、常圧下では液体にならずに昇華して気体になる。", True, "二酸化炭素の三重点は 5.1気圧以上にあるため、1気圧では固体から直接気体へ昇華する。"),
        (2, "同じ元素の同位体（例: 12C と 14C）は、質量は異なるが化学的性質はほぼ同じである。", True, "化学的性質は電子配置（陽子数）で決まるため、中性子数が違っても化学反応の性質はほぼ同じ。"),
        (2, "金属元素は一般に電子を失って陰イオンになりやすい。", False, "金属元素はイオン化エネルギーが小さく、電子を放出して「陽イオン」になりやすい。"),
        (2, "2族元素のうち、Be（ベリリウム）と Mg（マグネシウム）を除く Ca, Sr, Ba, Ra を狭義の「アルカリ土類金属」という。", True, "Be と Mg は水と常温で反応しにくく炎色反応も示さないため、Ca 以下と区別される。"),
        (2, "遷移元素（3族〜11族）はすべて金属元素であり、価電子の数は原則として1個または2個である。", True, "内側の電子殻に電子が充填されていくため最外殻電子数がほぼ一定になり、似た性質を示す。"),
        (2, "同じ電子配置（電子数 10個）をもつ O^2-, F-, Na+, Mg^2+ のうち、イオン半径が最も大きいのは Mg^2+ である。", False, "電子数が同じなら原子番号（核の正電荷）が大きいほど電子を強く引き寄せるため半径は最小になる。最大は O^2-。"),
        (2, "絶対零度 (-273.15 ℃) に近づくほど、物質を構成する粒子の熱運動は激しくなる。", False, "絶対温度が下がるほど熱運動は弱まり、絶対零度で熱運動がほぼ停止する。"),
        (2, "電子の質量は、陽子や中性子の質量のおよそ 1 / 1840 と非常に小さい。", True, "そのため原子の質量のほとんどは原子核（陽子と中性子）が占める。"),
        (3, "35Cl と 37Cl の2種類の塩素原子が存在するとき、塩素分子 Cl2 には質量の異なる分子が合計 3種類 存在する。", True, "(35,35), (35,37), (37,37) の3通りの組合せがある。"),
        (3, "電子親和力は 18族の貴ガス元素で最大となる。", False, "貴ガスは安定しているため電子を受け取りにくく電子親和力はほぼ0（負）であり、最大は17族のハロゲン。"),
    ]
    for diff, q, is_t, exp in k1_ox:
        qb.add_ox(sid, uid, diff, q, is_t, exp)

    # --- kagaku-u2: 物質の変化 (56問) ---
    uid = "kagaku-u2"
    # 1) 物質量 (mol)・モル質量・気体体積・溶液濃度・化学反応式計算 (記述 14問 + 選択 6問)
    mol_writes = [
        (1, "二酸化炭素 CO2 の分子量はいくらか？（原子量: C=12, O=16）", "44", "12 + 16×2 = 44。", None),
        (1, "水 H2O 36 g は何 mol か？（原子量: H=1, O=16）", "2", "H2O のモル質量は 18 g/mol。36 / 18 = 2 mol。", ["2.0", "2mol", "2.0mol"]),
        (1, "標準状態（0℃, 1.013×10^5 Pa）において、メタン CH4 0.50 mol の体積は何 L か？", "11.2",
         "気体の種類によらず標準状態 1 mol = 22.4 L。22.4 × 0.50 = 11.2 L。", ["11.2L"]),
        (2, "標準状態で 5.6 L の二酸化炭素 CO2 の質量は何 g か？（C=12, O=16）", "11",
         "物質量は 5.6 / 22.4 = 0.25 mol。質量は 44 × 0.25 = 11 g。", ["11.0", "11g", "11.0g"]),
        (2, "水酸化ナトリウム NaOH (式量 40) 8.0 g を水に溶かして全体を 500 mL (0.50 L) にした。この水溶液のモル濃度は何 mol/L か？", "0.4",
         "NaOH は 8.0 / 40 = 0.20 mol。0.20 mol / 0.50 L = 0.40 mol/L。", ["0.40", "0.4mol/L", "0.40mol/L"]),
        (2, "0.20 mol/L の塩化ナトリウム水溶液 250 mL 中に含まれる NaCl は何 mol か？", "0.05",
         "0.20 mol/L × 0.25 L = 0.050 mol。", ["0.050", "0.05mol", "0.050mol"]),
        (2, "2.0 mol/L の塩酸 100 mL に水を加えて全体を 500 mL に希釈したとき、希釈後のモル濃度は何 mol/L か？", "0.4",
         "C1 V1 = C2 V2 より 2.0 × 100 = C2 × 500 ⇒ C2 = 0.40 mol/L。", ["0.40", "0.4mol/L", "0.40mol/L"]),
        (3, "質量パーセント濃度 36.5%、密度 1.2 g/cm^3 の濃塩酸（HCl 分子量 36.5）のモル濃度は何 mol/L か？", "12",
         "溶液 1 L (1000 cm^3) の質量は 1200 g。溶質 HCl は 1200 × 0.365 = 438 g。438 / 36.5 = 12 mol/L。", ["12.0", "12mol/L"]),
        (2, "プロパン C3H8 1.0 mol を完全燃焼させるとき、必要な酸素 O2 は何 mol か？", "5",
         "C3H8 + 5 O2 → 3 CO2 + 4 H2O より C3H8 1 mol に対して O2 は 5 mol 必要。", ["5.0", "5mol"]),
        (3, "マグネシウム Mg 2.4 g に十分な量の塩酸を加えたとき、発生する水素 H2 は標準状態で何 L か？（Mg=24）", "2.24",
         "Mg + 2 HCl → MgCl2 + H2。Mg は 2.4 / 24 = 0.10 mol なので H2 も 0.10 mol、体積 22.4 × 0.10 = 2.24 L。", ["2.24L"]),
        (2, "0.10 mol/L の塩酸 (HCl) の pH はいくらか？", "1",
         "強酸1価なので [H+] = 0.10 = 10^-1 mol/L。よって pH = 1。", ["1.0"]),
        (2, "0.050 mol/L の硫酸 (H2SO4、完全電離とする) の pH はいくらか？", "1",
         "2価の強酸なので [H+] = 2 × 0.050 = 0.10 = 10^-1 mol/L。よって pH = 1。", ["1.0"]),
        (2, "0.010 mol/L の水酸化ナトリウム水溶液 (NaOH) の pH はいくらか？（25℃、Kw = 1.0×10^-14）", "12",
         "[OH-] = 10^-2 mol/L より [H+] = 10^-14 / 10^-2 = 10^-12 mol/L。よって pH = 12。", ["12.0"]),
        (3, "0.10 mol/L のシュウ酸水溶液 10 mL を中和するのに、0.20 mol/L の NaOH 水溶液は何 mL 必要か？（シュウ酸は2価の酸）", "10",
         "2 × 0.10 × 10 = 1 × 0.20 × V より V = 10 mL。", ["10mL", "10.0"]),
    ]
    for diff, q, ans, exp, alt in mol_writes:
        qb.add_write(sid, uid, diff, q, ans, exp, alt=alt)

    # 計算・知識の選択 (14問)
    k2_mc = [
        (1, "硫酸アンモニウム (NH4)2SO4 の式量はいくらか？（N=14, H=1, S=32, O=16）", "132",
         ["114", "98", "146"], "(14 + 4)×2 + 32 + 16×4 = 36 + 32 + 64 = 132。"),
        (2, "アボガドロ定数を 6.0×10^23 /mol とするとき、水分子 H2O 0.50 mol に含まれる「水素原子」の個数は？", "6.0×10^23 個",
         ["3.0×10^23 個", "1.2×10^24 個", "9.0×10^23 個"],
         "水分子 0.50 mol には分子 3.0×10^23 個があり、1分子中に H 原子は 2個あるため 2 × 3.0×10^23 = 6.0×10^23 個。"),
        (2, "標準状態で密度が 1.25 g/L である気体の分子量はおよそいくらか？", "28",
         ["32", "44", "16"], "1 mol (22.4 L) あたりの質量がモル質量なので 1.25 × 22.4 = 28 g/mol（N2 や CO など）。"),
        (3, "窒素 N2 0.50 mol と水素 H2 1.2 mol を反応させてアンモニア NH3 を合成するとき、最大何 mol の NH3 が生成するか？", "0.80 mol",
         ["1.0 mol", "1.2 mol", "0.60 mol"],
         "N2 + 3 H2 → 2 NH3。N2 0.50 mol に対し H2 は 1.5 mol 必要なので H2 が不足（過不足）。H2 1.2 mol からは 1.2 × (2/3) = 0.80 mol。"),
        (1, "ブレンステッド・ローリーの定義において、「酸」とはどのような物質・イオンか？", "相手に水素イオン (H+) を与える物質",
         ["水中で水酸化物イオン (OH-) を生じる物質", "相手から水素イオン (H+) を受け取る物質", "相手から電子を受け取る物質"],
         "ブレンステッド・ローリーの定義では H+ の供与体が酸、受容体が塩基（アレニウスの定義より広い）。"),
        (1, "次の酸・塩基のうち、「弱酸」に分類されるものはどれか？", "酢酸 (CH3COOH)",
         ["塩酸 (HCl)", "硫酸 (H2SO4)", "硝酸 (HNO3)"],
         "塩酸・硫酸・硝酸は代表的な強酸。酢酸・炭酸・シュウ酸・硫化水素は弱酸。"),
        (2, "pH = 3 の塩酸を純水で 100倍 に薄めた水溶液の pH はいくらか？", "5",
         ["1", "6", "300"], "[H+] が 10^-3 から 1/100 の 10^-5 mol/L になるため pH = 5。"),
        (3, "pH = 5 の塩酸を純水で 1000倍 に薄めたとき、水溶液の pH に最も近い値はどれか？", "約 6.96（7よりわずかに小さい）",
         ["8", "7", "6"], "いくら薄めても酸性溶液が塩基性（pH > 7）になることはなく、水の自己電離により 7 に近づき約 6.96 になる。"),
        (2, "酢酸ナトリウム (CH3COONa) を水に溶かしたとき、その水溶液の液性は何性になるか？", "塩基性",
         ["酸性", "中性", "両性"], "弱酸 (CH3COOH) と強塩基 (NaOH) からできた正塩の水溶液は塩の加水分解により塩基性を示す。"),
        (2, "弱酸（酢酸）を強塩基（水酸化ナトリウム）で中和滴定するとき、指示薬として最も適切なものは？", "フェノールフタレイン（無色→赤）",
         ["メチルオレンジ（赤→黄）", "BTB溶液のみ", "ヨウ素デンプン反応"],
         "中和点が弱塩基性側（pH 8〜9 付近）になるため、変色域が pH 8.0〜9.8 のフェノールフタレインを使う。"),
        (2, "中和滴定の実験において、使用前に「これから入れる溶液」で共洗いする必要がある器具の組合せは？", "ホールピペットとビュレット",
         ["コニカルビーカーとメスフラスコ", "ホールピペットとコニカルビーカー", "ビュレットとメスフラスコ"],
         "濃度が変わってはいけない溶液を正確に測り取るホールピペットとビュレットは共洗いする。コニカルビーカーはモル数が変わらなければ水で濡れていてもよい。"),
        (2, "次の物質中の下線（指定）原子の酸化数として、過酸化水素 H2O2 中の「酸素原子 O」の酸化数は？", "-1",
         ["-2", "0", "+2"], "H は +1 が2個で +2。分子全体で 0 となるため O 1個あたり -1（通常の酸化物では -2）。"),
        (2, "酸化・還元の定義において、ある物質が「酸化された」といえるのはどのような変化のときか？", "電子を失ったとき（酸化数が増加したとき）",
         ["電子を受け取ったとき（酸化数が減少したとき）", "水素と結合したとき", "酸素を失ったとき"],
         "酸化＝酸素を得る、水素を失う、電子を失う、酸化数が増加する。"),
        (3, "次の反応式 Cu + 4 HNO3 → Cu(NO3)2 + 2 NO2 + 2 H2O において、酸化剤として働いている物質と還元剤の組合せは？",
         "酸化剤: HNO3、還元剤: Cu",
         ["酸化剤: Cu、還元剤: HNO3", "酸化剤: NO2、還元剤: H2O", "酸化剤: Cu(NO3)2、還元剤: HNO3"],
         "Cu は酸化数 0 → +2 に酸化されたため還元剤、HNO3 中の N は +5 → +4 に還元されたため酸化剤。"),
    ]
    for diff, q, ans, dist, exp in k2_mc:
        qb.add_mc(sid, uid, diff, q, ans, dist, exp)

    # 酸化数・イオン化列・計算など追加記述 (10問)
    k2_writes2 = [
        (2, "二クロム酸カリウム K2Cr2O7 中のクロム原子 (Cr) の酸化数はいくつか？（符号をつけて答えよ、例: +3）", "+6",
         "K(+1)×2 + 2×Cr + O(-2)×7 = 0 ⇒ 2Cr = +12 ⇒ Cr = +6。", ["6"]),
        (2, "過マンガン酸イオン MnO4^- 中のマンガン原子 (Mn) の酸化数は？（符号付き）", "+7",
         "Mn + 4×(-2) = -1 ⇒ Mn = +7。", ["7"]),
        (2, "アンモニウムイオン NH4^+ 中の窒素原子 (N) の酸化数は？（符号付き）", "-3",
         "N + 4×(+1) = +1 ⇒ N = -3。", None),
        (2, "硫酸イオン SO4^2- 中の硫黄原子 (S) の酸化数は？（符号付き）", "+6",
         "S + 4×(-2) = -2 ⇒ S = +6。", ["6"]),
        (1, "塩化アンモニウム NH4Cl のような「強酸と弱塩基からできた塩」の水溶液は何性を示すか？（〇〇性）", "酸性",
         "強酸 (HCl) と弱塩基 (NH3) の塩は加水分解により弱酸性を示す。", ["弱酸性"]),
        (1, "炭酸水素ナトリウム NaHCO3 のように、元の酸の H が一部残っている塩を分類上何というか？", "酸性塩",
         "組成中に交換可能な H+ が残っている塩を酸性塩という（水溶液の液性は弱塩基性である点と混同しないこと）。", None),
        (2, "Cu, Zn, Ag, Fe の4種類の金属のうち、イオン化傾向が最も大きい金属を元素記号で答えよ。", "Zn",
         "イオン化列は K > Ca > Na > Mg > Al > Zn > Fe > Ni > Sn > Pb > (H2) > Cu > Hg > Ag > Pt > Au。", None),
        (2, "濃硝酸と濃塩酸を体積比 1 : 3 で混ぜた、金 (Au) や白金 (Pt) も溶かす強い酸化力をもつ混合液を何というか？", "王水",
         "濃硝酸と濃塩酸を 1 : 3 で混合した液体を王水という。", None),
        (3, "硫酸酸性の過マンガン酸カリウム水溶液で MnO4^- が反応して Mn^2+ になるとき、MnO4^- 1 mol が受け取る電子は何 mol か？", "5",
         "MnO4^- + 8 H+ + 5 e- → Mn^2+ + 4 H2O（酸化数 +7 → +2 より 5 mol）。", ["5mol", "5.0"]),
        (3, "鉄 (Fe) を濃硝酸に浸したとき、表面に緻密な酸化被膜ができて溶けなくなる現象を何というか？", "不動態",
         "Fe, Ni, Cr, Al, Co などの金属が濃硝酸に浸されると表面に緻密な酸化被膜を作り反応が止まる現象を不動態という。", None),
    ]
    for diff, q, ans, exp, alt in k2_writes2:
        qb.add_write(sid, uid, diff, q, ans, exp, alt=alt)

    # ○× (12問)
    k2_ox = [
        (1, "標準状態 (0℃, 1.013×10^5 Pa) において、水素 H2 1 mol の体積と酸素 O2 1 mol の体積はともに約 22.4 L である。", True,
         "アボガドロの法則より、理想気体では種類によらず標準状態 1 mol が約 22.4 L になる。"),
        (1, "塩化ナトリウム NaCl のようにイオンからなる物質は、分子量ではなく「式量」で表す。", True,
         "分子を作らないイオン結晶や金属・共有結合の結晶には組成式に対する式量を用いる。"),
        (2, "アンモニア (NH3) は、ブレンステッド・ローリーの定義では H+ を受け取るため塩基として働く。", True,
         "NH3 + H2O ⇄ NH4^+ + OH^- のように H+ を受け取るため塩基である。"),
        (2, "2価の酸である硫酸 H2SO4 と 1価の酸である塩酸 HCl は、同じモル濃度なら同じ量の NaOH を中和できる。", False,
         "2価の硫酸は1分子あたり H+ を2個出すため、同体積・同濃度なら2倍の NaOH と反応する。"),
        (2, "酸性塩である炭酸水素ナトリウム (NaHCO3) の水溶液は酸性を示す。", False,
         "NaHCO3 は分類上は「酸性塩」だが、水溶液は加水分解により「弱塩基性」を示す。"),
        (2, "過酸化水素 H2O2 は、相手によって酸化剤としても還元剤としても働くことができる。", True,
         "O の酸化数が -1 のため、-2 に還元も 0 (O2) に酸化もされうる（KMnO4 と反応する際は還元剤）。"),
        (2, "金属のイオン化傾向が大きい金属ほど、単体として酸化されにくく、陽イオンになりにくい。", False,
         "イオン化傾向が大きい金属ほど電子を失いやすく（酸化されやすく）、陽イオンになりやすい。"),
        (2, "銅 (Cu) は希塩酸や希硫酸には溶けないが、熱濃硫酸や硝酸には酸化されて溶ける。", True,
         "Cu は H2 よりイオン化傾向が小さいため H+ では酸化されないが、酸化力のある硝酸・熱濃硫酸とは反応する。"),
        (3, "0.1 mol/L の酢酸水溶液と 0.1 mol/L の塩酸を同体積ずつ用意したとき、完全に中和するのに必要な NaOH 水溶液の体積は同じである。", True,
         "どちらも1価の酸で物質量が等しいため、弱酸でも電離平衡が移動してすべて反応し、必要な塩基量は等しくなる。"),
        (3, "半反応式は、電子 e- が化学反応式の左辺にあれば還元剤、右辺にあれば酸化剤の働きを示している。", False,
         "逆！左辺に + e- があるのは電子を受け取る（自分が還元される＝相手を酸化する「酸化剤」）半反応式である。"),
        (2, "トタンは鉄板に亜鉛 (Zn) をめっきしたもので、傷がついても鉄より亜鉛が先に溶けて鉄の腐食を防ぐ。", True,
         "Zn > Fe より亜鉛が犠牲陽極として先に酸化される。ブリキ (Fe に Sn) は鉄が先に錆びる。"),
        (2, "同じ温度の純水において、水素イオン濃度 [H+] と水酸化物イオン濃度 [OH-] の積（水のイオン積 Kw）はほぼ一定である。", True,
         "25℃ では常に Kw = [H+][OH-] = 1.0×10^-14 (mol/L)^2 となる。"),
    ]
    for diff, q, is_t, exp in k2_ox:
        qb.add_ox(sid, uid, diff, q, is_t, exp)

    # kagaku-u2 追加6問 (合計56問へ)
    k2_extra = [
        (2, "メチルオレンジの変色域 (pH 3.1〜4.4) で、pH 3.1 より小さい強酸性領域での色は何色か？", "赤色",
         ["黄色", "青色", "無色"], "メチルオレンジは酸性側で赤色、塩基性（pH 4.4以上）で黄色を示す。"),
        (2, "中和滴定において「強酸（塩酸）× 弱塩基（アンモニア水）」の組み合わせのとき、中和点付近の液性は何性になるか？", "酸性",
         ["塩基性", "中性", "常に pH 7"], "生成する NH4Cl 水溶液が加水分解して弱酸性を示すため、メチルオレンジを指示薬に選ぶ。"),
        (2, "メスフラスコを使って正確な濃度の水溶液を調製する際、溶質を溶かした後に標線まで何を加えるか？", "純水（蒸留水）",
         ["濃塩酸", "エタノール", "元の溶液"], "液面（メニスカスの底）が標線に一致するまで純水を加えて体積を正確に合わせる。"),
        (3, "0.10 mol/L の過マンガン酸カリウム水溶液 10 mL が、酸性条件下で 0.50 mol/L の過酸化水素水何 mL と過不足なく反応するか？", "5.0 mL",
         ["10 mL", "2.5 mL", "20 mL"],
         "受け取る電子 5×0.10×10 = 5 mmol。H2O2 は1 mol あたり 2 mol の電子を出すため 2×0.50×V = 5 ⇒ V = 5.0 mL。"),
        (1, "反応前後で、酸化数の変化を伴う反応の総称を何というか？", "酸化還元反応",
         ["中和反応", "加水分解", "置換反応"], "電子の授受（酸化数の増減）がある反応を酸化還元反応という。"),
        (3, "ダニエル電池において、負極の亜鉛板 (Zn) で起こる反応は酸化・還元のどちらか？", "酸化反応 (Zn → Zn^2+ + 2e-)",
         ["還元反応 (Zn^2+ + 2e- → Zn)", "中和反応", "沈殿反応"], "負極ではイオン化傾向の大きい金属が電子を出して溶ける（酸化される）。"),
    ]
    for diff, q, ans, dist, exp in k2_extra:
        qb.add_mc(sid, uid, diff, q, ans, dist, exp)

    # --- kagaku-u3: 化学結合 (56問) ---
    uid = "kagaku-u3"
    # 選択 (28問)
    k3_mc = [
        (1, "陽イオンと陰イオンが静電気的引力（クーロン力）によって結びつく結合を何というか？", "イオン結合",
         ["共有結合", "金属結合", "水素結合"], "主に金属元素の陽イオンと非金属元素の陰イオンが引き合って作る結合をイオン結合という。"),
        (1, "次の物質のうち、イオン結合（イオン結晶）からできているものはどれか？", "塩化カルシウム (CaCl2)",
         ["二酸化炭素 (CO2)", "ダイヤモンド (C)", "塩化水素 (HCl)"],
         "金属 (Ca) と非金属 (Cl) からなる CaCl2 はイオン結晶。他は共有結合による分子や結晶。"),
        (1, "アンモニウムイオン (NH4^+) と硫酸イオン (SO4^2-) からなるイオン結晶「硫酸アンモニウム」の組成式は？", "(NH4)2SO4",
         ["NH4SO4", "NH4(SO4)2", "(NH4)3(SO4)2"], "電荷の総和が 0 になるように +1 の NH4^+ が2個、-2 の SO4^2- が1個結びつく。"),
        (2, "イオン結晶がハンマーで叩くと特定の面に沿って割れやすい（劈開する）理由は？",
         "結晶の面がずれると同符号のイオン同士が隣り合い、反発力が生じるから",
         ["原子が自由電子によって緩くつながっているから", "分子間力が非常に弱いから", "共有結合がすべて切れるから"],
         "ずれた瞬間に陽イオン同士・陰イオン同士が向かい合い、強い静電気的反発で割れてしまう。"),
        (2, "塩化ナトリウム (NaCl) 型の結晶格子において、1個の Na^+ の周りに最も近く取り囲む Cl^- は何個あるか（配位数）？", "6個",
         ["4個", "8個", "12個"], "NaCl 型では上下・前後・左右の 6個の異種イオンに囲まれている（CsCl 型は 8個）。"),
        (1, "非金属元素の原子同士が互いの不対電子を出し合って電子対を共有してできる結合は？", "共有結合",
         ["イオン結合", "金属結合", "配位結合のみ"], "2つの原子が電子対を共有する結合を共有結合という。"),
        (2, "アンモニア分子 NH3 に水素イオン H+ が結合してアンモニウムイオン NH4^+ ができるとき、新しく形成された結合を特に何というか？", "配位結合",
         ["イオン結合", "金属結合", "水素結合"], "一方の原子だけが非共有電子対を提供してできる共有結合を配位結合という（形成後は4本すべて等価）。"),
        (2, "次の分子のうち、分子内に「三重結合」をもつものはどれか？", "窒素 (N2)",
         ["酸素 (O2)", "塩素 (Cl2)", "二酸化炭素 (CO2)"], "N2 は N≡N の三重結合、O2 と CO2 は二重結合、Cl2 は単結合をもつ。"),
        (2, "水分子 (H2O) の立体構造（形）として正しいものは？", "折れ線形",
         ["直線形", "三角錐形", "正四面体形"], "中心の O に2つの非共有電子対と2つの共有電子対があるため、約 104.5° の折れ線形になる。"),
        (2, "二酸化炭素 (CO2) の立体構造と分子全体の極性の組み合わせとして正しいのは？", "直線形・無極性分子",
         ["折れ線形・極性分子", "直線形・極性分子", "折れ線形・無極性分子"],
         "O=C=O の直線形であり、左右の極性が対称で打ち消し合うため分子全体としては無極性分子になる。"),
        (2, "次の分子のうち、「極性分子」に分類されるものはどれか？", "アンモニア (NH3)",
         ["メタン (CH4)", "二酸化炭素 (CO2)", "水素 (H2)"], "NH3 は三角錐形で電荷の偏りが打ち消されないため極性分子。CH4 は正四面体形で無極性。"),
        (2, "すべての元素の中で、共有電子対を引き寄せる強さ「電気陰性度」が最も大きい元素はどれか？", "フッ素 (F)",
         ["塩素 (Cl)", "酸素 (O)", "ヘリウム (He)"], "貴ガスを除くと周期表の右上にある F が最大（ポーリングの値 4.0）。"),
        (2, "同じ16族の水素化合物の中で、水 (H2O) の沸点が H2S や H2Se に比べて異常に高い理由は？",
         "分子間に強い「水素結合」が働いているから",
         ["H2O の分子量が最も大きいから", "H2O がイオン結晶を作るから", "共有結合が熱で切れにくいから"],
         "電気陰性度の大きい F, O, N に結合した H は隣の分子と強い水素結合を作るため、HF, H2O, NH3 は沸点が異常に高い。"),
        (2, "氷が水よりも密度が小さく、水に浮く主な理由は？",
         "水素結合によって隙間（空隙）の多い立体構造をとるから",
         ["氷になると水分子が分解して気泡ができるから", "氷になると共有結合が切れるから", "ファンデルワールス力が消えるから"],
         "氷では1つの H2O が周囲4分子と正四面体状に水素結合し、隙間が多くかさばった結晶構造になる。"),
        (1, "ダイヤモンドやケイ素 (Si)、二酸化ケイ素 (SiO2) などが分類される結晶の種類は？", "共有結合の結晶",
         ["分子結晶", "イオン結晶", "金属結晶"], "多数の原子が共有結合のネットワークで連続してつながった結晶を共有結合の結晶という。"),
        (2, "二酸化ケイ素 (SiO2) は分子として存在するのか、それとも共有結合の結晶か？", "多数の Si と O が共有結合で網目状につながった「共有結合の結晶」",
         ["CO2 と同じ独立した分子からなる「分子結晶」", "Si^4+ と O^2- からなる「イオン結晶」", "自由電子を含む「金属結晶」"],
         "SiO2 は石英や水晶の主成分であり、1個の Si に4個の O が正四面体状に連続結合した共有結合の結晶。"),
        (1, "次の物質のうち、「分子結晶」に分類され、常温付近で昇華性を示すものは？", "ヨウ素 (I2) / ドライアイス (CO2)",
         ["塩化ナトリウム (NaCl)", "石英 (SiO2)", "鉄 (Fe)"], "I2 やドライアイスは分子同士が弱い分子間力で結びついた分子結晶で、融点・沸点が低く昇華しやすい。"),
        (1, "金属の結晶が薄く広げられる性質「展性」や細く伸ばせる性質「延性」をもつ理由は？",
         "結晶がずれても「自由電子」が陽イオン同士をつなぎ止める接着剤になるから",
         ["金属結合がイオン結合より弱いから", "金属原子同士が共有結合しているから", "金属には隙間がないから"],
         "金属結晶では自由電子が動き回って結合を保つため、叩いてずれても割れずに変形する。"),
        (2, "銅 (Cu) に亜鉛 (Zn) を混ぜて作られる代表的な合金の名称は？", "黄銅（しんちゅう）",
         ["青銅（ブロンズ）", "ジュラルミン", "ステンレス鋼"], "黄銅（Cu+Zn）、青銅（Cu+Sn）、ジュラルミン（Al+Cu+Mg等）、ステンレス鋼（Fe+Cr+Ni）。"),
        (2, "青銅（ブロンズ）の主成分となる金属の組合せは？", "銅 (Cu) と スズ (Sn)",
         ["銅 (Cu) と 亜鉛 (Zn)", "鉄 (Fe) と クロム (Cr)", "アルミニウム (Al) と マグネシウム (Mg)"],
         "銅にスズを加えた合金が青銅（銅像や硬貨などに利用）。"),
        (3, "次の4種類の結晶のうち、一般に「融点が最も高い」傾向にある結晶の種類はどれか？", "共有結合の結晶（例: ダイヤモンド・SiC）",
         ["分子結晶（例: ドライアイス）", "金属結晶（例: ナトリウム）", "イオン結晶（例: 塩化ナトリウム）"],
         "ダイヤモンド（約3550℃以上）のように結合がすべて強固な共有結合で組まれているため極めて高い融点を示す。"),
        (3, "極性溶媒である水によく溶けやすい物質はどれか？", "塩化水素 (HCl) やアンモニア (NH3) のような極性分子や多くのイオン結晶",
         ["ヨウ素 (I2) やメタン (CH4)", "二酸化炭素や酸素 (O2)", "ベンゼンやヘキサン"],
         "「似たものは似たものに溶ける」の原則により、極性溶媒の水には極性分子やイオン性物質がよく溶ける。"),
        (3, "無極性分子同士の間にも働く、すべての分子間に存在する弱い引力を何というか？", "ファンデルワールス力",
         ["クーロン力", "金属結合", "配位結合"],
         "分子量の大きい無極性分子ほど電子の動きの偏りが大きくなるため、ファンデルワールス力が強まり沸点が上がる。"),
        (2, "金属の結晶格子（体心立方格子）における単位格子1個あたりの原子数は何個か？", "2個",
         ["1個", "4個", "8個"], "体心立方格子では、中心に 1個 + 8つの頂点に (1/8)×8 = 1個 ＝ 計 2個。"),
        (3, "面心立方格子における単位格子1個あたりの原子数と配位数の組は？", "原子数 4個、配位数 12",
         ["原子数 2個、配位数 8", "原子数 4個、配位数 8", "原子数 2個、配位数 12"],
         "面の中心 6×(1/2) + 頂点 8×(1/8) = 4個。最密構造であり配位数は 12。"),
        (2, "アンモニア分子 NH3 の電子式を描いたとき、窒素原子 N の上にある「非共有電子対」は何対か？", "1対",
         ["0対", "2対", "3対"], "N の価電子5個のうち3個が H と共有結合し、残り2個が1対の非共有電子対となる。"),
        (2, "塩化ナトリウムとスクロース（ショ糖）を見分ける実験で、水に溶かした後に電気を流すとどうなるか？",
         "塩化ナトリウム水溶液（電解質）のみ電流が流れる",
         ["スクロース水溶液のみ電流が流れる", "両方ともよく電流が流れる", "両方とも電流が流れない"],
         "イオン結晶の NaCl は電離して Na+ と Cl- を生じる電解質だが、共有結合分子のスクロースは非電解質。"),
        (3, "同じ無極性分子である希ガス（He, Ne, Ar, Kr）の沸点を比べると、原子番号が大きいほどどうなるか？",
         "ファンデルワールス力が強くなるため、沸点は高くなる",
         ["質量が重くても結合しないので沸点はすべて同じ", "原子番号が大きいほど沸点は低くなる", "水素結合が強まるため沸点が高くなる"],
         "分子量（原子量）・電子数が増えるほど瞬間的な電荷の偏りが大きくなりファンデルワールス力が増す。"),
    ]
    for diff, q, ans, dist, exp in k3_mc:
        qb.add_mc(sid, uid, diff, q, ans, dist, exp)

    # 記述 (16問)
    k3_writes = [
        (1, "水酸化物イオンのイオン式（例: OH^- または OH-）を半角で答えよ。", "OH-", "酸素と水素からなる1価の陰イオンは OH^-。", ["OH^-"]),
        (1, "硫酸イオンのイオン式（例: SO4^2-）を半角で答えよ。", "SO4^2-", "硫酸から H+ が2個とれた2価の陰イオンは SO4^2-。", ["SO42-", "SO₄²⁻"]),
        (1, "硝酸イオンのイオン式を半角で答えよ（例: NO3-）。", "NO3-", "1価の陰イオンは NO3-。", ["NO3^-", "NO₃⁻"]),
        (1, "ナトリウムイオン (Na+) と酸化物イオン (O^2-) からなる酸化ナトリウムの組成式は？", "Na2O", "Na+ が2個、O^2- が1個で電荷 0 になるため Na2O。", chem_alts("Na2O")),
        (1, "アルミニウムイオン (Al^3+) と硫酸イオン (SO4^2-) からなる硫酸アルミニウムの組成式は？", "Al2(SO4)3",
         "+3×2 + (-2)×3 = 0 となる最小公倍数比 2:3 より Al2(SO4)3。", chem_alts("Al2(SO4)3")),
        (2, "1個の原子がもつ「不対電子」の数のことを、その原子の共有結合における何というか？（〇の数）", "原子価",
         "共有結合を作ることができる腕の数（不対電子数）を原子価という。", ["結合の手の数", "結合の手"]),
        (2, "水分子 H2O の1分子中に存在する「非共有電子対」の数は全部で何組（対）か？", "2",
         "O の価電子6個のうち2個が H と共有され、残り4個が 2組の非共有電子対になる。", ["2組", "2対"]),
        (2, "メタン (CH4) 分子の立体構造を何形というか？", "正四面体形",
         "中心の C に4つの結合電子対が互いに最も離れる方向を向くため正四面体形（結合角約109.5°）。", ["正四面体"]),
        (2, "アンモニア (NH3) 分子の立体構造を何形というか？", "三角錐形",
         "非共有電子対1つと3つの N-H 結合が正四面体の頂点方向を向くため、原子だけを見ると三角錐形になる。", ["三角錐"]),
        (2, "鉄 (Fe) にクロム (Cr) やニッケル (Ni) を混ぜた、さびにくい合金を何というか？", "ステンレス鋼",
         "鉄にクロム約18%、ニッケル約8%などを加えた耐食性の高い合金をステンレス鋼という。", ["ステンレス"]),
        (2, "アルミニウムに銅やマグネシウムなどを加えた、軽くて強度が高い航空機材料などに使われる合金は？", "ジュラルミン",
         "軽量かつ高強度な Al 系合金をジュラルミンという。", None),
        (2, "塩化ナトリウム NaCl や塩化カルシウム CaCl2 のように、イオン結合の連続した配列から成る化合物を表す式を「分子式」に対して何式というか？", "組成式",
         "独立した分子を作らないため、構成イオンの最も簡単な整数比を示す組成式で表す。", None),
        (2, "共有電子対をどちらかの原子が引き寄せる強さの度合いを表す数値を何というか？", "電気陰性度",
         "2原子間の電気陰性度の差が大きいほど結合の極性が強くなる。", None),
        (3, "水 (H2O) やフッ化水素 (HF)、アンモニア (NH3) の分子間に働く、F・O・N と H との間の特に強い分子間力を何結合というか？", "水素結合",
         "電気陰性度の非常に大きい F, O, N に結合した H 原子を介した強い分子間引力を水素結合という。", None),
        (3, "金属の結晶において、金属結晶を構成する陽イオンの周りを自由に動き回る価電子のことを何というか？", "自由電子",
         "自由電子の存在が金属特有の電気伝導性・熱伝導性・金属光沢・展性・延性の原因である。", None),
        (3, "炭素の同素体であるダイヤモンドの結晶中では、1個の炭素原子は他の何個の炭素原子と共有結合しているか？", "4",
         "正四面体の中心と4頂点の位置関係で4個の炭素原子と強固に共有結合している。", ["4個"]),
    ]
    for diff, q, ans, exp, alt in k3_writes:
        qb.add_write(sid, uid, diff, q, ans, exp, alt=alt)

    # ○× (12問) -> 28 + 16 + 12 = 56問!
    k3_ox = [
        (1, "塩化水素 (HCl) の分子は、共有結合でできており分子全体に極性がある。", True,
         "Cl の方が H より電気陰性度が大きいため、Cl 側が δ-、H 側が δ+ に偏った極性分子になる。"),
        (1, "金属結晶は、固体状態でも液体状態（融解状態）でも電気をよく通す。", True,
         "自由電子が自由に移動できるため、固体でも液体でも高い電気伝導性を示す。"),
        (1, "イオン結晶は、固体状態では電流を流さないが、水に溶かしたり融解させたりすると電流を流す。", True,
         "固体ではイオンが固定されているが、水溶液や融解液ではイオンが自由に動けるようになる。"),
        (2, "分子結晶であるドライアイス (CO2) は、昇華するとき分子内の C=O 共有結合がすべて切れる。", False,
         "切れるのは分子同士を結びつけている弱い分子間力だけで、分子内の C=O 共有結合は切れない。"),
        (2, "アンモニウムイオン NH4^+ の4本の N-H 結合のうち、1本だけは配位結合であるため他の3本よりも長くて切れやすい。", False,
         "形成された後は4本の結合は完全に等価になり、区別できなくなる。"),
        (2, "ダイヤモンドも黒鉛も、どちらも非常に融点が高く、水に溶けにくい共有結合の結晶である。", True,
         "どちらも C 原子の共有結合の連続ネットワークでできているため融点が極めて高い。"),
        (2, "黒鉛は電気を通さないが、ダイヤモンドは電気をよく通す。", False,
         "逆！黒鉛は層内に余った非局在化電子（自由電子に類似）があるため電気を通すが、ダイヤモンドは通さない。"),
        (2, "同じ元素からなる単体の分子（例: Cl2, O2, N2）は、結合の極性がなく必ず無極性分子になる。", True,
         "同じ原子同士の電気陰性度は等しいため電子の偏りが生じない。"),
        (2, "体心立方格子の金属結晶では、1個の原子に隣接する原子の数（配位数）は 12 である。", False,
         "体心立方格子の配位数は 8 である（12 は面心立方格子・六方最密構造）。"),
        (3, "イオン結合のみからなる化合物（NaCl 等）は存在しても、共有結合とイオン結合の両方を含む化合物は存在しない。", False,
         "水酸化ナトリウム (NaOH) や硫酸アンモニウム ((NH4)2SO4) など、多原子イオンを含むイオン結晶では両方を含む。"),
        (3, "極性分子同士でないと分子間力（ファンデルワールス力）は一切働かない。", False,
         "ファンデルワールス力は極性の有無に関わらずすべての分子・原子間に普遍的に働く。"),
        (2, "分子量が近いメタン (CH4: 分子量16) とアンモニア (NH3: 分子量17) では、水素結合をもつアンモニアの方が沸点がかなり高い。", True,
         "CH4 の沸点は -162℃、NH3 は水素結合により -33℃ と大きく上昇する。"),
    ]
    for diff, q, is_t, exp in k3_ox:
        qb.add_ox(sid, uid, diff, q, is_t, exp)


# ============================================================
# 7. 生物基礎 (seibutsu): 4単元 × 42問 = 168問
# ============================================================

def generate_seibutsu(qb: QuestionBank) -> None:
    sid = "seibutsu"

    # --- seibutsu-u1: 生物の特徴 (42問) ---
    uid = "seibutsu-u1"
    s1_mc = [
        (1, "すべての生物に共通する特徴として、当てはまらないものはどれか？", "光合成を行うこと",
         ["細胞からできていること", "代謝（エネルギーの獲得と利用）を行うこと", "遺伝情報(DNA)をもち自己複製すること"],
         "光合成は植物やシアノバクテリアなど一部の独立栄養生物のみが行う。"),
        (1, "1665年にコルクの切片を顕微鏡で観察し、小部屋構造を「細胞 (cell)」と名付けた人物は？", "フック",
         ["レーウェンフック", "シュライデン", "シュワン"],
         "ロバート・フックが著書『ミクログラフィア』でコルクの細胞壁を cell と命名した。"),
        (1, "次の生物のうち、核膜をもたない「原核生物」に分類されるものはどれか？", "大腸菌 / シアノバクテリア",
         ["酵母菌", "ゾウリムシ", "アオミドロ"],
         "細菌（大腸菌など）やシアノバクテリア（ネンジュモ等）は原核生物。酵母菌は菌類であり真核生物なので要注意！"),
        (2, "原核細胞にも真核細胞にも共通して存在する細胞小器官・構造はどれか？", "リボソームと細胞膜",
         ["ミトコンドリアと核", "葉緑体とゴルジ体", "液胞と核膜"],
         "原核細胞には膜で包まれた細胞小器官（核・ミトコンドリア・葉緑体等）はないが、タンパク質合成の場であるリボソームと細胞膜・DNAは共通して持つ。"),
        (2, "動物細胞には存在せず、植物細胞に特徴的に発達している構造の組合せは？", "葉緑体・細胞壁・発達した液胞",
         ["ミトコンドリア・リボソーム・核", "細胞膜・中心体・核小体", "ミトコンドリア・細胞壁・中心体"],
         "植物細胞にはセルロースを主成分とする細胞壁、葉緑体、大きな液胞があり、一般に中心体はもたない。"),
        (2, "光学顕微鏡で観察する際、接眼レンズ10倍・対物レンズ40倍で観察した場合の総合倍率は？", "400倍",
         ["50倍", "100倍", "4000倍"], "総合倍率 = 接眼レンズ倍率 × 対物レンズ倍率 = 10 × 40 = 400倍。"),
        (2, "細胞内共生説（マーギュリス）において、真核細胞の「ミトコンドリア」の起源と考えられている生物は？", "好気性細菌",
         ["シアノバクテリア", "嫌気性細菌", "ウイルス"],
         "酸素を使って効率よくATPを作る好気性細菌が共生してミトコンドリアに、シアノバクテリアが葉緑体になったとされる。"),
        (2, "ミトコンドリアと葉緑体が「細胞内共生説」の証拠として共通して持つ特徴はどれか？",
         "二重膜構造をもち、独自の環状DNAとリボソームをもつこと",
         ["一重膜構造で、核のDNAと同じ直鎖状DNAをもつこと", "細胞壁と同じセルロースを含んでいること", "細胞分裂の際には常に消滅すること"],
         "宿主の食作用で取り込まれた名残で二重膜（内側が元の膜、外側が宿主の膜）をもち、独自のDNAを持つ。"),
        (1, "生物が体外から取り入れた簡単な物質から、エネルギーを使って複雑な有機物を合成する代謝を何というか？", "同化",
         ["異化", "発酵", "解糖"], "光合成やタンパク質合成などは「同化」、呼吸や有機物の分解は「異化」。"),
        (1, "生体内のエネルギー通貨と呼ばれる「ATP」を構成する3つの成分の組合せとして正しいのは？",
         "アデニン・リボース・3つのリン酸",
         ["アデニン・デオキシリボース・3つのリン酸", "グアニン・リボース・2つのリン酸", "チミン・デオキシリボース・3つのリン酸"],
         "ATP（アデノシン三リン酸）は RNA と同じ糖「リボース」と塩基「アデニン」にリン酸が3つ結合したもの。"),
        (2, "ATP 1分子の内部に含まれる「高エネルギーリン酸結合」は何か所あるか？", "2か所",
         ["1か所", "3か所", "4か所"], "1つ目のリン酸とリボースの結合は通常の結合で、2番目と3番目のリン酸同士の結合の2か所が高エネルギーリン酸結合。"),
        (2, "酵素の化学的な本体（主成分）は何か？", "タンパク質",
         ["炭水化物", "脂質", "核酸 (DNA)"], "酵素は主にタンパク質からなり、立体構造（活性部位）で特定の基質と結合する。"),
        (2, "ヒトの胃液に含まれる消化酵素「ペプシン」の最適 pH に最も近いものは？", "pH 2 付近（強酸性）",
         ["pH 7 付近（中性）", "pH 8〜9 付近（弱塩基性）", "pH 12 付近（強塩基性）"],
         "ペプシンは胃酸中の強酸性 (pH 2) で最もよく働き、だ液アミラーゼは中性 (pH 7)、トリプシンは弱塩基性 (pH 8) で働く。"),
        (2, "酵素反応を高温（例: 80℃以上）に加熱すると反応が進まなくなる現象「失活」の理由は？",
         "熱によって酵素（タンパク質）の立体構造が壊れて元に戻らなくなる（熱変性）から",
         ["基質が蒸発してなくなるから", "酵素が完全に分解されて原子になるから", "ATP がすべて消費されるから"],
         "タンパク質の立体構造が崩れると基質が活性部位にはまらなくなり（熱変性）、低温に戻しても活性は回復しない。"),
        (3, "無機触媒である酸化マンガン(IV) と生体触媒であるカタラーゼ（酵素）を比較したとき、カタラーゼの特徴は？",
         "常温・中性付近の穏やかな条件で高い反応性を示し、基質特異性がある",
         ["100℃に加熱すると反応速度が無限に速くなる", "過酸化水素以外の物質も無差別に分解できる", "反応の前後で自分自身も消費されて減る"],
         "酵素は特定の相手だけに働く「基質特異性」と穏やかな最適温度・最適pHをもつ点が無機触媒と異なる。"),
        (2, "酵母菌がグルコースからエタノールと二酸化炭素を生じて ATP を得る無酸素下の異化作用を何というか？", "アルコール発酵",
         ["乳酸発酵", "光合成", "好気呼吸"], "酸素を使わない異化の代表がアルコール発酵（酵母菌）と乳酸発酵（乳酸菌・激しい運動時の筋肉）。"),
        (3, "ある細菌の細胞は、体積の割に表面積が大きい小さなサイズを保っている。光学顕微鏡の限界に近いこの大きさの単位として最も適切なのは？", "約 1〜10 μm",
         ["約 1〜10 mm", "約 1〜10 nm", "約 100〜500 μm"],
         "原核細胞は一般に約 1〜5 μm、真核細胞は約 10〜100 μm、ウイルスは約 20〜300 nm 程度である。"),
        (2, "ウイルスが「生物と非生物の中間」とみなされる理由として正しい組合せは？",
         "遺伝物質(DNAかRNA)をもち増殖するが、細胞構造をもたず単独では代謝できない",
         ["細胞膜と核をもつが、DNAをもたない", "ミトコンドリアだけで光合成ができる", "単体でATPを合成して自力で分裂できる"],
         "宿主の細胞に感染しその代謝系・リボソームを借りて増殖する点では生物的だが、非細胞性で単独代謝できない点は非生物的。"),
    ]
    for diff, q, ans, dist, exp in s1_mc:
        qb.add_mc(sid, uid, diff, q, ans, dist, exp)

    s1_writes = [
        (1, "生物の細胞内で行われるすべての化学反応（同化と異化）をまとめて何というか？", "代謝", "エネルギーや物質の変換を行う化学反応の総称を代謝という。", None),
        (1, "「すべての生物は細胞からできている」という細胞説を、植物について提唱したドイツの生物学者は？", "シュライデン",
         "1838年にシュライデンが植物で、1839年にシュワンが動物で細胞説を唱えた。", None),
        (1, "「すべての細胞は細胞から生じる」と唱え、細胞説を完成させた人物は？", "ウィルヒョー", "1855年にウィルヒョーが提唱した。", ["ウィルヒョウ"]),
        (1, "植物の細胞にのみ見られ、光エネルギーを用いて有機物を合成する場となる細胞小器官は？", "葉緑体", "光合成の場は葉緑体である。", None),
        (1, "真核細胞で酸素を用いた呼吸により大量の ATP を合成する場となる細胞小器官は？", "ミトコンドリア", "好気呼吸の主な場はミトコンドリアである。", None),
        (1, "アデノシン三リン酸の略称を半角英字大文字3文字で答えよ。", "ATP", "Adenosine Triphosphate の略で ATP。", None),
        (2, "ATP が水と反応してリン酸が1つ外れたときに生じる物質を英字3文字で答えよ。", "ADP", "アデノシン二リン酸 (Adenosine Diphosphate) ＝ ADP になる。", None),
        (2, "光合成で光エネルギーにより二酸化炭素と水から有機物を合成する反応は、同化・異化のどちらか？", "同化", "単純な無機物から複雑な有機物を作るため同化である。", None),
        (2, "化学反応の開始に必要なエネルギーの壁を下げ、反応速度を速める生体触媒を何というか？", "酵素", "酵素は活性化エネルギーを下げて反応を促進する。", None),
        (2, "酵素の特定の立体構造にぴったり結合して反応を受ける相手となる物質を何というか？", "基質", "酵素は特定の基質とのみ結合して酵素-基質複合体を作る。", None),
        (2, "対物ミクロメーターの1目盛りは 10 μm である。接眼ミクロメーターの 5目盛りが対物ミクロメーターの 2目盛りと一致したとき、接眼ミクロメーターの1目盛りは何 μm か？", "4",
         "2目盛り = 20 μm なので、接眼ミクロメーター 1目盛り = 20 / 5 = 4 μm。", ["4μm", "4.0"]),
        (3, "真核細胞の内部にある、分解酵素を含み老廃物や浸透圧調節・アントシアニン等の色素を蓄える袋状の構造は？", "液胞", "植物細胞で大きく発達する一重膜の細胞小器官は液胞。", None),
    ]
    for diff, q, ans, exp, alt in s1_writes:
        qb.add_write(sid, uid, diff, q, ans, exp, alt=alt)

    s1_ox = [
        (1, "光学顕微鏡は、分解能が約 0.2 μm であり、電子顕微鏡よりも高い倍率で微細構造を観察できる。", False,
         "電子顕微鏡のほうが分解能が高く（約 0.1〜0.2 nm）、ウイルスやリボソームなども観察できる。"),
        (1, "酵母菌は単細胞生物であるが、核膜をもつため真核生物に分類される。", True,
         "菌類に属する単細胞の真核生物であり、ミトコンドリアや核を持つ。"),
        (1, "シアノバクテリアは葉緑体をもたないが、光合成色素をもち光合成を行うことができる。", True,
         "原核生物なので葉緑体はないが、細胞膜の陥入構造などにクロロフィル等をもち光合成を行う。"),
        (2, "酵素は反応によって変化したあと、1回の反応ごとに分解されて再利用できない。", False,
         "酵素は触媒であるため、反応前後で自身は変化せず繰り返し反応に利用できる。"),
        (2, "ATP は生体内でエネルギーの貯蔵庫として使われるが、長期間の大量貯蔵には適さず、その都度合成と分解が繰り返される。", True,
         "長期的な貯蔵にはデンプンやグリコーゲン、脂肪が使われ、ATP は回転の速いエネルギー通貨として働く。"),
        (2, "低温（例: 0℃付近）では酵素の反応速度は極めて遅くなるが、酵素は失活しておらず温度を上げれば再び働く。", True,
         "低温では熱運動が低下して反応が進まないだけで熱変性は起きていない。高温でのみ不可逆的に失活する。"),
        (2, "植物細胞には葉緑体があるが、呼吸を行うミトコンドリアは存在しない。", False,
         "植物細胞も生きてATPを作るためミトコンドリアをもち、昼も夜も呼吸を行っている。"),
        (2, "原核細胞の DNA は、真核細胞の核内の DNA と異なり環状であることが多い。", True,
         "原核細胞の DNA は環状で細胞質基質に存在する。"),
        (2, "人間の体細胞のうち、成熟した赤血球は核をもたない特殊な真核細胞である。", True,
         "哺乳類の赤血球は分化の過程で脱核し、より多くのヘモグロビンを運べるようになっている。"),
        (3, "酵素の反応において、基質濃度をどれだけ高くしても、酵素量が一定ならば反応速度はある上限（最大速度）で頭打ちになる。", True,
         "すべての酵素分子が基質と結合して飽和状態になると、それ以上基質を増やしても速度は上がらない。"),
        (2, "同化を行うときは一般に外部からエネルギーが必要となり、異化を行うときは一般にエネルギーが放出される。", True,
         "複雑な物質を合成する同化はエネルギーを吸収し、分解する異化はエネルギーを放出する。"),
        (3, "「すべての生物の細胞は、必ず細胞壁で覆われている」という記述は正しい。", False,
         "動物細胞には細胞壁が存在しない（細胞膜のみ）。"),
    ]
    for diff, q, is_t, exp in s1_ox:
        qb.add_ox(sid, uid, diff, q, is_t, exp)

    # --- seibutsu-u2: 遺伝子とそのはたらき (42問) ---
    uid = "seibutsu-u2"
    s2_mc = [
        (1, "1928年に肺炎双球菌を用いた実験で、死滅したS型菌の成分によって無毒のR型菌がS型菌へ「形質転換」することを発見したのは？", "グリフィス",
         ["エイブリー", "ハーシーとチェイス", "ワトソンとクリック"],
         "グリフィスが形質転換を発見し、のちにエイブリーがその本体（形質転換因子）が DNA であることを証明した。"),
        (2, "1952年に T2 ファージを用いて、DNA とタンパク質のどちらが遺伝物質であるかを放射性同位体 32P と 35S で証明したのは？", "ハーシーとチェイス",
         ["グリフィス", "メセルソンとスタール", "シャルガフ"],
         "DNAに含まれるリンを 32P、タンパク質に含まれる硫黄を 35S で標識し、大腸菌内に入った 32P が遺伝物質だと示した。"),
        (1, "DNA を構成する基本単位「ヌクレオチド」の3つの成分の組合せは？", "リン酸・デオキシリボース・塩基",
         ["リン酸・リボース・塩基", "リン酸・グルコース・アミノ酸", "硫酸・デオキシリボース・塩基"],
         "DNA の糖はデオキシリボース（RNA の糖はリボース）。"),
        (1, "DNA の二重らせん構造における相補的塩基対の正しい組み合わせは？", "A と T、G と C",
         ["A と G、T と C", "A と U、G と C", "A と C、G と T"],
         "アデニン (A) はチミン (T) と2本の水素結合、グアニン (G) はシトシン (C) と3本の水素結合で対合する。"),
        (2, "DNA の複製様式である「半保存的複製」を、重い窒素 15N を含む培地を用いて実験的に証明した研究者組は？", "メセルソンとスタール",
         ["ワトソンとクリック", "ハーシーとチェイス", "ウィルキンスとフランクリン"],
         "15N で培養した大腸菌を 14N 培地に移して分裂させ、DNA の密度の帯（中間密度）から半保存的複製を示した。"),
        (2, "細胞周期において、DNA の複製（DNA量が2倍になる過程）が行われる時期はどれか？", "S期（DNA合成期）",
         ["G1期", "G2期", "M期（分裂期）"],
         "間期は G1期 → S期（DNA複製） → G2期 の順に進み、その後 M期（核分裂・細胞質分裂）に入る。"),
        (2, "体細胞分裂の M期において、凝縮した染色体が細胞の赤道面に規則正しく並ぶ時期は？", "中期",
         ["前期", "後期", "終期"], "前期（核膜消失・染色体凝縮）→ 中期（赤道面に並ぶ）→ 後期（両極へ移動）→ 終期（核膜再形成）。"),
        (2, "細胞周期の合計が 20時間 の培養細胞において、M期にある細胞が全体の 10% を占めていた。M期の長さは何時間か？", "2時間",
         ["1時間", "4時間", "10時間"], "各時期の滞在時間は細胞数割合に比例するため、20時間 × 0.10 = 2時間。"),
        (1, "DNA の塩基配列をもとに mRNA が合成される過程を何というか？", "転写",
         ["翻訳", "複製", "スプライシング"], "DNA → mRNA が転写、mRNA → タンパク質 が翻訳（この一方向の流れがセントラルドグマ）。"),
        (2, "真核生物において、転写された mRNA 前駆体から不要な部分（イントロン）を取り除き、必要な部分（エクソン）をつなぎ合わせる過程は？", "スプライシング",
         ["トランスレーション", "突然変異", "形質転換"], "スプライシングによって成熟 mRNA が作られ、核膜孔を通って細胞質のリボソームへ送られる。"),
        (2, "mRNA の連続する 3つの塩基の並びで、1つのアミノ酸を指定する単位を何というか？", "コドン（遺伝暗号）",
         ["アンチコドン", "ヌクレオソーム", "イントロン"], "mRNA 側の3塩基がコドン、それを運ぶ tRNA 側の相補的な3塩基がアンチコドン。"),
        (2, "生物の遺伝情報の1セット（例: ヒトでは約30億塩基対・23本の染色体に含まれる全情報）を何というか？", "ゲノム",
         ["コドン", "ヒストン", "オペロン"], "生殖細胞（配偶子）1組に含まれる最小限の遺伝情報一式をゲノムという。"),
        (2, "アミノ酸 100個 からなるタンパク質をコードする領域（終止コドンを除く）の mRNA の塩基数と、対応する二本鎖 DNA の塩基対数は？", "300塩基、300塩基対",
         ["100塩基、100塩基対", "300塩基、600塩基対", "150塩基、300塩基対"],
         "1アミノ酸＝3塩基なので 100×3 = 300塩基の mRNA。二本鎖 DNA でも同じ 300塩基対（合計塩基数は600個）。"),
        (2, "同じ個体の皮膚の細胞と筋肉の細胞で形や働きが大きく異なる主な理由は？", "もつゲノム（DNA）は同じだが、発現（転写）する遺伝子の組み合わせが異なるから",
         ["細胞分化の際に不要な DNA を捨てて別の DNA に書き換えるから", "皮膚細胞は RNA しか持たないから", "細胞ごとに染色体数が半分ずつ減るから"],
         "ゲノムの同一性はガードンのアフリカツメガエルの核移植実験などで証明されている。"),
        (3, "ユスリカのだ腺染色体を観察したとき、特定の部位がほどけて膨らんでいる「パフ」では何が盛んに行われているか？", "遺伝子の転写（RNA合成）",
         ["DNA の複製", "タンパク質の翻訳", "染色体の分解"],
         "染色体の凝縮がほどけて RNA ポリメラーゼが結合し、活発に転写が行われている場所がパフとして観察される。"),
        (3, "アフリカツメガエルの未受精卵の核を紫外線で破壊し、おたまじゃくしの小腸上皮細胞の核を移植してカエルへと発生させた実験（1962年）を行った研究者は？", "ガードン",
         ["ヤナギサワ", "シュペーマン", "ド・フリース"], "ガードンの核移植実験により、分化した体細胞にも個体全体を作る全遺伝情報（ゲノム）が残っていることが示された。"),
        (3, "tRNA がリボソーム上で mRNA のコドン「AUG」を認識して結合するとき、tRNA 側の相補的なアンチコドンの塩基配列は？（5'→3'または対応順で「UAC」）", "UAC",
         ["ATG", "TAC", "AUG"], "RNA では T の代わりに U を使うため、A↔U, U↔A, G↔C で「UAC」が対合する。"),
        (2, "DNA を合成する際に、塩基配列を鋳型として新しいヌクレオチド鎖をつなぐ酵素を何というか？", "DNA ポリメラーゼ",
         ["RNA ポリメラーゼ", "アミラーゼ", "リパーゼ"], "複製には DNA ポリメラーゼ、転写には RNA ポリメラーゼが働く。"),
    ]
    for diff, q, ans, dist, exp in s2_mc:
        qb.add_mc(sid, uid, diff, q, ans, dist, exp)

    # 記述 (14問) - シャルガフ計算含む！
    s2_writes = [
        (1, "RNA を構成する4種類の塩基は A, G, C と何（半角大文字1文字）か？", "U", "RNA ではチミン (T) の代わりにウラシル (U) が使われる。", None),
        (1, "DNA 1分子の二重らせん構造を1953年に提唱した2人の科学者のうち、クリックの相棒は？", "ワトソン", "ワトソンとクリックがX線回折データなどから二重らせんモデルを提唱した。", None),
        (2, "ある二本鎖 DNA において、全塩基のうちアデニン (A) の割合が 22% であった。グアニン (G) の割合は何 % か（数値のみ）？", "28",
         "シャルガフの法則より A=T=22%。残りは 100 - 44 = 56%。G=C なので G = 56/2 = 28%。", ["28%"]),
        (2, "ある二本鎖 DNA でグアニン (G) が 31% を占めるとき、チミン (T) の割合は何 % か（数値のみ）？", "19",
         "G=C=31% より A+T = 100 - 62 = 38%。よって T = 38/2 = 19%。", ["19%"]),
        (3, "二本鎖 DNA（計1000塩基対）の一方の鎖（H鎖）で A が 200個、T が 300個 含まれていた。DNA 全体（両鎖合計2000塩基）での A の総数は何個か？", "500",
         "相補鎖（L鎖）の A の数は H鎖の T の数に等しい 300個。したがって全体では 200 + 300 = 500個。", ["500個"]),
        (3, "二本鎖 DNA（2000塩基対）において、一方の鎖を鋳型として長さ 1000塩基の mRNA が転写された。鋳型鎖上の塩基で G が 250個 のとき、作られた mRNA 上の C の数は何個か？", "250",
         "鋳型鎖の G に対して相補的に mRNA には C が並ぶため、ちょうど 250個 になる。", ["250個"]),
        (1, "DNA → RNA → タンパク質 という遺伝情報の伝達の流れを表した基本原則を何というか？", "セントラルドグマ",
         "クリックが提唱した遺伝情報の一方向性の原理をセントラルドグマという。", None),
        (2, "真核生物の DNA が巻き付いている、塩基性タンパク質の名称は？", "ヒストン",
         "DNA は 8量体のヒストンに巻き付いてヌクレオソーム構造を形成する。", None),
        (2, "mRNA 上でタンパク質合成の開始を合図する開始コドンは通常「AUG」であるが、これは何というアミノ酸を指定しているか？", "メチオニン",
         "開始コドン AUG はメチオニンを指定する。", None),
        (2, "細胞分裂を一度も経験せず G1期のDNA量が「2」の細胞がある。この細胞が DNA複製を終えた直後の G2期の DNA量はいくらか？", "4",
         "S期に DNA が複製されて倍増するため、G2期の相対DNA量は 4 になる。", None),
        (2, "ヒトの体細胞1個に含まれる常染色体の本数は何本か（性染色体を除く）？", "44",
         "ヒトの体細胞は計46本（2n=46）で、うち常染色体44本＋性染色体2本（XXまたはXY）。", ["44本"]),
        (2, "ヒトの生殖細胞（精子や卵）1個に含まれる染色体の合計本数は何本か？", "23",
         "減数分裂により半減するため n = 23本（常染色体22本＋性染色体1本）。", ["23本"]),
        (3, "15N で完全に標識された大腸菌 DNA を 14N のみの培地に移し、2回分裂させたとき、全 DNA 分子のうち「15N と 14N のハイブリッド型（中間の重さ）」の DNA が占める割合は何 % か？", "50",
         "1回目でハイブリッド2本。2回目でハイブリッド2本と軽(14N-14N)2本の計4本になるため 2/4 = 50%。", ["50%"]),
        (2, "植物の体細胞分裂を観察するとき、先端の分裂組織を用いるが、観察時に細胞同士の接着を緩めて押しつぶしやすくするため塩酸などで処理する操作を何というか？", "解離",
         "固定（酢酸アルコール等）→ 解離（塩酸）→ 染色（酢酸オルセインや酢酸カーミン）→ 押しつぶし の順に行う。", None),
    ]
    for diff, q, ans, exp, alt in s2_writes:
        qb.add_write(sid, uid, diff, q, ans, exp, alt=alt)

    # ○× (10問) -> 18 + 14 + 10 = 42問!
    s2_ox = [
        (1, "エイブリーの実験では、S型菌の抽出液に DNA 分解酵素 (DNase) を加えると R型菌の形質転換が起きなくなった。", True,
         "タンパク質分解酵素や RNA 分解酵素では形質転換が起きたが、DNA 分解酵素でのみ阻止されたことで本体が DNA と示された。"),
        (1, "RNA は通常、DNA と同じように二本鎖の二重らせん構造をとっている。", False,
         "RNA は原則として一本鎖の構造をとる（ただし tRNA や rRNA の一部で相補的な折れ畳みは生じる）。"),
        (2, "DNA の二重らせんを構成する2本の鎖は、同じ向き（並行）ではなく互いに逆向き（逆平行）に走っている。", True,
         "一方が 5'→3' なら他方は 3'→5' の向きで対合する。"),
        (2, "体細胞分裂において、M期の所要時間は間期（G1 + S + G2）の所要時間よりもはるかに長い。", False,
         "多くの細胞では間期が細胞周期の大部分（約90%以上）を占め、M期は短い。"),
        (2, "1つのアミノ酸を指定するコドンは必ず1種類だけに限られる。", False,
         "コドンは 4^3 = 64通りあるのに対しアミノ酸は20種類なので、多くのアミノ酸には複数のコドン（縮重）が対応する。"),
        (2, "終止コドン（UAA, UAG, UGA）には、対応するアミノ酸を運ぶ tRNA が存在しない。", True,
         "終止コドンがリボソームに入ると解離因子が結合して翻訳が終了する。"),
        (2, "すべての生物において、細胞1個あたりの DNA 量が多いほどその生物は複雑で高等である。", False,
         "C値パラドックスと呼ばれ、両生類やユリなどヒトよりはるかに大量のDNA（非コード領域含む）をもつ生物も多い。"),
        (2, "ヒトのゲノムのうち、実際にタンパク質のアミノ酸配列をコードしている（エクソン等の）割合は全体の約 1〜2% 程度である。", True,
         "ヒトゲノム約30億塩基対の大部分はイントロンや反復配列などの非コード領域であり、遺伝子コード領域は極めて少ない。"),
        (3, "遺伝子の転写によって作られるのは mRNA だけであり、tRNA や rRNA は DNA から転写されない。", False,
         "tRNA や rRNA も DNA 上の遺伝子領域から転写されて作られる（ただしタンパク質には翻訳されない非コードRNA）。"),
        (2, "減数分裂とは異なり、通常の体細胞分裂では娘細胞の染色体数は母細胞と同じ（2n → 2n）に保たれる。", True,
         "S期のDNA複製とM期の均等分配により、体細胞分裂では同じ遺伝情報と染色体数が受け継がれる。"),
    ]
    for diff, q, is_t, exp in s2_ox:
        qb.add_ox(sid, uid, diff, q, is_t, exp)

    # --- seibutsu-u3: 生物の体内環境 (42問) ---
    uid = "seibutsu-u3"
    s3_mc = [
        (1, "外部環境の変化にかかわらず、体内の水分量・体温・血糖値・体液濃度などを一定に保つ性質を何というか？", "恒常性（ホメオスタシス）",
         ["適応放散", "走性", "形質転換"], "キャノンが提唱した内部環境を一定に保つ仕組みを恒常性（ホメオスタシス）という。"),
        (1, "体液のうち、血管からしみ出して細胞と細胞の隙間を満たしている液体はどれか？", "組織液",
         ["血漿", "リンパ液", "原尿"], "毛細血管から血漿成分の一部がしみ出したものが組織液、さらにリンパ管に入ったものがリンパ液。"),
        (2, "血液凝固の仕組みにおいて、血漿中のタンパク質「フィブリノーゲン」を繊維状の「フィブリン」に変える酵素は？", "トロンビン",
         ["プラスミン", "アミラーゼ", "トリプシン"],
         "損傷部・血小板の因子と Ca^2+ によりプロトロンビンがトロンビンになり、フィブリノーゲンをフィブリンへ変える。"),
        (2, "血液凝固した血餅を取り除いたあとに残る黄色い上澄み液を何というか？", "血清",
         ["血漿", "組織液", "リンパ液"], "血漿からフィブリノーゲンなどの凝固因子が消費されて除かれた液体が血清である。"),
        (2, "ヒトの血液循環において、右心室から肺へ「静脈血」を送り出す血管の名称は？", "肺動脈",
         ["肺静脈", "大動脈", "大静脈"],
         "心臓から出る血管が「動脈」、戻る血管が「静脈」。肺動脈は酸素の少ない静脈血を肺へ送り、肺静脈が動脈血を左心房へ戻す。"),
        (2, "酸素解離曲線において、二酸化炭素濃度 (CO2分圧) が高い組織ではヘモグロビンが酸素を離しやすくなる現象は？", "ボーア効果",
         ["ホメオスタシス", "パスツール効果", "負のフィードバック"],
         "CO2 が多く酸性度が高い活発な組織ほど曲線が右下にシフトし、より多くの O2 を組織に供給できる。"),
        (3, "肺胞 (O2分圧 100 mmHg, CO2 40 mmHg) で酸素ヘモグロビンの割合が 95%、組織 (O2分圧 30 mmHg, CO2 70 mmHg) で 35% であった。肺で結合した酸素のうち何 % が組織で解離したか？", "約 63%",
         ["60%", "約 37%", "35%"],
         "解離した量 95 - 35 = 60 を、元の結合量 95 で割る！ 60 / 95 ≈ 0.631 (約 63%)。60%と答えるひっかけに注意。"),
        (1, "腎臓で血液をろ過して原尿を作る、毛細血管が糸玉状に丸まった構造とそれを包む袋を合わせた名称は？", "腎小体（マルピーギ小体）",
         ["ネフロン", "細尿管", "集合管"], "糸球体＋ボーマンのう＝腎小体。さらに細尿管を合わせてネフロン（腎単位）という。"),
        (2, "健康なヒトの腎臓において、原尿中にろ過されたもののうち、細尿管で原則「100% 再吸収」される物質は？", "グルコース（ブドウ糖）",
         ["尿素", "クレアチニン", "ナトリウムイオン"],
         "グルコースやアミノ酸は健康なら100%再吸収される（糖尿病では閾値を超え尿に出る）。尿素は約50%が再吸収される。"),
        (2, "肝臓の働きとして「誤っている」ものはどれか？", "赤血球を新しく作り出す（造血）",
         ["有害なアンモニアを毒性の低い尿素に変える", "余分なグルコースをグリコーゲンとして貯蔵する", "脂肪の乳化を助ける胆汁を生成する"],
         "大人の赤血球は主に骨髄で作られる（肝臓は老朽化した赤血球を破壊する場であり、胆汁色素の材料にもなる）。"),
        (2, "自律神経系のうち、「交感神経」が優位になったときに起こる体の反応として正しいものは？", "心拍数の増加・気管支の拡張・消化管運動の抑制",
         ["心拍数の減少・瞳孔の縮小・消化の促進", "唾液の大量分泌（さらさら）・血圧の低下", "膀胱の収縮による排尿の促進"],
         "闘争・逃走反応に関わる交感神経は心拍・血圧・血糖を上げ、胃腸などの消化運動は抑制する。"),
        (2, "脳の部位のうち、自律神経系と内分泌系（ホルモン分泌）の両方の最高中枢として体温や血糖を調節しているのは？", "間脳の視床下部",
         ["小脳", "延髄", "大脳皮質"], "間脳の視床下部が体温・浸透圧・自律神経・脳下垂体のホルモン放出を制御する。"),
        (2, "血糖濃度を「下げる」働きをもつ唯一のホルモンと、それが分泌される部位の組合せは？", "インスリン・すい臓ランゲルハンス島B細胞",
         ["グルカゴン・すい臓ランゲルハンス島A細胞", "アドレナリン・副腎髄質", "チロキシン・甲状腺"],
         "血糖を下げるホルモンはインスリンのみ。他（グルカゴン、アドレナリン、糖質コルチコイド、成長ホルモン）はすべて血糖を上げる。"),
        (2, "腎臓の集合管における「水の再吸収」を促進し、尿量を減少させて体液の塩類濃度を下げるホルモンは？", "バソプレシン（抗利尿ホルモン）",
         ["鉱質コルチコイド", "チロキシン", "パラトルモン"],
         "脳下垂体後葉から分泌されるバソプレシンは水の再吸収を促進する（鉱質コルチコイドは Na+ の再吸収を促進）。"),
        (2, "体内に侵入した細菌や異物を直接取り込んで分解する「食作用」をもち、抗原提示も行う自然免疫の細胞は？", "マクロファージ・樹状細胞",
         ["B細胞・形質細胞", "キラーT細胞", "赤血球"],
         "特に樹状細胞は強力な抗原提示細胞としてリンパ節へ移動し、獲得免疫（ヘルパーT細胞）を始動させる。"),
        (2, "細菌や毒素などの細胞外異物に対して、抗体（免疫グロブリン）を産生して排除する仕組みを何というか？", "体液性免疫",
         ["細胞性免疫", "自然免疫", "アレルギー反応"],
         "ヘルパーT細胞に活性化された B細胞が「形質細胞（抗体産生細胞）」に分化して抗体を分泌するのが体液性免疫。"),
        (2, "ウイルス感染細胞やがん細胞などを、抗体を使わずに直接攻撃・破壊して排除する免疫担当細胞は？", "キラーT細胞（細胞性免疫）",
         ["形質細胞", "好塩基球", "記憶B細胞"],
         "キラーT細胞は細胞性免疫の主役であり、MHCクラスIに提示された異常抗原を認識して標的細胞をアポトーシスさせる。"),
        (3, "毒ヘビに噛まれた緊急時などに、あらかじめ他動物（ウマ等）で作らせた抗体を含む血清を注射して治療する方法を何というか？", "血清療法（受動免疫）",
         ["予防接種（ワクチン）", "拒絶反応", "自己免疫疾患"],
         "他者で作られた抗体を直接投与するため即効性はあるが、免疫記憶は残らず効果は一時的（また同じ抗血清を打つとアナフィラキシーのリスク）。"),
    ]
    for diff, q, ans, dist, exp in s3_mc:
        qb.add_mc(sid, uid, diff, q, ans, dist, exp)

    # 記述 (14問) - 腎臓の濃縮率・再吸収計算含む！
    s3_writes = [
        (1, "心臓の拍動リズムを生み出す、右心房にある天然のペースメーカーを何というか？", "洞房結節",
         "右心房上部にある洞房結節から電気的興奮が発生し、心臓全体へ伝わる。", ["キース・フラック結節"]),
        (1, "赤血球中に含まれ、酸素と可逆的に結合・解離して運搬する赤いタンパク質を何というか？", "ヘモグロビン",
         "鉄を含むヘムとグロビンからなる複合タンパク質ヘモグロビンが O2 を運ぶ。", None),
        (1, "腎臓のボーマンのうへろ過された液体で、まだ再吸収を受ける前の液体を何というか？", "原尿",
         "血漿中のタンパク質以外の低分子物質がろ過された液体を原尿という（ヒトで1日約150〜180 L）。", None),
        (2, "原尿にはろ過されるが、細尿管で全く再吸収も分泌もされない多糖類（濃縮率の計算に使われる物質）は？", "イヌリン",
         "イヌリンの血漿濃度と尿中濃度の比から水の濃縮率と原尿量を求めることができる。", None),
        (2, "イヌリンの血漿中濃度が 0.10 mg/mL、尿中濃度が 12.0 mg/mL、1日の尿量が 1.5 L のとき、イヌリンの濃縮率は何倍か（数値のみ）？", "120",
         "濃縮率 = 尿中濃度 / 血漿中濃度 = 12.0 / 0.10 = 120倍。", ["120倍"]),
        (3, "上の条件（イヌリン濃縮率 120倍、1日の尿量 1.5 L）のとき、1日に作られる「原尿量」は何 L か（数値のみ）？", "180",
         "イヌリンは再吸収されないため、原尿量 = 尿量 × イヌリン濃縮率 = 1.5 × 120 = 180 L。", ["180L"]),
        (3, "1日の原尿量が 180 L、尿量が 1.8 L であるとき、ろ過された水分の何 % が細尿管・集合管で再吸収されたか（数値のみ）？", "99",
         "再吸収された水は 180 - 1.8 = 178.2 L。178.2 / 180 × 100 = 99%。", ["99%"]),
        (1, "小腸で吸収された栄養素（グルコースやアミノ酸など）を豊富に含み、心臓ではなく直接「肝臓」へ注ぎ込む血管は？", "肝門脈",
         "小腸絨毛の毛細血管から肝臓へ入る血管を肝門脈（門脈）という。", ["門脈"]),
        (2, "肝臓でアミノ酸の分解時に生じた有害なアンモニアを尿素に変える代謝経路を何回路（またはオルニチン回路）というか？", "尿素回路",
         "オルニチン回路とも呼ばれ、ATP を消費してアンモニアから毒性の低い尿素を合成する。", ["オルニチン回路"]),
        (2, "交感神経の末端から分泌される主な神経伝達物質（副腎髄質のホルモンと異なり神経終末から出るもの）は？", "ノルアドレナリン",
         "交感神経末端からはノルアドレナリン、副交感神経末端からはアセチルコリンが分泌される。", None),
        (2, "ホルモンなどの最終産物が増加すると、それが視床下部や脳下垂体に作用して分泌を抑制する調節機構を「負の何」というか？", "フィードバック",
         "最終産物が上流の分泌を抑えて一定値に保つ仕組みを負のフィードバック調節という。", ["フィードバック調節"]),
        (2, "涙や唾液・鼻汁などに含まれ、細菌の細胞壁（ペプチドグリカン）を分解して感染を防ぐ自然免疫の酵素は？", "リゾチーム",
         "物理的・化学的防御の代表である抗菌物質リゾチーム（および抗菌ペプチドのディフェンシン）。", None),
        (2, "免疫応答において、同じ抗原が2回目に侵入した際、1回目よりも極めて速く大量の抗体が作られる現象は「何応答」か？", "二次応答",
         "記憶細胞（メモリーB細胞・T細胞）が体内に残っているため迅速・強力に反応する二次応答（免疫記憶）。", None),
        (2, "本来は無害な花粉や食物などの抗原に対して、獲得免疫が過剰に反応して体に不都合な症状を引き起こす現象を何というか？", "アレルギー",
         "IgE 抗体や肥満細胞（マスト細胞）からのヒスタミン放出などによる過敏症をアレルギーという。", None),
    ]
    for diff, q, ans, exp, alt in s3_writes:
        qb.add_write(sid, uid, diff, q, ans, exp, alt=alt)

    # ○× (10問) -> 18 + 14 + 10 = 42問!
    s3_ox = [
        (1, "赤血球は血液中で酸素を運ぶ役割をもち、内部には巨大な核が存在する。", False,
         "ヒトなど哺乳類の成熟した赤血球は無核である（両生類・鳥類など有核の動物もいる）。"),
        (1, "血液中の血漿タンパク質（アルブミン等）は大きいため、健康な腎臓の糸球体からはほとんどろ過されない。", True,
         "血球や巨大な血漿タンパク質は糸球体の壁を通過できず血液中に残る。"),
        (2, "糖尿病患者の尿中にグルコースが検出されるのは、インスリン不足などにより原尿中のグルコース量が再吸収の上限を超えるためである。", True,
         "ろ過された量が細尿管の輸送担体の最大能力（閾値）を超えると再吸収しきれず尿に出る。"),
        (2, "交感神経が興奮すると心拍数は増えるが、副交感神経の末端からはアセチルコリンが分泌され心拍数は減少する。", True,
         "心臓や多くの臓器は交感神経と副交感神経の二重支配を受け、互いに拮抗的に調節される。"),
        (2, "内分泌腺から分泌されるホルモンは、専用の導管を通って特定の標的器官に運ばれる。", False,
         "ホルモンは導管をもたず直接「血液」中に分泌されて全身を循環し、特定の受容体をもつ標的細胞に作用する（外分泌腺と区別）。"),
        (2, "寒い環境下では、甲状腺からチロキシンの分泌が増加し、肝臓や骨格筋などでの代謝（発熱）が活発になる。", True,
         "寒冷刺激→視床下部→脳下垂体前葉 (TSH)→甲状腺 (チロキシン) の経路で基礎代謝が上がる。"),
        (2, "血糖値が低下したときに働くホルモンは、グルカゴン、アドレナリン、糖質コルチコイド、成長ホルモンなど複数存在する。", True,
         "低血糖は直ちに生命の危機につながるため複数の経路で保護されている。"),
        (2, "予防接種（ワクチン）を打つことで獲得した免疫は、抗体そのものを注射しているため寿命が数週間しかない。", False,
         "ワクチンは弱毒化・無毒化した抗原を投与して自身の体内で記憶細胞を作らせる「能動免疫」であり、長期間持続する。"),
        (3, "後天性免疫不全症候群 (AIDS) の原因ウイルス HIV は、獲得免疫の司令塔である「ヘルパーT細胞」に感染して破壊する。", True,
         "ヘルパーT細胞が減少すると体液性免疫も細胞性免疫も機能不全に陥り、日和見感染症などを発症する。"),
        (2, "自己の正常な細胞や組織を誤って抗原とみなして免疫細胞が攻撃してしまう病気を「自己免疫疾患」という。", True,
         "関節リウマチや1型糖尿病、バセドウ病などが自己免疫疾患の代表例である。"),
    ]
    for diff, q, is_t, exp in s3_ox:
        qb.add_ox(sid, uid, diff, q, is_t, exp)

    # --- seibutsu-u4: 生態系とその保全 (42問) ---
    uid = "seibutsu-u4"
    s4_mc = [
        (1, "火山噴火後の溶岩台地など、土壌も植物の種子も存在しない裸地から始まる遷移を何というか？", "一次遷移（乾性遷移）",
         ["二次遷移", "湿性遷移", "極相"], "土壌のない状態から始まるのが一次遷移、山火事や伐採跡地など土壌・種子が残る状態からが二次遷移。"),
        (1, "一次遷移において、裸地に最初に侵入して根を張り土壌形成を助けるコケ植物や地衣類などを何というか？", "先駆種（パイオニア植物）",
         ["極相樹", "陰樹", "帰化植物"], "乾燥や貧栄養に強いコケ・地衣類やススキ・イタドリ・ヤシャブシなどが先駆種として働く。"),
        (2, "陽生植物と陰生植物の光-光合成曲線を比較したとき、陽生植物の特徴として正しいものは？",
         "光補償点も光飽和点も、陰生植物より高い",
         ["光補償点は低く、光飽和点が高い", "光補償点は高く、光飽和点が低い", "強い光の下でも陰生植物より光合成速度が低い"],
         "陽生植物は呼吸速度が大きく光補償点が高いが、強光下での最大光合成速度（光飽和点）は非常に高い。"),
        (2, "極相林（シイ・カシ・ブナ等の陰樹林）の林床が暗くても、陰樹の幼木が生き残って成長できる理由は？",
         "光補償点が低く、弱い光の下でも呼吸量を上回る光合成を行えるから",
         ["葉緑体を持たず土壌の有機物を直接吸収するから", "光飽和点が極めて高く強光を好むから", "菌類から光エネルギーをもらうから"],
         "陰樹の幼木は少ない光量でも見かけの光合成速度がプラスになるため、林内で生き残って世代交代できる。"),
        (1, "日本の暖温帯（本州中部以南の低地、年平均気温約 14〜21℃）に広く分布する常緑広葉樹からなるバイオームは？", "照葉樹林",
         ["夏緑樹林", "亜寒帯針葉樹林", "硬葉樹林"], "光沢のある厚い葉をもつシイ、カシ、タブノキ、クスノキなどからなるのが照葉樹林。"),
        (2, "日本の冷温帯（本州中部以北や山地、ブナ・ミズナラなどが代表樹種）に分布する落葉広葉樹林は？", "夏緑樹林",
         ["照葉樹林", "硬葉樹林", "雨緑樹林"], "冬に落葉し夏に緑の葉をつけるブナ・ミズナラ・カエデなどが夏緑樹林。"),
        (2, "次の樹木のうち、日本の「亜寒帯針葉樹林」（北海道北部・東部や本州高山帯下部）の代表樹種は？", "エゾマツ・トドマツ・シラビソ",
         ["スダジイ・タブノキ", "ブナ・ミズナラ", "ガジュマル・アコウ"],
         "低温に強い常緑針葉樹のエゾマツ、トドマツ、シラビソ、オオシラビソなどが優占する。"),
        (2, "地中海性気候（夏に高温・乾燥、冬に温暖・湿潤）の地域に見られ、オリーブやコルクガシが分布するバイオームは？", "硬葉樹林",
         ["照葉樹林", "雨緑樹林", "サバンナ"], "夏の乾燥に耐えるため小さく硬い常緑の葉をもつ硬葉樹林が形成される。"),
        (2, "熱帯・亜熱帯のうち、雨季と乾季の区別が明瞭で乾季に落葉するチークなどが見られるバイオームは？", "雨緑樹林",
         ["熱帯多雨林", "夏緑樹林", "ステップ"], "乾季の乾燥を防ぐため落葉する林が雨緑樹林（モンスーン林）。"),
        (2, "マメ科植物の根に共生し、大気中の窒素 (N2) を取り込んでアンモニウムイオン (NH4+) に変える（窒素固定を行う）細菌は？", "根粒菌",
         ["脱窒菌", "硝酸菌", "大腸菌"], "根粒菌（ほかに土壌中のアゾトバクターやシアノバクテリアのネンジュモ等）が窒素固定を行う。"),
        (2, "窒素循環において、土壌中のアンモニウムイオン (NH4+) を亜硝酸イオン、さらに硝酸イオン (NO3-) へ酸化する働きを何というか？", "硝化（亜硝酸菌・硝酸菌による）",
         ["脱窒", "窒素固定", "窒素同化"], "好気性の化学合成細菌である亜硝酸菌・硝酸菌が硝化を行い、植物が吸収しやすい NO3- を作る。"),
        (2, "生態系における「物質」と「エネルギー」の移動の決定的な違いとして正しい説明は？",
         "物質（炭素・窒素等）は生態系内を循環するが、エネルギーは熱として逃げるため循環しない",
         ["エネルギーは太陽に循環して戻るが、物質は消滅する", "物質もエネルギーも生産者で消滅し循環しない", "物質は一方向にのみ流れ、エネルギーだけが循環する"],
         "太陽から入った光エネルギーは化学エネルギーを経て最終的に熱エネルギーとして宇宙へ放散されるため一方向流である。"),
        (2, "ある生態系の中で、個体数や現存量はそれほど多くないにもかかわらず、取り除かれると群集全体の種多様性やバランスが激変する種を何というか？", "キーストーン種",
         ["先駆種", "指標生物", "固有種"], "岩礁海岸のヒトデ（ウニやイガイの独占を防ぎ多様性を維持）やラッコなどが代表例。"),
        (2, "水銀や DDT・PCB などの分解・排出されにくい有害物質が、食物連鎖の上位の栄養段階に行くほど高濃度に蓄積される現象を何というか？", "生物濃縮",
         ["富栄養化", "相利共生", "種間競争"], "水俣病のメチル水銀や、高次捕食者に多く蓄積される化学物質の例が典型。"),
        (2, "湖沼や内湾に生活排水・肥料中の窒素やリンが大量に流入し、植物プランクトンが異常増殖（アオコや赤潮）する現象は？", "富栄養化",
         ["砂漠化", "酸性雨", "生物濃縮"], "大量のプランクトンの死骸を分解する細菌が溶存酸素を消費し尽くし、魚介類が窒息死する原因になる。"),
        (2, "生物多様性の保全における「3つのレベルの多様性」の正しい組み合わせは？",
         "遺伝子の多様性・種の多様性・生態系の多様性",
         ["細胞の多様性・器官の多様性・個体の多様性", "生産者・消費者・分解者の多様性", "陸上・海洋・大気の多様性"],
         "生物多様性条約でも、種内変異（遺伝子）、多様な種、多様な生息環境（生態系）の3レベルで定義されている。"),
        (3, "国際的な湿地および水鳥の保全を目的として採択された条約（日本では釧路湿原や琵琶湖などが登録）はどれか？", "ラムサール条約",
         ["ワシントン条約", "モントリオール議定書", "バーゼル条約"],
         "ラムサール条約＝湿地保全、ワシントン条約 (CITES)＝絶滅危惧動植物の国際取引規制、モントリオール議定書＝フロン規制（オゾン層）。"),
        (3, "森林面積が一定の生産者が、1年間に光合成によって生産した有機物の総量（総生産量）から、生産者自身の呼吸消費量を差し引いた値を何というか？", "純生産量",
         ["成長量", "被食量", "現存量"],
         "純生産量 = 総生産量 - 呼吸量。さらに純生産量から被食量と枯死量を引いたものがその年の「成長量」になる。"),
    ]
    for diff, q, ans, dist, exp in s4_mc:
        qb.add_mc(sid, uid, diff, q, ans, dist, exp)

    s4_writes = [
        (1, "遷移が進んで環境とつり合いがとれ、大きな変化が見られなくなった最終的な安定状態を何というか？", "極相",
         "クライマックスとも呼び、日本では一般に陰樹林が極相となる。", ["クライマックス", "極相林"]),
        (1, "植物において、見かけの光合成速度が 0（光合成による CO2 吸収速度 ＝ 呼吸による CO2 放出速度）となる光の強さを何というか？", "光補償点",
         "光補償点より弱い光では植物は成長できず、やがて枯れてしまう。", ["補償点"]),
        (1, "光の強さをある値以上に強くしても光合成速度がそれ以上増加しなくなるときの光の強さを何というか？", "光飽和点",
         "光以外の要因（CO2濃度や温度など）が律速となる限界点を光飽和点という。", ["飽和点"]),
        (1, "気温と降水量によって決まる、ある地域の植物群系とそこに生息する動物を含めた生物群集の大きなまとまりを何というか？", "バイオーム",
         "生物群系とも呼ばれ、熱帯多雨林・照葉樹林・サバンナ・ツンドラなどが含まれる。", ["生物群系"]),
        (1, "生態系内で無機物（CO2 と水）から光合成などによって有機物を合成する生物群（植物・藻類など）を何というか？", "生産者",
         "独立栄養生物は生産者、他の生物を食べる動物は消費者、遺骸や排出物を無機物に分解する菌類・細菌は分解者。", None),
        (2, "窒素循環において、嫌気的条件下で土壌中の硝酸イオン (NO3-) を窒素ガス (N2) へ還元して大気中に戻す細菌を何というか？", "脱窒菌",
         "脱窒菌の働きにより、窒素は再び大気中の N2 へと還る。", None),
        (2, "ある森林で、生産者の総生産量が 20 t/(ha・年)、呼吸量が 12 t/(ha・年) であった。純生産量は何 t/(ha・年) か（数値のみ）？", "8",
         "純生産量 = 総生産量 - 呼吸量 = 20 - 12 = 8 t/(ha・年)。", None),
        (2, "上の純生産量 8 t/(ha・年) の森林で、植食性動物による被食量が 1.5、枯死・落葉量が 3.5 のとき、植物の成長量は何 t/(ha・年) か？", "3",
         "成長量 = 純生産量 - (被食量 + 枯死量) = 8 - (1.5 + 3.5) = 3.0。", ["3.0"]),
        (2, "日本の垂直分布において、標高の高い高山帯（森林限界より上）に見られる背の低い常緑針葉低木は？", "ハイマツ",
         "強風と積雪に適応して地上を這うように生育するハイマツのお花畑などが見られる。", None),
        (2, "沖縄や奄美などの亜熱帯の河口域（汽水域）に発達する、マングローブ林の代表的な樹木群（オヒルギなど）を総称して何という群落（〇〇林）という？", "マングローブ林",
         "熱帯・亜熱帯の潮間帯に成立する常緑林をマングローブ林という。", ["マングローブ", "ヒルギ"]),
        (2, "絶滅のおそれのある野生生物の種を調査し、リスト化してまとめた資料（国際自然保護連合 IUCN や環境省が作成）を何というか？", "レッドデータブック",
         "絶滅危惧種の生息状況等をまとめた本をレッドデータブック（リストをレッドリスト）という。", ["レッドリスト"]),
        (3, "二酸化硫黄 (SO2) や窒素酸化物 (NOx) が大気中の水分と反応し、通常より低い pH（目安として pH 5.6 未満）となって降る雨を何というか？", "酸性雨",
         "大気中の CO2 が溶けただけの自然な雨でも pH 5.6 程度のため、pH 5.6 未満の降水を酸性雨と定義する。", None),
        (2, "人間の活動によって本来の生息地以外の地域へ持ち込まれた生物のうち、在来種を捕食するなど生態系に大きな悪影響を及ぼす恐れがあり法律で飼育等が規制される種は？", "特定外来生物",
         "外来生物法により指定されるオオクチバス、アライグマ、ヒアリなどを特定外来生物という。", ["外来生物"]),
        (2, "オゾン層を破壊する主な原因物質であり、モントリオール議定書によって国際的に生産・使用が規制された化学物質の総称は？", "フロン",
         "クロロフルオロカーボン (CFC) などのフロン類が成層圏で塩素ラジカルを生じオゾンを破壊する。", ["フロン類", "CFC"]),
    ]
    for diff, q, ans, exp, alt in s4_writes:
        qb.add_write(sid, uid, diff, q, ans, exp, alt=alt)

    # ○× (10問) -> 18 + 14 + 10 = 42問!
    s4_ox = [
        (1, "陽樹林から極相の陰樹林へ遷移が進むと、一般に森の中の地面（林床）はより明るくなる。", False,
         "木々が密生して上層を覆うようになるため林床は暗くなり、陽樹の幼木は育ちにくくなる。"),
        (1, "土壌や枯れ葉の中に含まれる有機物を分解する菌類や細菌は、生態系において「分解者」の役割を担う。", True,
         "菌類・細菌やミミズ・トビムシ等の土壌動物が有機物を分解し、最終的に無機物に戻して生産者に再利用させる。"),
        (2, "同じ緯度であっても、標高が約 100 m 上がるごとに気温は約 0.6℃ 下がるため、植生が垂直方向に変化する（垂直分布）。", True,
         "低地から山頂に向かって照葉樹林 → 夏緑樹林 → 針葉樹林 → 高山帯（ハイマツ・お花畑）と変化する。"),
        (2, "植物の根と菌根菌（菌類）が栄養をやり取りしたり、マメ科植物と根粒菌が共生したりする関係は「相利共生」である。", True,
         "双方が利益を得る共生関係を相利共生という。"),
        (2, "エネルギーピラミッドや生産力ピラミッドは、栄養段階が上位になるにつれて必ず小さく（上に向かって細く）なる。", True,
         "個体数ピラミッド（1本の大木に多数の昆虫がつく等）や現存量ピラミッドは逆転することがあるが、一定時間あたりのエネルギー量（生産力）は決して逆転しない。"),
        (2, "窒素固定細菌は、大気中の窒素 (N2) をそのままの形で植物の葉から吸収させている。", False,
         "植物は N2 を直接利用できないため、窒素固定細菌が NH4+ に変換し、さらに硝化されて NO3- などとして根から吸収される。"),
        (2, "ある河川に大量の有機排水が流れ込むと、分解細菌の呼吸によって水中の溶存酸素が急激に増加する。", False,
         "有機物を分解する好気性細菌が大量に酸素を消費するため、溶存酸素は急激に「減少」する（BOD が上昇する）。"),
        (2, "ワシントン条約は、絶滅のおそれのある野生動植物の「国際取引（輸出入）」を規制するための条約である。", True,
         "絶滅危惧種の商業取引を制限・禁止することで種の保全を図る条約である。"),
        (3, "「見かけの光合成速度」とは、光合成によって実際に作られた総量（真の光合成速度）から呼吸速度を差し引いた値である。", True,
         "外から測定できる CO2 吸収量が見かけの光合成速度であり、真の光合成速度 ＝ 見かけの光合成速度 ＋ 呼吸速度。"),
        (2, "大気中の二酸化炭素濃度はここ数十年変化しておらず、産業革命以前と同じ 0.028% のまま一定である。", False,
         "化石燃料の大量消費や森林伐採により産業革命前の約 0.028% (280 ppm) から 0.04% (420 ppm) 超へと急増している。"),
    ]
    for diff, q, is_t, exp in s4_ox:
        qb.add_ox(sid, uid, diff, q, is_t, exp)


# ============================================================
# メインエントリーポイントおよび厳格な自己検証
# ============================================================

def generate() -> list[dict]:
    """全7科目の高品質問題を生成してリストで返す。"""
    qb = QuestionBank(seed=20261115)
    generate_math1(qb)
    generate_mathA(qb)
    generate_math2(qb)
    generate_mathB(qb)
    generate_mathC(qb)
    generate_kagaku(qb)
    generate_seibutsu(qb)
    return qb.build()


if __name__ == "__main__":
    questions = generate()

    # 期待される科目と全単元IDのマッピング（data/subjects.json準拠）
    expected_units = {
        "math1": ["math1-u1", "math1-u2", "math1-u3", "math1-u4", "math1-u5"],
        "mathA": ["mathA-u1", "mathA-u2", "mathA-u3"],
        "math2": ["math2-u1", "math2-u2", "math2-u3", "math2-u4", "math2-u5", "math2-u6"],
        "mathB": ["mathB-u1", "mathB-u2"],
        "mathC": ["mathC-u1", "mathC-u2"],
        "kagaku": ["kagaku-u1", "kagaku-u2", "kagaku-u3"],
        "seibutsu": ["seibutsu-u1", "seibutsu-u2", "seibutsu-u3", "seibutsu-u4"],
    }

    ids = [q["id"] for q in questions]
    q_texts = [q["question"] for q in questions]
    assert len(ids) == len(set(ids)), "IDに重複があります！"
    assert len(q_texts) == len(set(q_texts)), "問題文(question)に重複があります！"

    by_subj: dict[str, list[dict]] = {s: [] for s in expected_units}
    for q in questions:
        assert q["subjectId"] in expected_units, f"未知の subjectId: {q['subjectId']}"
        assert q["unitId"] in expected_units[q["subjectId"]], f"不正な unitId: {q['unitId']}"
        assert q["type"] in {"選択", "記述", "○×"}, f"不正な type: {q['type']}"
        assert q["difficulty"] in {1, 2, 3}, f"不正な difficulty: {q['difficulty']}"
        assert isinstance(q["explanation"], str) and len(q["explanation"]) > 0, f"解説が空です: {q['id']}"
        if q["type"] == "選択":
            choices = q.get("choices")
            assert isinstance(choices, list) and len(choices) == 4, f"選択問題の選択肢が4つではありません: {q['id']}"
            assert len(set(choices)) == 4, f"選択肢に重複があります: {q['id']} {choices}"
            assert q["answer"] in choices, f"選択肢に正解が含まれていません: {q['id']}"
        else:
            assert "choices" not in q, f"選択問題以外に choices が含まれています: {q['id']}"
            if q["type"] == "○×":
                assert q["answer"] in {"○", "×"}, f"○×の答えが不正です: {q['id']}"
        by_subj[q["subjectId"]].append(q)

    print(f"総問題数: {len(questions)} 問")
    for sid, units in expected_units.items():
        items = by_subj[sid]
        assert 150 <= len(items) <= 200, f"{sid} の問題数が 150..200 の範囲外です: {len(items)}"
        u_counts = Counter(q["unitId"] for q in items)
        t_counts = Counter(q["type"] for q in items)
        d_counts = Counter(q["difficulty"] for q in items)
        for u in units:
            assert u_counts[u] > 0, f"単元 {u} の問題数が 0 です"
        print(
            f"  {sid:8s}: {len(items):3d} 問 | 単元={dict(u_counts)} | "
            f"形式={dict(t_counts)} | 難易度={dict(sorted(d_counts.items()))}"
        )
    print("すべての自己アサーションに合格しました。")
