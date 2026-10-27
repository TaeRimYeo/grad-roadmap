"""
학기별 수강 로드맵 솔버 (Google OR-Tools CP-SAT).

[CP-SAT 이란? (초보자용)]
    "이런 변수들이 있고, 이런 조건(제약)을 다 지켜야 하고, 이 점수(목적함수)를 가장 작게 하고 싶다"
    라고 적어주면, 조건을 모두 만족하는 답 중 점수가 가장 좋은 답을 찾아주는 도구입니다.
    우리는 답을 찾는 방법을 직접 짜지 않고 '문제'만 정확하게 적습니다.

[변수]
    x[c][t]  : 과목 c 를 학기 t 에 들으면 1, 아니면 0       (BoolVar = 0 또는 1 만 가지는 변수)
    used[t]  : 학기 t 에 학교를 다니면 1
    last[t]  : 학기 t 가 본인의 마지막 학기이면 1  (= used[t] - used[t+1])
    L[t]     : 학기 t 의 총 학점 (= Σ 학점 × x[c][t])

    학기 번호 t : 1학년 1학기 = 1, ..., 3학년 2학기 = 6 (regular_terms), 7·8 = 졸업유예 추가학기
    홀수 t 는 1학기, 짝수 t 는 2학기 입니다.

[목적함수 — 우선순위를 가중치로 표현]
    1. 학기 수 최소 (Σ used)
    2. 가상 과목 '학점 합' 최소 (실제 과목으로 채울 수 있으면 실제 과목 우선)
       - '개수' 가 아니라 '학점' 인 이유: 개수로 세면 초과 학점 1을 아끼려고
         정규 과목(수리능력 2학점)을 빼고 가상 교양(3학점)을 넣는 일이 생깁니다.
         학과 시간표 과목을 빼는 것보다 1학점 더 듣는 편이 학생에게 낫습니다.
    3. 가상 과목을 쓰는 계획이라면, 빠진 실제 과목 학점 최소
       - 2순위만으로는 "실제 109 + 가상 2 = 111" 과 "창업실무(1) 빼고 108 + 가상 2 = 110" 이
         가상 학점(2)이 같아 구분되지 않고, 4순위(초과 학점)가 창업실무를 빼는 쪽을 고릅니다.
       - 가상 과목이 하나도 없는 계획에는 적용하지 않습니다. (그때는 4순위대로 필요한 만큼만 들음)
    4. 초과 학점 최소 (필요 이상으로 많이 듣지 않게)
    5. 과목을 권장 학기(term_index)에 가깝게 (Σ |t - term_index|)
    6. 가상 과목 개수 최소 (위가 모두 같을 때만 쓰는 동점 처리용)

    '높은 순위가 1만큼 좋아지는 것' 이 '그보다 낮은 순위가 아무리 좋아지는 것' 보다 크도록 가중치를 정합니다.
        W6 = 1
        W5 = (6순위 최댓값 + 1)
        W4 = W5 × (5순위 최댓값 + 1)
        ...
        W1 = W2 × (2순위 최댓값 + 1)
    이렇게 하면 한 번만 풀어도 단계별로 푼 것과 같은 순서가 지켜집니다.

[불가능할 때 — assumption(가정) 리터럴]
    제약을 묶음별로 "이 스위치(리터럴)가 켜져 있을 때만 지킨다" 로 만들어 두고,
    모든 스위치를 켠 채로 풀게 합니다. 해가 없으면 CP-SAT 이
    "이 스위치들을 동시에 켜면 안 된다" 는 목록(원인)을 알려줍니다.
    그 목록을 한국어 문장으로 바꾸고, 해당 스위치를 끈 뒤 다시 풀어 다른 원인도 찾습니다.

이 파일은 FastAPI·DB 를 import 하지 않는 순수 함수만 둡니다. (diagnose.py 와 같은 원칙)

[입력 모양]
    courses     : 아직 안 들은 과목 (diagnose()["available"] 그대로 넘기면 됨. F 받은 과목도 포함)
                  [{"code", "name", "credits", "category", "offered", "term_index"}, ...]
    prereqs     : [("CM1108", "CM1210"), ...]           # (선수 code, 후수 code)
    done_codes  : 이수 완료한 과목 code 목록
    diagnosis   : diagnose() 의 반환값 그대로
    start_term  : 다음에 들을 학기 번호 (1 ~ 8)
    term_rule   : requirements.json 의 term_credit_rule
"""

from ortools.sat.python import cp_model

from diagnose import MAJOR_CATEGORIES, _eul_reul
from placeholder import make_placeholders

# 정규 학기 뒤에 붙일 수 있는 추가학기(졸업유예) 수. 정규 6 + 추가 2 = 8학기까지 탐색합니다.
MAX_EXTRA_TERMS = 2

# 개설 학기 (courses.csv 의 offered): 1 = 1학기만, 2 = 2학기만, 3 = 양학기
OFFERED_FIRST = 1
OFFERED_SECOND = 2

# 결과가 매번 같도록 고정하는 값
#   작업자(num_workers)를 여러 개 쓰면 '점수가 같은 답' 중 어느 것이 먼저 나오느냐가 실행마다 달라집니다.
#   (실제로 8개로 돌렸을 때 같은 입력에 다른 배치가 나왔음)
#   병렬이면서 결정적인 interleave_search 모드는 신입생 기준 약 4초로 느려서,
#   작업자 1개 + 고정 seed 로 풉니다. 이 경우 신입생도 1초 안쪽에 최적해가 나옵니다.
RANDOM_SEED = 42
NUM_WORKERS = 1
TIME_LIMIT_SECONDS = 10.0

# 원인 찾기를 최대 몇 번 반복할지 (원인 하나 찾을 때마다 그 제약을 풀고 다시 풂)
MAX_REASON_ROUNDS = 6


# =========================================================================
# 작은 도우미 함수
# =========================================================================


def _eun_neun(word: str) -> str:
    """조사 '은' / '는' 을 고릅니다. (받침 판단은 diagnose._eul_reul 을 그대로 활용)"""
    return {"을": "은", "를": "는"}.get(_eul_reul(word), "은(는)")


def _credit(course: dict) -> int:
    """
    학점을 정수로 바꿉니다. CP-SAT 은 정수만 다루기 때문입니다.
    2.5 학점 같은 값이 들어오면 계산이 틀어지므로 바로 알려줍니다.
    """
    value = float(course.get("credits") or 0)
    if not value.is_integer():
        raise ValueError(f"{course.get('name')} 의 학점({value})이 정수가 아닙니다. 솔버는 정수 학점만 지원합니다")
    return int(value)


def _semester_of(term: int) -> int:
    """학기 번호 → 1학기/2학기. 홀수 번호는 1학기, 짝수 번호는 2학기입니다."""
    return OFFERED_FIRST if term % 2 == 1 else OFFERED_SECOND


def term_label(term: int, regular_terms: int) -> str:
    """
    학기 번호를 화면용 이름으로 바꿉니다.

        regular_terms=6 일 때:  1 → 1학년 1학기,  6 → 3학년 2학기,  7 → 추가 1학기,  8 → 추가 2학기
    """
    if term <= regular_terms:
        return f"{(term + 1) // 2}학년 {_semester_of(term)}학기"
    return f"추가 {term - regular_terms}학기"


def _is_open(course: dict, term: int) -> bool:
    """과목이 이 학기에 열리는지. offered 가 1·2 가 아니면(양학기·미정) 제한 없음으로 봅니다."""
    offered = int(course.get("offered") or 0)
    if offered in (OFFERED_FIRST, OFFERED_SECOND):
        return _semester_of(term) == offered
    return True


# =========================================================================
# 모델 만들기
# =========================================================================


class _Plan:
    """
    솔버에 넣을 정리된 입력값 묶음.
    모델을 두 번(최적화용 / 원인 찾기용) 만들기 때문에, 입력 정리는 한 번만 해서 여기에 담아둡니다.
    """

    def __init__(self, courses, prereqs, done_codes, diagnosis, start_term, term_rule):
        self.regular_terms = int(term_rule["regular_terms"])
        self.max_term = self.regular_terms + MAX_EXTRA_TERMS
        if not 1 <= start_term <= self.max_term:
            raise ValueError(f"start_term 은 1 ~ {self.max_term} 사이여야 합니다 (받은 값: {start_term})")
        self.start_term = start_term
        self.terms = list(range(start_term, self.max_term + 1))

        # 학기 학점 규칙 (requirements.json 의 term_credit_rule)
        self.regular_min = int(term_rule["regular"]["min"])
        self.final_min = int(term_rule["final_term"]["min"])
        self.extra_min = int(term_rule["extra_terms"]["min"])
        self.max_credits = int(term_rule["regular"]["max"])

        # ---- 남은 학점 (diagnose 결과에서 그대로 가져옴) ----
        self.missing_required = [m["code"] for m in diagnosis["required"]["missing"]]
        required_remaining = diagnosis["required"]["remaining"]
        major_elective_needed = diagnosis["major_elective_needed"]
        free_needed = diagnosis["free_needed"]
        # 전공학점(전필+전선)으로 채워야 할 학점 / 총학점으로 채워야 할 학점
        self.need_major = required_remaining + major_elective_needed
        self.need_total = required_remaining + major_elective_needed + free_needed

        # ---- 실제 과목 (학점 0 인 과목은 배치할 의미가 없으므로 제외) ----
        self.real = [dict(c, credits=_credit(c), is_placeholder=False) for c in courses if _credit(c) > 0]
        self.real_codes = {c["code"] for c in self.real}
        self.done_codes = set(done_codes)

        # 정규 학기를 전부 다녀야 하는가? (이미 추가학기라면 이 제약은 걸지 않음)
        self.force_regular = start_term <= self.regular_terms

        # ---- 가상 과목 ----
        # 기본은 free_needed 만큼. 다만 "정규 학기를 전부 다녀야 하는데 남은 과목이 너무 적은" 경우
        # 학기마다 최소 학점을 채울 자리가 모자랄 수 있으므로, 모자라는 만큼 더 만듭니다.
        self.placeholders = make_placeholders(max(free_needed, self._min_load() - sum(c["credits"] for c in self.real)))

        self.all_courses = self.real + self.placeholders

        # ---- 선수과목: 이번 계획과 관련 있는 것만 ----
        # 후수과목이 후보에 있고, 선수과목을 아직 이수하지 않은 경우만 제약이 필요합니다.
        self.prereqs = [(a, b) for a, b in prereqs if b in self.real_codes and a not in self.done_codes]

        self.course_by_code = {c["code"]: c for c in self.all_courses}

    def _min_load(self) -> int:
        """앞으로 반드시 들어야 하는 최소 학점 (가상 과목 개수를 정할 때만 사용)"""
        if self.force_regular:
            # 정규 마지막 학기까지 전부 다님: 중간 학기는 regular_min, 마지막 학기는 final_min
            n = self.regular_terms - self.start_term + 1
            return self.regular_min * (n - 1) + self.final_min
        return self.extra_min  # 추가학기라면 최소 한 학기는 다님

    def nothing_left(self) -> bool:
        """더 들을 것이 없는지 (이미 졸업요건을 다 채움)"""
        return self.need_total <= 0 and self.need_major <= 0 and not self.missing_required


def _build_model(plan: _Plan, assumption_keys=None):
    """
    CP-SAT 모델을 만듭니다.

    assumption_keys 가 None 이면 → 모든 제약을 그냥 겁니다. (최적화용)
    assumption_keys 가 집합이면  → 그 안에 든 제약 묶음은 '스위치(리터럴)가 켜졌을 때만' 지키고,
                                   집합에 없는 묶음은 아예 걸지 않습니다. (원인 찾기용)

    돌려주는 값: (model, x, used, switches)
        switches : 제약 묶음 이름 → 스위치 BoolVar
    """
    model = cp_model.CpModel()
    terms = plan.terms
    switches: dict[str, cp_model.IntVar] = {}

    def guard(key: str):
        """
        제약 묶음 key 의 스위치를 돌려줍니다.
            - 최적화용: None (스위치 없이 항상 지킴)
            - 원인 찾기용 & 꺼진 묶음: False (이 제약을 걸지 말라는 뜻)
        """
        if assumption_keys is None:
            return None
        if key not in assumption_keys:
            return False
        if key not in switches:
            switches[key] = model.new_bool_var(key)
        return switches[key]

    def add(constraint_expr, key: str):
        """제약을 추가하되, 원인 찾기용이면 스위치가 켜졌을 때만 지키도록 합니다."""
        lit = guard(key)
        if lit is False:
            return
        ct = model.add(constraint_expr)
        if lit is not None:
            ct.only_enforce_if(lit)

    # ---------------------------------------------------------------------
    # 변수
    # ---------------------------------------------------------------------
    x = {c["code"]: {t: model.new_bool_var(f"x_{c['code']}_{t}") for t in terms} for c in plan.all_courses}
    used = {t: model.new_bool_var(f"used_{t}") for t in terms}
    last = {t: model.new_bool_var(f"last_{t}") for t in terms}

    def take(code):
        """과목을 듣는지 (0 또는 1): 모든 학기의 x 를 더한 값"""
        return sum(x[code][t] for t in terms)

    def term_of(code):
        """과목을 듣는 학기 번호 (안 들으면 0)"""
        return sum(t * x[code][t] for t in terms)

    credits = {t: sum(c["credits"] * x[c["code"]][t] for c in plan.all_courses) for t in terms}

    # ---------------------------------------------------------------------
    # 기본 구조 (항상 지킴 — 이것만으로는 '아무것도 안 듣기' 가 가능하므로 불가능의 원인이 되지 않음)
    # ---------------------------------------------------------------------
    for c in plan.all_courses:
        # 한 과목은 최대 한 번 (전필은 아래에서 '정확히 한 번' 을 따로 겁니다)
        model.add(take(c["code"]) <= 1)
        # 다니지 않는 학기에는 과목을 넣을 수 없음
        for t in terms:
            model.add(x[c["code"]][t] <= used[t])

    for t in terms:
        nxt = used[t + 1] if t + 1 in used else 0
        # 학기는 중간에 비는 학기 없이 연속 사용: used[t+1] ≤ used[t]
        if t + 1 in used:
            model.add(used[t + 1] <= used[t])
        # 마지막 학기 = 이번 학기는 다니고 다음 학기는 안 다님
        model.add(last[t] == used[t] - nxt)

    # 가상 과목 대칭 제거:
    #   '교양 A(3학점)' 와 '교양 C(3학점)' 는 이름만 다를 뿐 똑같은 과목이라
    #   솔버가 둘을 바꿔보는 헛수고를 합니다. 같은 학점끼리는 앞 글자부터, 앞 학기부터 쓰게 고정합니다.
    by_credit: dict[int, list[str]] = {}
    for p in plan.placeholders:
        by_credit.setdefault(p["credits"], []).append(p["code"])
    for codes in by_credit.values():
        for prev, cur in zip(codes, codes[1:]):
            model.add(take(cur) <= take(prev))
            cur_taken = model.new_bool_var(f"taken_{cur}")
            model.add(take(cur) == cur_taken)
            model.add(term_of(cur) >= term_of(prev)).only_enforce_if(cur_taken)

    # ---------------------------------------------------------------------
    # 과목 제약
    # ---------------------------------------------------------------------
    # 남은 전공필수: 정확히 1번
    for code in plan.missing_required:
        add(take(code) == 1, f"required:{code}")

    # 개설학기: 열리지 않는 학기에는 배치 불가 (가상 과목은 제한 없음)
    for c in plan.real:
        closed = [t for t in terms if not _is_open(c, t)]
        if closed:
            add(sum(x[c["code"]][t] for t in closed) == 0, f"offered:{c['code']}")

    # 선수과목:
    #   후수 b 를 t 학기에 들으려면, t 보다 앞선 학기에 선수 a 를 들었어야 함
    #       x[b][t] ≤ Σ_{t' < t} x[a][t']
    #   → a 를 안 듣는 계획이면 오른쪽이 항상 0 이므로 b 도 못 들음
    for a, b in plan.prereqs:
        key = f"prereq:{a}>{b}"
        for t in terms:
            before = sum(x[a][s] for s in terms if s < t) if a in x else 0
            add(x[b][t] <= before, key)

    # ---------------------------------------------------------------------
    # 학기 학점 (docs/솔버_학점제약_메모.md 공식)
    # ---------------------------------------------------------------------
    for t in terms:
        add(credits[t] <= plan.max_credits * used[t], "max_credits")
        if t <= plan.regular_terms:
            # 중간 학기 regular_min(15), 마지막 학기 final_min(10), 미사용 0
            add(
                credits[t] >= plan.regular_min * used[t] - (plan.regular_min - plan.final_min) * last[t],
                "min_credits",
            )
        else:
            # 추가학기는 마지막이든 아니든 extra_min(10)
            add(credits[t] >= plan.extra_min * used[t], "min_credits")

    # 정규 학기는 전부 다님 (조기졸업 없음). 이미 추가학기라면 걸지 않음
    if plan.force_regular:
        for t in terms:
            if t <= plan.regular_terms:
                add(used[t] == 1, "regular_terms")

    # ---------------------------------------------------------------------
    # 졸업 학점
    # ---------------------------------------------------------------------
    major_sum = sum(c["credits"] * take(c["code"]) for c in plan.real if c.get("category") in MAJOR_CATEGORIES)
    total_sum = sum(credits[t] for t in terms)
    add(major_sum >= plan.need_major, "major")
    add(total_sum >= plan.need_total, "total")

    # ---------------------------------------------------------------------
    # 목적함수 (원인 찾기용에는 필요 없음 — '해가 있느냐' 만 보면 됨)
    # ---------------------------------------------------------------------
    if assumption_keys is None:
        # 5순위: 권장 학기와의 거리. t 와 term_index 가 모두 상수라서 |t - term_index| 도 그냥 숫자입니다.
        distance = 0
        distance_max = 0
        for c in plan.real:
            ti = c.get("term_index")
            if not ti:
                continue
            gaps = {t: abs(t - int(ti)) for t in terms}
            distance += sum(gaps[t] * x[c["code"]][t] for t in terms)
            distance_max += max(gaps.values())

        # 4순위: 초과 학점. total_sum - need_total 이지만 상수(need_total)는 순위에 영향이 없으므로 뺍니다.
        excess_max = sum(c["credits"] for c in plan.all_courses)

        # 3순위: 가상 과목을 쓰는 계획에서 빠진 실제 과목 학점
        #   any_ph   : 가상 과목을 하나라도 쓰면 1 (가상 과목마다 any_ph ≥ take 이므로, 쓰면 반드시 1)
        #   dropped  : 가상 과목을 쓰는데 이 실제 과목은 안 들으면 1  (dropped ≥ any_ph - take)
        #   가상 과목을 안 쓰면 any_ph 를 0 으로 두는 편이 점수가 좋으므로 솔버가 알아서 0 으로 둡니다.
        any_ph = model.new_bool_var("any_placeholder")
        for p in plan.placeholders:
            model.add(any_ph >= take(p["code"]))
        dropped_credits = 0
        for c in plan.real:
            dropped = model.new_bool_var(f"dropped_{c['code']}")
            model.add(dropped >= any_ph - take(c["code"]))
            dropped_credits += c["credits"] * dropped
        dropped_max = sum(c["credits"] for c in plan.real)

        # 2순위: 가상 과목 학점 합
        placeholder_credits = sum(p["credits"] * take(p["code"]) for p in plan.placeholders)
        placeholder_credits_max = sum(p["credits"] for p in plan.placeholders)
        # 6순위: 가상 과목 개수 (동점 처리용)
        placeholder_count = sum(take(p["code"]) for p in plan.placeholders)
        placeholder_max = len(plan.placeholders)

        w5 = placeholder_max + 1
        w4 = w5 * (distance_max + 1)
        w3 = w4 * (excess_max + 1)
        w2 = w3 * (dropped_max + 1)
        w1 = w2 * (placeholder_credits_max + 1)
        model.minimize(
            w1 * sum(used.values())
            + w2 * placeholder_credits
            + w3 * dropped_credits
            + w4 * total_sum
            + w5 * distance
            + placeholder_count
        )

    return model, x, used, switches


# =========================================================================
# 불가능 원인 → 한국어 문장
# =========================================================================


def _range_text(plan: _Plan, terms: list[int]) -> str:
    """'남은 2개 학기(3학년 1학기~3학년 2학기)' 같은 문구"""
    first = term_label(terms[0], plan.regular_terms)
    if len(terms) == 1:
        return f"남은 1개 학기({first})"
    return f"남은 {len(terms)}개 학기({first}~{term_label(terms[-1], plan.regular_terms)})"


def _explain(plan: _Plan, core: set[str]) -> list[str]:
    """
    CP-SAT 이 알려준 '동시에 지킬 수 없는 제약 묶음(core)' 을 사람이 읽을 문장으로 바꿉니다.
    규칙으로만 만들며, 어떤 묶음 조합이냐에 따라 문장을 고릅니다.
    """
    name = {code: c["name"] for code, c in plan.course_by_code.items()}
    span = _range_text(plan, plan.terms)
    messages = []
    explained = set()

    # ---- 전공필수 과목이 왜 못 들어가는가 ----
    for key in sorted(k for k in core if k.startswith("required:")):
        code = key.split(":", 1)[1]
        n = name[code]
        if f"offered:{code}" in core:
            sem = int(plan.course_by_code[code]["offered"])
            if not any(_semester_of(t) == sem for t in plan.terms):
                messages.append(f"{n}{_eun_neun(n)} {sem}학기에만 열리는데 {span}에는 {sem}학기가 없습니다")
            else:
                messages.append(f"{n}{_eun_neun(n)} {sem}학기에만 열려서 {span} 안에 배치할 수 없습니다")
            explained |= {key, f"offered:{code}"}
        for a, b in plan.prereqs:
            pkey = f"prereq:{a}>{b}"
            if b == code and pkey in core:
                an = name.get(a, a)
                if a not in plan.real_codes:
                    messages.append(f"{n}{_eun_neun(n)} {an}{_eul_reul(an)} 먼저 들어야 하는데 {an}{_eul_reul(an)} 들을 수 없습니다")
                else:
                    messages.append(
                        f"{n}{_eun_neun(n)} {an}{_eul_reul(an)} 먼저 들어야 하는데 {span} 안에서 순서대로 들을 수 없습니다"
                    )
                explained |= {key, pkey, f"required:{a}", f"offered:{a}", f"offered:{b}"}

    # ---- 학점이 모자람 ----
    if "total" in core:
        most = len(plan.terms) * plan.max_credits
        messages.append(
            f"{span} 안에 남은 {plan.need_total}학점을 채울 수 없습니다 (한 학기 최대 {plan.max_credits}학점 → 최대 {most}학점)"
        )
        explained |= {"total", "max_credits"}
    if "major" in core:
        # 남은 학기 중 한 번이라도 열리는 전공 과목의 학점 합계
        open_major = sum(
            c["credits"]
            for c in plan.real
            if c.get("category") in MAJOR_CATEGORIES and any(_is_open(c, t) for t in plan.terms)
        )
        if open_major < plan.need_major:
            detail = f"이 기간에 열리는 전공 과목은 모두 합쳐 {open_major}학점입니다"
        else:
            detail = f"한 학기 최대 {plan.max_credits}학점"
        messages.append(f"{span} 안에 남은 전공 {plan.need_major}학점을 채울 수 없습니다 ({detail})")
        explained |= {"major", "max_credits"}
    if "total" in core or "major" in core:
        # 학점이 모자란 경우, 함께 딸려 나온 '일반 과목의 개설학기·선수과목' 묶음은
        # "그 과목들을 이 기간에 못 들어서 학점이 모자란다" 는 같은 이야기이므로 따로 적지 않습니다.
        explained |= {k for k in core if k.startswith(("offered:", "prereq:"))}
    if "regular_terms" in core and "min_credits" in core:
        messages.append(
            f"정규 {plan.regular_terms}학기를 모두 다녀야 하는데, 학기마다 최소 {plan.regular_min}학점을 채울 과목이 부족합니다"
        )
        explained |= {"regular_terms", "min_credits"}

    # ---- 위 규칙에 안 걸린 나머지 (드문 경우) ----
    leftover = sorted(core - explained - {"max_credits", "min_credits"})
    if leftover or not messages:
        labels = []
        for key in leftover:
            kind, _, rest = key.partition(":")
            if kind == "offered":
                labels.append(f"{name[rest]} 개설학기")
            elif kind == "prereq":
                a, b = rest.split(">")
                labels.append(f"{name.get(a, a)} → {name[b]} 선수과목 순서")
            elif kind == "required":
                labels.append(f"전공필수 {name.get(rest, rest)}")
            else:
                labels.append({"regular_terms": f"정규 {plan.regular_terms}학기 이수"}.get(key, key))
        if not labels:
            labels = ["학기별 최소·최대 학점"]
        messages.append("다음 조건을 동시에 만족할 수 없습니다: " + ", ".join(labels))
    return messages


def _find_reasons(plan: _Plan) -> list[str]:
    """
    불가능한 원인을 찾습니다.

    1) 모든 제약 묶음의 스위치를 켜고 풀기 → CP-SAT 이 '충돌하는 스위치 목록' 을 돌려줌
    2) 그 목록을 문장으로 바꾸고, 해당 묶음을 빼고 다시 풀기
    3) 해가 생길 때까지(또는 MAX_REASON_ROUNDS 번) 반복 → 서로 다른 원인을 모두 모음
    """
    # 첫 판: 모든 묶음 켜기. 이름 목록을 얻기 위해 일단 '전부 포함' 으로 한 번 만듭니다.
    _, _, _, switches = _build_model(plan, assumption_keys=_AllKeys())
    active = set(switches)
    reasons: list[str] = []

    for _ in range(MAX_REASON_ROUNDS):
        model, _, _, switches = _build_model(plan, assumption_keys=active)
        # 스위치 이름 순서대로 넣어야 원인 목록이 매번 같게 나옵니다.
        model.add_assumptions([switches[k] for k in sorted(switches)])

        solver = cp_model.CpSolver()
        # 원인 목록(core)은 작업자 1개일 때 안정적으로 나옵니다.
        solver.parameters.num_workers = 1
        solver.parameters.random_seed = RANDOM_SEED
        solver.parameters.max_time_in_seconds = TIME_LIMIT_SECONDS
        status = solver.solve(model)
        if status != cp_model.INFEASIBLE:
            break

        index_to_key = {v.index: k for k, v in switches.items()}
        core = {index_to_key[i] for i in solver.sufficient_assumptions_for_infeasibility() if i in index_to_key}
        if not core:
            break
        for msg in _explain(plan, core):
            if msg not in reasons:
                reasons.append(msg)
        active -= core

    return reasons or ["조건을 모두 만족하는 계획이 없습니다"]


class _AllKeys:
    """모든 key 를 '들어 있음' 으로 대답하는 집합 흉내. (제약 묶음 이름을 처음 모을 때 사용)"""

    def __contains__(self, key):
        return True


# =========================================================================
# 메인 함수
# =========================================================================


def solve_roadmap(
    courses: list[dict],
    prereqs: list,
    done_codes,
    diagnosis: dict,
    start_term: int,
    term_rule: dict,
) -> dict:
    """
    남은 과목을 start_term 부터 학기별로 배치합니다.

    돌려주는 값:
        {"feasible": True, "terms": [{"term": 5, "label": "3학년 1학기", "credits": 18,
                                      "courses": [{"code", "name", "credits", "category", "is_placeholder"}]}],
         "total_terms": 2, "placeholder_count": 3, "reasons": []}
    """
    plan = _Plan(courses, prereqs, done_codes, diagnosis, start_term, term_rule)

    # 이미 졸업요건을 다 채웠다면 풀 필요 없음
    if plan.nothing_left():
        return {"feasible": True, "terms": [], "total_terms": 0, "placeholder_count": 0, "reasons": []}

    # 남은 전필이 과목 목록(courses)에 아예 없으면 배치할 방법이 없음 → 모델을 만들기 전에 알려줌
    absent = [m["name"] for m in diagnosis["required"]["missing"] if m["code"] not in plan.real_codes]
    if absent:
        reasons = [f"전공필수 {n}{_eun_neun(n)} 들을 수 있는 과목 목록에 없습니다" for n in absent]
        return {"feasible": False, "terms": [], "total_terms": 0, "placeholder_count": 0, "reasons": reasons}

    model, x, used, _ = _build_model(plan)

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = RANDOM_SEED
    solver.parameters.num_workers = NUM_WORKERS
    solver.parameters.max_time_in_seconds = TIME_LIMIT_SECONDS
    status = solver.solve(model)

    if status == cp_model.INFEASIBLE:
        return {"feasible": False, "terms": [], "total_terms": 0, "placeholder_count": 0, "reasons": _find_reasons(plan)}
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # 제한시간 안에 답을 하나도 찾지 못함 (불가능하다고 증명된 것은 아님)
        return {
            "feasible": False,
            "terms": [],
            "total_terms": 0,
            "placeholder_count": 0,
            "reasons": [f"{TIME_LIMIT_SECONDS:g}초 안에 계획을 찾지 못했습니다"],
        }

    # ---- 답 읽기 ----
    result_terms = []
    placeholder_count = 0
    for t in plan.terms:
        if not solver.value(used[t]):
            continue
        picked = [c for c in plan.all_courses if solver.value(x[c["code"]][t])]
        # 실제 과목 먼저(code 순), 가상 과목은 뒤에
        picked.sort(key=lambda c: (c["is_placeholder"], c["code"]))
        placeholder_count += sum(1 for c in picked if c["is_placeholder"])
        result_terms.append(
            {
                "term": t,
                "label": term_label(t, plan.regular_terms),
                "credits": sum(c["credits"] for c in picked),
                "courses": [
                    {
                        "code": c["code"],
                        "name": c["name"],
                        "credits": c["credits"],
                        "category": c.get("category"),
                        "is_placeholder": c["is_placeholder"],
                    }
                    for c in picked
                ],
            }
        )

    return {
        "feasible": True,
        "terms": result_terms,
        "total_terms": len(result_terms),
        "placeholder_count": placeholder_count,
        "reasons": [],
    }
