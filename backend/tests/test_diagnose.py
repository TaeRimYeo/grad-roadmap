"""
진단(diagnose) · 가상 과목(placeholder) 테스트.

DB 를 쓰지 않고 backend/data/ 의 원본 CSV·JSON 을 직접 읽어서 테스트합니다.
(diagnose 는 순수 함수라서 DB 없이도 같은 결과가 나와야 합니다)
"""

import csv
import json
import os
import sys

import pytest

# backend/ 폴더를 import 경로에 추가 (conftest.py 와 같은 이유)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from diagnose import diagnose  # noqa: E402
from placeholder import make_placeholders  # noqa: E402

DATA_DIR = os.path.join(BACKEND_DIR, "data")


# =========================================================================
# 데이터 읽기 (fixture)
# =========================================================================


def _to_int(value):
    """CSV 의 '3.0' 같은 문자열을 숫자로. 빈 칸이면 None."""
    return int(float(value)) if value not in (None, "") else None


@pytest.fixture(scope="module")
def courses():
    """
    courses.csv → 과목 dict 목록.

    utf-8-sig : 파일 맨 앞의 BOM(보이지 않는 표시 문자)을 자동으로 떼어줍니다.
                그냥 utf-8 로 열면 첫 열 이름이 '\\ufeffcode' 가 되어버립니다.
    """
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
def requirement():
    """requirements.json 의 전문학사 졸업요건"""
    with open(os.path.join(DATA_DIR, "requirements.json"), encoding="utf-8") as f:
        program = json.load(f)["programs"]["전문학사"]
    return {
        "total_credits": program["total_credits"],
        "major_min": program["category_min"]["전공"],
        "required_courses": program["required_courses"],
    }


@pytest.fixture
def run(courses, prereqs, requirement):
    """테스트에서 completed 와 major 만 바꿔가며 diagnose 를 부르는 도우미"""

    def _run(completed, major="SW융합전공"):
        return diagnose(courses, prereqs, requirement, completed, major)

    return _run


def _code_of(courses, name):
    """과목명으로 code 찾기 (테스트 가독성용)"""
    return next(c["code"] for c in courses if c["name"] == name)


# =========================================================================
# 케이스 1 — SW융합전공, 1~4학기 공통+SW 과목 전부 이수
# =========================================================================


def test_sw_terms_1_to_4(run, courses):
    completed = [
        {"code": c["code"]}
        for c in courses
        if c["program"] == "전문학사"
        and c["major"] in ("공통", "SW융합전공")
        and 1 <= c["term_index"] <= 4
        and "현장실습" not in c["name"]
    ]
    r = run(completed)

    assert r["total"] == {"completed": 73, "required": 110, "remaining": 37}
    assert r["major"] == {"completed": 63, "required": 64, "remaining": 1}
    assert r["required"]["completed"] == 0
    assert r["required"]["required"] == 9
    assert [m["name"] for m in r["required"]["missing"]] == ["정보처리특론", "캡스톤디자인1", "캡스톤디자인2"]
    # 남은 전공 1학점은 전필 9학점으로 채워지므로 전선은 따로 필요 없음
    assert r["major_elective_needed"] == 0
    assert r["free_needed"] == 28  # 37 - 9 - 0
    assert r["graduatable"] is False
    assert r["unknown_codes"] == []

    # available 은 이수하지 않은 과목만, 현장실습·전공심화·게임 전용 과목은 없어야 함
    names = {a["name"] for a in r["available"]}
    assert "캡스톤디자인1" in names
    assert "파이썬프로그래밍기초" not in names
    assert not names & {"학기제현장실습", "현장실습", "딥러닝(온라인)", "게임엔진기초"}
    # 1~4학기를 다 들었으니 남은 과목은 전부 5~6학기 과목
    assert {a["term_index"] for a in r["available"]} == {5, 6}


# =========================================================================
# 케이스 2 — 신입생 (이수 없음)
# =========================================================================


def test_freshman(run):
    r = run([])

    assert r["total"] == {"completed": 0, "required": 110, "remaining": 110}
    assert r["major"] == {"completed": 0, "required": 64, "remaining": 64}
    assert r["required"]["completed"] == 0
    assert r["required"]["required"] == 9
    assert len(r["required"]["missing"]) == 3
    assert r["major_elective_needed"] == 55  # 64 - 9
    assert r["free_needed"] == 46  # 110 - 9 - 55
    assert r["graduatable"] is False


# =========================================================================
# 케이스 3 — 선수과목 미이수 경고
# =========================================================================


def test_prereq_warning(run, courses):
    # 파이썬프로그래밍기초 없이 다른 1학기 과목만 이수 → 응용이 경고에 나와야 함
    completed = [{"code": _code_of(courses, "웹프로그래밍기초")}]
    r = run(completed)

    messages = [w["message"] for w in r["prereq_warnings"]]
    assert "파이썬프로그래밍응용 — 파이썬프로그래밍기초를 먼저 이수해야 합니다" in messages
    # 웹프로그래밍기초는 들었으므로 웹프로그래밍응용은 경고가 없어야 함
    assert all(w["name"] != "웹프로그래밍응용" for w in r["prereq_warnings"])
    # 받침 있는 선수과목은 '을' (캡스톤디자인1 → 일)
    assert "캡스톤디자인2 — 캡스톤디자인1을 먼저 이수해야 합니다" in messages


# =========================================================================
# 케이스 4 — 같은 과목 중복 입력
# =========================================================================


def test_duplicate_counted_once(run, courses):
    code = _code_of(courses, "파이썬프로그래밍기초")  # 3학점
    manual = {"name": "글쓰기", "credits": 2, "category": "교양선택"}
    r = run([{"code": code}, {"code": code}, manual, dict(manual)])

    assert r["total"]["completed"] == 5  # 3 + 2, 두 번씩 넣었지만 한 번만
    assert r["major"]["completed"] == 3


# =========================================================================
# 케이스 5 — 직접 입력한 교양
# =========================================================================


def test_manual_elective_adds_to_total(run):
    r = run([{"name": "글쓰기", "credits": 2, "category": "교양선택"}])

    assert r["total"]["completed"] == 2
    assert r["total"]["remaining"] == 108
    assert r["major"]["completed"] == 0  # 교양은 전공학점에 안 들어감
    assert r["free_needed"] == 44  # 46 - 2


# =========================================================================
# 추가 — DB 에 없는 code
# =========================================================================


def test_unknown_code(run):
    r = run([{"code": "XX9999"}])
    assert r["unknown_codes"] == ["XX9999"]
    assert r["total"]["completed"] == 0  # 계산에서 제외


# =========================================================================
# placeholder
# =========================================================================


def test_placeholders_count_and_credits():
    items = make_placeholders(28)
    assert len(items) == 16  # ceil(28/2) + 2
    assert [p["credits"] for p in items].count(3) == 8
    assert [p["credits"] for p in items].count(2) == 8
    assert items[0]["code"] == "GE_A" and items[0]["name"] == "교양 A"
    assert all(p["is_placeholder"] and p["offered"] == 3 and p["prereqs"] == [] for p in items)


def test_placeholders_edge_cases():
    assert make_placeholders(0) == []
    # 홀수 개(ceil(5/2)+2 = 5)면 3학점이 하나 더 많음
    assert [p["credits"] for p in make_placeholders(5)] == [3, 2, 3, 2, 3]
    # 26개를 넘으면 GE_AA, GE_AB ... 로 이어짐 (110학점 → 57개)
    big = make_placeholders(110)
    assert len(big) == 57
    assert big[25]["code"] == "GE_Z" and big[26]["code"] == "GE_AA"


def test_placeholders_from_free_needed(run):
    # 가상 과목은 free_needed 기준으로 만든다 (신입생 46 → 25개)
    r = run([])
    assert len(make_placeholders(r["free_needed"])) == 25
