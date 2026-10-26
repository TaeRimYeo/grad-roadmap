"""
평점·취득학점 계산(grades.py) 테스트.

grades.py 는 순수 함수라서 DB 없이 dict 만 넣어서 테스트합니다.
"""

import os
import sys

# backend/ 폴더를 import 경로에 추가 (conftest.py 와 같은 이유)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from grades import calc_gpa, earned_credits, summarize  # noqa: E402


def _item(credits, grade, category="전공선택", year=1, semester="1"):
    """테스트용 이수 과목 한 개를 만드는 도우미."""
    return {
        "credits": credits,
        "category": category,
        "grade": grade,
        "taken_year": year,
        "taken_semester": semester,
    }


# =========================================================================
# calc_gpa / earned_credits
# =========================================================================


def test_gpa_basic():
    """A+ 3학점, B0 2학점 → (4.5×3 + 3.0×2) / 5 = 3.9"""
    assert calc_gpa([_item(3, "A+"), _item(2, "B0")]) == 3.9


def test_gpa_excludes_pass():
    """P 는 평점 계산에서 빠짐 (분모에도 안 들어감)"""
    assert calc_gpa([_item(3, "A0"), _item(2, "P")]) == 4.0


def test_gpa_excludes_no_grade():
    """성적 없음(None) 도 평점 계산에서 빠짐"""
    assert calc_gpa([_item(3, "B+"), _item(3, None)]) == 3.5


def test_gpa_includes_f_as_zero():
    """F 는 평점에 0점으로 들어감: (4.5×3 + 0×2) / 5 = 2.7"""
    assert calc_gpa([_item(3, "A+"), _item(2, "F")]) == 2.7


def test_gpa_rounding_half_up():
    """
    소수 둘째 자리 사사오입: (4.5×3 + 3.5×3 + 3.5×2) / 8 = 31.0 / 8 = 3.875 → 3.88
    (파이썬 기본 round(3.875, 2) 는 3.88 이 아닐 수 있어서 따로 확인)
    """
    assert calc_gpa([_item(3, "A+"), _item(3, "B+"), _item(2, "B+")]) == 3.88


def test_gpa_empty_is_none():
    """빈 목록이면 평점 null"""
    assert calc_gpa([]) is None


def test_gpa_only_pass_and_no_grade_is_none():
    """평점에 들어갈 과목이 하나도 없으면(P·성적 없음만) null"""
    assert calc_gpa([_item(2, "P"), _item(3, None)]) is None


def test_earned_credits_excludes_f_only():
    """취득학점: F 제외, P·성적 없음 포함 → 3 + 2 + 3 = 8"""
    items = [_item(3, "A+"), _item(2, "P"), _item(3, None), _item(2, "F")]
    assert earned_credits(items) == 8


# =========================================================================
# summarize
# =========================================================================


def test_summarize():
    items = [
        _item(3, "A+", "전공필수", 1, "1"),
        _item(3, "F", "전공선택", 1, "1"),
        _item(2, "B0", "교양선택", 1, "1"),
        _item(2, "P", "교양필수", 1, "여름"),
        _item(3, "A0", "전공선택", 1, "2"),
        _item(3, None, "전공선택", 2, "1"),
    ]
    result = summarize(items)

    # 전체: (4.5×3 + 0×3 + 3.0×2 + 4.0×3) / 11 = 31.5 / 11 = 2.8636... → 2.86
    assert result["gpa"] == 2.86
    # 전공: (4.5×3 + 0×3 + 4.0×3) / 9 = 25.5 / 9 = 2.8333... → 2.83
    assert result["major_gpa"] == 2.83
    # 취득학점: F(3) 만 빠짐 → 16 - 3 = 13
    assert result["earned_credits"] == 13
    assert result["by_category"] == {"전공필수": 3, "전공선택": 6, "교양": 4}

    # 학기 순서: 1학년 1학기 → 1학년 여름 → 1학년 2학기 → 2학년 1학기
    assert result["terms"] == [
        # (4.5×3 + 0×3 + 3.0×2) / 8 = 2.4375 → 2.44, 취득학점은 F 빼고 3 + 2 = 5
        {"year": 1, "semester": "1", "gpa": 2.44, "earned_credits": 5},
        {"year": 1, "semester": "여름", "gpa": None, "earned_credits": 2},
        {"year": 1, "semester": "2", "gpa": 4.0, "earned_credits": 3},
        {"year": 2, "semester": "1", "gpa": None, "earned_credits": 3},
    ]


def test_summarize_empty():
    """이수 내역이 없으면 평점은 null, 학점은 0"""
    assert summarize([]) == {
        "gpa": None,
        "major_gpa": None,
        "earned_credits": 0,
        "by_category": {"전공필수": 0, "전공선택": 0, "교양": 0},
        "terms": [],
    }
