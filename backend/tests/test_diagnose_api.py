"""
POST /api/diagnose 테스트.

[주의] 실제 Neon DB 를 사용합니다. (conftest.py 설명 참고)
    테스트 계정은 make_email 로 만들어서 테스트가 끝나면 자동으로 삭제됩니다.
    이수 내역은 DB 에 저장하지 않고 요청 본문으로만 보내므로 따로 지울 데이터가 없습니다.
"""

import csv
import os

import pytest

from conftest import TEST_PASSWORD, auth_header, login

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _sw_terms_1_to_4_codes() -> list[str]:
    """test_diagnose.py 케이스 1 과 같은 이수 내역: 1~4학기 공통+SW 과목 전부 (현장실습 제외)"""
    with open(os.path.join(DATA_DIR, "courses.csv"), encoding="utf-8-sig", newline="") as f:
        return [
            r["code"]
            for r in csv.DictReader(f)
            if r["program"] == "전문학사"
            and r["major"] in ("공통", "SW융합전공")
            and 1 <= int(r["term_index"]) <= 4
            and "현장실습" not in r["name"]
        ]


@pytest.fixture
def make_student(client, make_email):
    """
    학위과정·세부전공 이름을 골라서 학생 계정을 만들고 토큰을 돌려주는 함수.

    conftest 의 student fixture 는 '첫 번째' 과정·전공을 쓰므로,
    진단 결과가 전공에 따라 달라지는 이 테스트에서는 이름으로 직접 고릅니다.
    """
    options = client.get("/api/meta/signup-options").json()

    def _make(program_name: str, major_name: str = "SW융합전공") -> str:
        program = next(p for p in options["programs"] if p["name"] == program_name)
        major = next(
            m for m in options["majors"] if m["name"] == major_name and m["department_id"] == program["department_id"]
        )
        email = make_email()
        res = client.post(
            "/api/auth/signup",
            json={
                "email": email,
                "password": TEST_PASSWORD,
                "name": "진단테스트",
                "student_no": "20260001",
                "admission_year": 2026,
                "department_id": program["department_id"],
                "program_id": program["id"],
                "major_id": major["id"],
            },
        )
        assert res.status_code == 201, res.text
        return login(client, email)

    return _make


def test_diagnose_success(client, make_student):
    """케이스 1 과 같은 이수 내역 → free_needed 28, 가상 과목 16개"""
    token = make_student("전문학사")
    completed = [{"code": code} for code in _sw_terms_1_to_4_codes()]

    res = client.post("/api/diagnose", json={"completed": completed}, headers=auth_header(token))

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total"] == {"completed": 73, "required": 110, "remaining": 37}
    assert data["major"] == {"completed": 63, "required": 64, "remaining": 1}
    assert data["required"]["required"] == 9
    assert {m["name"] for m in data["required"]["missing"]} == {"정보처리특론", "캡스톤디자인1", "캡스톤디자인2"}
    assert data["major_elective_needed"] == 0
    assert data["free_needed"] == 28
    assert data["graduatable"] is False
    assert len(data["placeholders"]) == 16  # ceil(28/2) + 2


def test_diagnose_without_token(client):
    res = client.post("/api/diagnose", json={"completed": []})
    assert res.status_code == 401
    assert res.json()["detail"] == "로그인이 필요합니다"


def test_diagnose_unknown_code(client, make_student):
    token = make_student("전문학사")
    res = client.post(
        "/api/diagnose",
        json={"completed": [{"code": "CM1108"}, {"code": "CM9999"}]},
        headers=auth_header(token),
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "존재하지 않는 과목입니다: CM9999"


def test_diagnose_advanced_program(client, make_student):
    """전공심화 사용자는 아직 지원하지 않음 → 400"""
    token = make_student("전공심화")
    res = client.post("/api/diagnose", json={"completed": []}, headers=auth_header(token))
    assert res.status_code == 400
    assert res.json()["detail"] == "전공심화 과정 진단은 준비 중입니다"


def test_diagnose_incomplete_manual_item(client, make_student):
    """직접 입력 과목에 학점이 빠지면 → 422 한국어 메시지"""
    token = make_student("전문학사")
    res = client.post(
        "/api/diagnose",
        json={"completed": [{"name": "글쓰기", "category": "교양선택"}]},
        headers=auth_header(token),
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "직접 입력한 과목은 과목명·학점·이수구분을 모두 입력해야 합니다"
