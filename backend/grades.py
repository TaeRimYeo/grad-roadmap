"""
평점(GPA)·취득학점 계산 로직.

이 파일은 diagnose.py 처럼 DB·FastAPI 를 import 하지 않는 순수 함수만 둡니다.
(DB 에서 이수 내역을 읽는 일은 routers/grades.py 가 합니다.)

[규칙]
    - 4.5 만점: A+ 4.5, A0 4.0, B+ 3.5, B0 3.0, C+ 2.5, C0 2.0, D+ 1.5, D0 1.0, F 0
    - P(패스)와 성적 없음(None)  : 평점 계산에서 제외, 취득학점에는 포함
    - F                         : 평점에는 0점으로 포함, 취득학점·진단 이수에서는 제외 (= 다시 들어야 함)

[평점 계산식]
    평점 = Σ(성적 점수 × 학점) / Σ(평점에 들어가는 과목의 학점)

    예) A+ 3학점, F 2학점, P 2학점
        → (4.5×3 + 0×2) / (3 + 2) = 13.5 / 5 = 2.7    (P 는 분모·분자 모두에서 빠짐)
        → 취득학점 = 3 + 2(P) = 5                      (F 는 빠짐)

[입력 모양] 이수 과목 하나
    {"credits": 3, "category": "전공선택", "grade": "A+", "taken_year": 1, "taken_semester": "1"}
"""

from decimal import ROUND_HALF_UP, Decimal

# 성적 → 점수. 여기 없는 성적(P, None)은 평점 계산에서 빠집니다.
GRADE_POINTS = {
    "A+": 4.5,
    "A0": 4.0,
    "B+": 3.5,
    "B0": 3.0,
    "C+": 2.5,
    "C0": 2.0,
    "D+": 1.5,
    "D0": 1.0,
    "F": 0.0,
}

# 입력으로 받을 수 있는 성적 전체 (점수 있는 성적 + P)
VALID_GRADES = (*GRADE_POINTS, "P")

FAIL_GRADE = "F"

# 전공 평점·전공 학점에 들어가는 이수구분
MAJOR_CATEGORIES = ("전공필수", "전공선택")

# 이수구분별 학점에서 교양필수·교양선택은 '교양' 하나로 합칩니다.
CATEGORY_GROUPS = {
    "전공필수": "전공필수",
    "전공선택": "전공선택",
    "교양필수": "교양",
    "교양선택": "교양",
}

# 학기 정렬 순서: 1학기 → 여름 → 2학기 → 겨울 (같은 학년 안에서 실제로 들은 순서)
SEMESTER_ORDER = {"1": 1, "여름": 2, "2": 3, "겨울": 4}


# =========================================================================
# 작은 도우미 함수
# =========================================================================


def _round2(value: float) -> float:
    """
    소수 둘째 자리 반올림 (사사오입).

    파이썬 기본 round() 는 3.875 같은 값을 3.87 로 내리는 경우가 있습니다.
    (컴퓨터가 3.875 를 3.87499999... 처럼 저장하는 경우 + '짝수 쪽으로 반올림' 규칙 때문)
    성적표처럼 정확히 사사오입해야 하므로 Decimal 로 계산합니다.
    """
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def is_passed(grade: str | None) -> bool:
    """이수로 인정되는지. F 만 아니면 인정합니다 (성적 모름·P 도 인정)."""
    return grade != FAIL_GRADE


def term_sort_key(year: int, semester: str) -> tuple[int, int]:
    """(학년, 학기) 정렬 기준. sorted(..., key=...) 에 씁니다."""
    return (year, SEMESTER_ORDER.get(semester, 99))


# =========================================================================
# 평점 / 취득학점
# =========================================================================


def calc_gpa(items: list[dict]) -> float | None:
    """
    평점 계산. 평점에 들어가는 과목(점수 있는 성적)이 하나도 없으면 None.
    (0.0 으로 돌려주면 '평점 0점' 과 '아직 계산할 성적이 없음' 이 구분되지 않음)
    """
    point_sum = 0.0
    credit_sum = 0
    for item in items:
        point = GRADE_POINTS.get(item.get("grade"))
        if point is None:
            continue  # P 또는 성적 없음 → 평점에서 제외
        point_sum += point * item["credits"]
        credit_sum += item["credits"]

    if credit_sum == 0:
        return None
    return _round2(point_sum / credit_sum)


def earned_credits(items: list[dict]) -> int:
    """취득학점 합계. F 는 빼고, P·성적 없음은 포함합니다."""
    return sum(item["credits"] for item in items if is_passed(item.get("grade")))


# =========================================================================
# 메인 함수: 학점 요약
# =========================================================================


def summarize(items: list[dict]) -> dict:
    """
    GET /api/grades/summary 응답 전체를 만듭니다.

        gpa            : 전체 평점
        major_gpa      : 전공(전공필수+전공선택) 평점
        earned_credits : 취득학점 합계
        by_category    : 이수구분별 취득학점 {"전공필수", "전공선택", "교양"}
        terms          : 학기별 평점·취득학점 (학년·학기 순)
    """
    major_items = [item for item in items if item["category"] in MAJOR_CATEGORIES]

    # ---- 이수구분별 취득학점 (F 제외) ----
    by_category = {"전공필수": 0, "전공선택": 0, "교양": 0}
    for item in items:
        group = CATEGORY_GROUPS.get(item["category"])
        if group and is_passed(item.get("grade")):
            by_category[group] += item["credits"]

    # ---- 학기별로 묶기 ----
    # (학년, 학기) → 그 학기에 들은 과목 목록
    by_term: dict[tuple[int, str], list[dict]] = {}
    for item in items:
        by_term.setdefault((item["taken_year"], item["taken_semester"]), []).append(item)

    terms = [
        {
            "year": year,
            "semester": semester,
            "gpa": calc_gpa(term_items),
            "earned_credits": earned_credits(term_items),
        }
        for (year, semester), term_items in sorted(by_term.items(), key=lambda kv: term_sort_key(*kv[0]))
    ]

    return {
        "gpa": calc_gpa(items),
        "major_gpa": calc_gpa(major_items),
        "earned_credits": earned_credits(items),
        "by_category": by_category,
        "terms": terms,
    }
