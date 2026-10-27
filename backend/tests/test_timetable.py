"""
시간표 겹침 검사(timetable.py) 테스트.

timetable 은 순수 함수라서 DB 없이 dict 만 만들어 넣어 봅니다.
"""

import os
import sys

# backend/ 폴더를 import 경로에 추가 (conftest.py 와 같은 이유)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from timetable import course_conflict, find_conflicts, overlap  # noqa: E402


def sec(day: str, start: int, end: int) -> dict:
    """분반 하나 (테스트에 필요한 값만)"""
    return {"day": day, "start_period": start, "end_period": end}


def course(name: str, *sections: dict) -> dict:
    return {"name": name, "sections": list(sections)}


# =========================================================================
# 분반 두 개 비교
# =========================================================================


def test_same_day_overlap():
    """같은 요일, 교시가 겹침 → 겹치는 구간을 돌려줌"""
    assert overlap(sec("화", 3, 4), sec("화", 4, 5)) == (4, 4)
    assert overlap(sec("화", 2, 4), sec("화", 3, 4)) == (3, 4)


def test_different_day_no_overlap():
    """교시가 같아도 요일이 다르면 안 겹침"""
    assert overlap(sec("화", 3, 4), sec("수", 3, 4)) is None


def test_end_right_before_next_start_no_overlap():
    """끝교시 4 다음 시작교시 5 → 안 겹침 (붙어 있을 뿐)"""
    assert overlap(sec("화", 3, 4), sec("화", 5, 6)) is None
    assert overlap(sec("화", 5, 6), sec("화", 3, 4)) is None


# =========================================================================
# 과목 단위 경고
# =========================================================================


def test_conflict_message():
    """예시 문구 그대로 나오는지 ('응용' 은 받침이 있으므로 '과')"""
    a = course("자바프로그래밍응용", sec("화", 3, 4))
    b = course("C#프로그래밍", sec("화", 3, 4))
    assert course_conflict(a, b) == "자바프로그래밍응용과 C#프로그래밍의 수업 시간이 겹칩니다 (화 3~4교시)"


def test_conflict_message_no_batchim_and_single_period():
    """받침 없는 과목명은 '와', 한 교시만 겹치면 '4교시' 로 표시"""
    a = course("컴퓨터공학개론", sec("월", 3, 4))
    b = course("데이터베이스", sec("월", 4, 5))
    assert course_conflict(b, a) == "데이터베이스와 컴퓨터공학개론의 수업 시간이 겹칩니다 (월 4교시)"


def test_other_section_avoids_conflict():
    """분반이 여러 개라 겹치지 않는 분반을 고를 수 있으면 경고하지 않음"""
    graphics = course("컴퓨터그래픽", sec("화", 2, 4), sec("목", 2, 4))
    career = course("진로탐구", sec("화", 3, 4))
    assert course_conflict(graphics, career) is None


def test_all_sections_overlap_is_conflict():
    """모든 분반 조합이 겹치면 경고"""
    a = course("과목가", sec("화", 2, 4), sec("목", 2, 4))
    b = course("과목나", sec("화", 3, 3), sec("목", 4, 5))
    # 화-목, 목-화 조합은 안 겹치므로 경고 없음
    assert course_conflict(a, b) is None
    c = course("과목다", sec("화", 2, 4), sec("화", 6, 8))
    d = course("과목라", sec("화", 3, 7))
    assert course_conflict(c, d) == "과목다와 과목라의 수업 시간이 겹칩니다 (화 3~4교시)"


def test_no_sections_no_conflict():
    """가상 과목처럼 분반이 없으면 판단하지 않음"""
    assert course_conflict(course("교양 A"), course("진로탐구", sec("화", 3, 4))) is None


def test_find_conflicts_lists_every_pair():
    """한 학기 안의 겹치는 쌍을 모두 찾음"""
    courses = [
        course("가", sec("월", 1, 2)),
        course("나", sec("월", 2, 3)),
        course("다", sec("월", 3, 4)),
        course("라", sec("금", 1, 2)),
    ]
    assert find_conflicts(courses) == [
        "가와 나의 수업 시간이 겹칩니다 (월 2교시)",
        "나와 다의 수업 시간이 겹칩니다 (월 3교시)",
    ]
