"""
로드맵 솔버(solve_roadmap) 테스트.

test_diagnose.py 와 같이 DB 를 쓰지 않고 backend/data/ 의 원본 CSV·JSON 을 직접 읽습니다.
흐름은 실제 서비스와 같습니다:  이수 내역 → diagnose() → solve_roadmap()
"""

import csv
import json
import os
import sys
import time

import pytest

# backend/ 폴더를 import 경로에 추가 (conftest.py 와 같은 이유)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from diagnose import diagnose  # noqa: E402
from solver import solve_roadmap  # noqa: E402

DATA_DIR = os.path.join(BACKEND_DIR, "data")

# 테스트 하나당 허용 실행 시간(초)
TIME_BUDGET = 5.0


# =========================================================================
# 데이터 읽기 (fixture) — test_diagnose.py 와 같은 방식
# =========================================================================


def _to_int(value):
    """CSV 의 '3.0' 같은 문자열을 숫자로. 빈 칸이면 None."""
    return int(float(value)) if value not in (None, "") else None


@pytest.fixture(scope="module")
def courses():
    """courses.csv → 과목 dict 목록 (utf-8-sig: 파일 맨 앞 BOM 제거)"""
    with open(os.path.join(DATA_DIR, "courses.csv"), encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return [
        {
            "code": r["code"],
            "name": r["name"],
            "program": r["program"],
            "major": r["major"],
            "category": r["category"] or None,
            "credits": _to_int(r["credits"]),
            "offered": _to_int(r["offered"]),
            "term_index": _to_int(r["term_index"]),
        }
        for r in rows
    ]


@pytest.fixture(scope="module")
def prereqs():
    """prerequisites.csv → (선수 code, 후수 code) 목록"""
    with open(os.path.join(DATA_DIR, "prerequisites.csv"), encoding="utf-8-sig", newline="") as f:
        return [(r["prereq_code"], r["course_code"]) for r in csv.DictReader(f)]


@pytest.fixture(scope="module")
def program():
    """requirements.json 의 전문학사 항목 전체"""
    with open(os.path.join(DATA_DIR, "requirements.json"), encoding="utf-8") as f:
        return json.load(f)["programs"]["전문학사"]


@pytest.fixture(scope="module")
def requirement(program):
    """diagnose() 가 받는 졸업요건 모양"""
    return {
        "total_credits": program["total_credits"],
        "major_min": program["category_min"]["전공"],
        "required_courses": program["required_courses"],
    }


@pytest.fixture
def plan(courses, prereqs, requirement, program):
    """
    이수 code 목록과 start_term 만 바꿔가며 진단 → 솔버를 부르는 도우미.
    실행 시간이 TIME_BUDGET 을 넘으면 바로 실패시킵니다.
    """

    def _plan(done_codes, start_term, major="SW융합전공"):
        diagnosis = diagnose(courses, prereqs, requirement, [{"code": c} for c in done_codes], major)
        began = time.perf_counter()
        result = solve_roadmap(
            diagnosis["available"], prereqs, done_codes, diagnosis, start_term, program["term_credit_rule"]
        )
        elapsed = time.perf_counter() - began
        assert elapsed < TIME_BUDGET, f"솔버가 {elapsed:.2f}초 걸렸습니다 (허용 {TIME_BUDGET}초)"
        return diagnosis, result

    return _plan


def _sw_codes(courses, first_term, last_term):
    """공통+SW 과목 중 권장학기가 first_term~last_term 인 과목 code (현장실습 제외)"""
    return [
        c["code"]
        for c in courses
        if c["program"] == "전문학사"
        and c["major"] in ("공통", "SW융합전공")
        and first_term <= c["term_index"] <= last_term
        and "현장실습" not in c["name"]
    ]


def _placed(result):
    """결과에서 code → 배치된 학기 번호 (가상 과목 제외)"""
    return {c["code"]: t["term"] for t in result["terms"] for c in t["courses"] if not c["is_placeholder"]}


# =========================================================================
# 케이스 1 — SW 신입생 (start_term 1)
# =========================================================================


def test_freshman_six_terms(plan, courses, prereqs, program):
    diagnosis, r = plan([], start_term=1)

    assert r["feasible"] is True
    assert r["reasons"] == []
    assert r["total_terms"] == 6
    assert [t["term"] for t in r["terms"]] == [1, 2, 3, 4, 5, 6]
    assert [t["label"] for t in r["terms"]][0] == "1학년 1학기"
    assert [t["label"] for t in r["terms"]][-1] == "3학년 2학기"

    # 학기마다 15~22학점, 표시된 학점 = 과목 학점 합
    for t in r["terms"]:
        assert 15 <= t["credits"] <= 22, t
        assert t["credits"] == sum(c["credits"] for c in t["courses"])

    # 졸업 학점: 총 110 이상, 전공(전필+전선) 64 이상
    all_courses = [c for t in r["terms"] for c in t["courses"]]
    assert sum(c["credits"] for c in all_courses) >= 110
    assert sum(c["credits"] for c in all_courses if c["category"] in ("전공필수", "전공선택")) >= 64
    assert r["placeholder_count"] == sum(1 for c in all_courses if c["is_placeholder"])

    placed = _placed(r)
    # 전공필수 3과목이 모두 들어감
    for code in program["required_courses"]:
        assert code in placed
    # 같은 과목이 두 번 들어가지 않음
    real_codes = [c["code"] for c in all_courses if not c["is_placeholder"]]
    assert len(real_codes) == len(set(real_codes))

    # 선수과목 순서: 둘 다 배치됐다면 선수가 먼저, 후수만 배치되는 일은 없음
    for before, after in prereqs:
        if after in placed:
            assert before in placed, f"{after} 의 선수 {before} 가 없음"
            assert placed[before] < placed[after]

    # 개설학기: offered 1 → 홀수 학기, 2 → 짝수 학기
    offered = {c["code"]: c["offered"] for c in courses}
    for code, term in placed.items():
        if offered[code] == 1:
            assert term % 2 == 1, code
        elif offered[code] == 2:
            assert term % 2 == 0, code


def test_freshman_prefers_real_courses(plan):
    """
    가상 과목은 '학점 합' 기준으로 최소화되므로, 실제 과목을 빼고 가상 과목을 넣지 않아야 합니다.
    SW 신입생이 들을 수 있는 실제 과목은 109학점 → 110학점까지 1학점이 모자라서
    가장 작은 가상 과목(2학점) 1개만 들어가야 합니다. (초과 1학점은 감수)
    """
    diagnosis, r = plan([], start_term=1)

    placed = _placed(r)
    # diagnose 가 '들을 수 있다' 고 한 실제 과목이 전부 계획에 들어감 (수리능력 포함)
    assert {c["code"] for c in diagnosis["available"]} == set(placed)
    assert "수리능력" in {c["name"] for t in r["terms"] for c in t["courses"]}

    placeholders = [c for t in r["terms"] for c in t["courses"] if c["is_placeholder"]]
    assert r["placeholder_count"] == 1
    assert [c["credits"] for c in placeholders] == [2]


# =========================================================================
# 케이스 2 — SW 1~4학기 이수 (test_diagnose 케이스1 과 같은 입력), start_term 5
# =========================================================================


def test_after_four_terms(plan, courses):
    diagnosis, r = plan(_sw_codes(courses, 1, 4), start_term=5)

    assert diagnosis["total"]["remaining"] == 37
    assert r["feasible"] is True
    assert r["total_terms"] == 2
    assert [t["label"] for t in r["terms"]] == ["3학년 1학기", "3학년 2학기"]
    # 남은 37학점을 2학기 안에 다 채움
    assert sum(t["credits"] for t in r["terms"]) >= 37
    names = {c["name"] for t in r["terms"] for c in t["courses"]}
    assert {"정보처리특론", "캡스톤디자인1", "캡스톤디자인2"} <= names


def test_no_placeholder_takes_only_what_is_needed(plan, courses):
    """
    가상 과목이 필요 없는 학생은 '실제 과목 빼지 않기' 규칙이 적용되지 않아야 합니다.
    (그렇지 않으면 남은 과목을 전부 들어 초과 학점이 커짐)
    """
    # SW 1~4학기 + 게임 과목 5개(14학점) 이수 → 남은 23학점, 5·6학기 실제 과목은 36학점
    done = _sw_codes(courses, 1, 4) + ["CM1201", "CM1202", "CM1205", "CM2101", "CM2103"]
    diagnosis, r = plan(done, start_term=5)

    assert diagnosis["total"]["remaining"] == 23
    assert r["feasible"] is True
    assert r["placeholder_count"] == 0
    placed_total = sum(t["credits"] for t in r["terms"])
    assert 23 <= placed_total < 36


# =========================================================================
# 케이스 3 — 마지막 학기는 10학점이면 충분
# =========================================================================


def test_last_term_allows_ten_credits(plan, courses):
    # 1~5학기 + 6학기 과목 3개(9학점)를 이수 → 남은 10학점, 6학기(마지막)부터 시작
    done = _sw_codes(courses, 1, 5) + ["CM3205", "CM3206", "CM3209"]
    diagnosis, r = plan(done, start_term=6)

    assert diagnosis["total"]["remaining"] == 10
    assert r["feasible"] is True
    assert r["total_terms"] == 1
    last = r["terms"][0]
    assert last["label"] == "3학년 2학기"
    # 15학점 미만이지만 본인의 마지막 학기라서 허용됨
    assert 10 <= last["credits"] < 15
    assert "캡스톤디자인2" in {c["name"] for c in last["courses"]}


# =========================================================================
# 케이스 4 — 불가능: 마지막 추가학기(8) 하나에 110학점
# =========================================================================


def test_infeasible_reports_reasons(plan):
    diagnosis, r = plan([], start_term=8)

    assert diagnosis["total"]["remaining"] > 22
    assert r["feasible"] is False
    assert r["terms"] == []
    assert len(r["reasons"]) > 0
    # 학점이 모자라다는 이유와, 1학기에만 열리는 전필 때문이라는 이유가 모두 있어야 함
    assert any("110학점을 채울 수 없습니다" in m for m in r["reasons"]), r["reasons"]
    assert any("캡스톤디자인1은 1학기에만 열리는데" in m for m in r["reasons"]), r["reasons"]


# =========================================================================
# 추가 — 같은 입력이면 항상 같은 결과
# =========================================================================


def test_deterministic(plan):
    _, first = plan([], start_term=1)
    _, second = plan([], start_term=1)
    assert first == second
