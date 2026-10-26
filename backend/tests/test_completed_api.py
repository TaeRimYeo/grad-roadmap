"""
이수 내역 저장(/api/completed)·과목 목록(/api/courses)·학점 요약(/api/grades/summary)·
저장된 내역으로 진단(/api/diagnose/me) 테스트.

[주의] 실제 Neon DB 를 사용합니다. (conftest.py 설명 참고)
    이수 내역은 테스트 계정에 딸려 저장되고, 테스트가 끝나 계정을 지우면
    DB 의 ON DELETE CASCADE 로 이수 내역도 함께 지워집니다.
"""

import pytest

from conftest import auth_header
from test_diagnose_api import _sw_terms_1_to_4_codes


@pytest.fixture
def token(make_student):
    """전문학사 · SW융합전공 학생 토큰"""
    return make_student("전문학사", "SW융합전공")


def _add(client, token, **body):
    """POST /api/completed 를 보내는 도우미. 학년·학기를 안 주면 1학년 1학기."""
    body.setdefault("taken_year", 1)
    body.setdefault("taken_semester", "1")
    return client.post("/api/completed", json=body, headers=auth_header(token))


def _list(client, token):
    res = client.get("/api/completed", headers=auth_header(token))
    assert res.status_code == 200, res.text
    return res.json()


# =========================================================================
# 추가 / 목록
# =========================================================================


def test_add_and_list_sorted(client, token):
    """학과 과목·직접 입력 과목 추가 → 목록은 학년·학기 순 (1학기 → 여름 → 2학기)"""
    # 일부러 늦은 학기부터 추가
    res = _add(client, token, code="CM1207", taken_semester="2", grade="B+")
    assert res.status_code == 201, res.text
    res = _add(client, token, name="글쓰기", credits=2, category="교양선택", taken_semester="여름")
    assert res.status_code == 201, res.text
    res = _add(client, token, code="CM1102", grade="A+")
    assert res.status_code == 201, res.text
    assert res.json() == {
        "id": res.json()["id"],
        "code": "CM1102",
        "name": "웹프로그래밍기초",
        "major": "공통",
        "category": "전공선택",  # 학점·이수구분은 과목표 값
        "credits": 3,
        "taken_year": 1,
        "taken_semester": "1",
        "grade": "A+",
        "is_custom": False,
    }

    items = _list(client, token)
    assert [(i["code"], i["name"], i["taken_semester"]) for i in items] == [
        ("CM1102", "웹프로그래밍기초", "1"),
        (None, "글쓰기", "여름"),
        ("CM1207", "웹프로그래밍응용", "2"),
    ]
    assert items[1]["grade"] is None  # 성적 모름
    assert items[1]["is_custom"] is True


def test_add_semester_as_number(client, token):
    """학기를 숫자 2 로 보내도 "2" 로 저장"""
    res = _add(client, token, code="CM1102", taken_semester=2)
    assert res.status_code == 201, res.text
    assert res.json()["taken_semester"] == "2"


def test_add_duplicate_code_409(client, token):
    assert _add(client, token, code="CM1102").status_code == 201
    res = _add(client, token, code="CM1102", taken_year=2)
    assert res.status_code == 409
    assert res.json()["detail"] == "이미 등록된 과목입니다: CM1102"


def test_add_duplicate_custom_name_409(client, token):
    """직접 입력 과목은 공백을 무시하고 이름 비교 ('글쓰기' = ' 글 쓰기 ')"""
    assert _add(client, token, name="글쓰기", credits=2, category="교양선택").status_code == 201
    res = _add(client, token, name=" 글 쓰기 ", credits=3, category="교양필수")
    assert res.status_code == 409
    assert res.json()["detail"] == "이미 등록된 과목입니다: 글 쓰기"


def test_add_unknown_code_422(client, token):
    res = _add(client, token, code="CM9999")
    assert res.status_code == 422
    assert res.json()["detail"] == "존재하지 않는 과목입니다: CM9999"


@pytest.mark.parametrize(
    "body, detail",
    [
        ({"code": "CM1102", "grade": "A"}, "성적은 A+, A0, B+, B0, C+, C0, D+, D0, F, P 중 하나여야 합니다"),
        ({"code": "CM1102", "taken_year": 5}, "학년은 1~4 중 하나여야 합니다"),
        ({"code": "CM1102", "taken_semester": "봄"}, "학기는 1, 2, 여름, 겨울 중 하나여야 합니다"),
        ({"name": "글쓰기", "category": "교양선택"}, "직접 입력한 과목은 과목명·학점·이수구분을 모두 입력해야 합니다"),
    ],    ids=["bad_grade", "bad_year", "bad_semester", "custom_missing_credits"],
)
def test_add_invalid_input_422(client, token, body, detail):
    res = _add(client, token, **body)
    assert res.status_code == 422
    assert res.json()["detail"] == detail


def test_without_token_401(client):
    res = client.get("/api/completed")
    assert res.status_code == 401
    assert res.json()["detail"] == "로그인이 필요합니다"


# =========================================================================
# bulk
# =========================================================================


def test_bulk_success(client, token):
    res = client.post(
        "/api/completed/bulk",
        json={
            "taken_year": 1,
            "taken_semester": "1",
            "items": [
                {"code": "CM1101", "grade": "A+"},
                {"code": "CM1102"},
                {"name": "글쓰기", "credits": 2, "category": "교양선택", "grade": None},
            ],
        },
        headers=auth_header(token),
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert [(i["code"], i["name"], i["grade"]) for i in data] == [
        ("CM1101", "수리능력", "A+"),
        ("CM1102", "웹프로그래밍기초", None),
        (None, "글쓰기", None),
    ]
    # 학기는 위에서 한 번만 보낸 값이 전부에 적용됨
    assert {(i["taken_year"], i["taken_semester"]) for i in data} == {(1, "1")}
    assert len(_list(client, token)) == 3


def test_bulk_all_or_nothing_when_already_registered(client, token):
    """하나라도 이미 등록된 과목이면 409, 나머지도 저장하지 않음"""
    assert _add(client, token, code="CM1102").status_code == 201
    res = client.post(
        "/api/completed/bulk",
        json={"taken_year": 1, "taken_semester": "1", "items": [{"code": "CM1103"}, {"code": "CM1102"}]},
        headers=auth_header(token),
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "이미 등록된 과목입니다: CM1102"
    assert [i["code"] for i in _list(client, token)] == ["CM1102"]  # CM1103 은 저장 안 됨


def test_bulk_duplicate_within_request(client, token):
    """요청 안에서 같은 과목이 두 번 나와도 409 (code, 이름 모두)"""
    res = client.post(
        "/api/completed/bulk",
        json={
            "taken_year": 1,
            "taken_semester": "1",
            "items": [
                {"code": "CM1101"},
                {"code": "CM1101"},
                {"name": "글쓰기", "credits": 2, "category": "교양선택"},
                {"name": "글 쓰기", "credits": 2, "category": "교양선택"},
            ],
        },
        headers=auth_header(token),
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "이미 등록된 과목입니다: CM1101, 글 쓰기"
    assert _list(client, token) == []


def test_bulk_unknown_code_saves_nothing(client, token):
    res = client.post(
        "/api/completed/bulk",
        json={"taken_year": 1, "taken_semester": "1", "items": [{"code": "CM1101"}, {"code": "CM9999"}]},
        headers=auth_header(token),
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "존재하지 않는 과목입니다: CM9999"
    assert _list(client, token) == []


# =========================================================================
# 수정 / 삭제
# =========================================================================


def test_update(client, token):
    row_id = _add(client, token, code="CM1102", grade="F").json()["id"]
    url = f"/api/completed/{row_id}"

    # 재수강: 성적만 바꾸기
    res = client.patch(url, json={"grade": "B+"}, headers=auth_header(token))
    assert res.status_code == 200, res.text
    assert (res.json()["grade"], res.json()["taken_year"], res.json()["taken_semester"]) == ("B+", 1, "1")

    # 시기만 바꾸기 (성적은 그대로)
    res = client.patch(url, json={"taken_year": 2, "taken_semester": "겨울"}, headers=auth_header(token))
    assert (res.json()["grade"], res.json()["taken_year"], res.json()["taken_semester"]) == ("B+", 2, "겨울")

    # null 을 보내면 성적 지우기 (성적 모름)
    res = client.patch(url, json={"grade": None}, headers=auth_header(token))
    assert res.json()["grade"] is None
    assert res.json()["taken_year"] == 2


@pytest.mark.parametrize(
    "body, detail",
    [
        ({}, "수정할 항목(grade, taken_year, taken_semester)이 없습니다"),
        ({"taken_year": None}, "학년·학기는 비울 수 없습니다"),
        ({"grade": "A"}, "성적은 A+, A0, B+, B0, C+, C0, D+, D0, F, P 중 하나여야 합니다"),
    ],
    ids=["empty_body", "null_year", "bad_grade"],
)
def test_update_invalid_422(client, token, body, detail):
    row_id = _add(client, token, code="CM1102").json()["id"]
    res = client.patch(f"/api/completed/{row_id}", json=body, headers=auth_header(token))
    assert res.status_code == 422
    assert res.json()["detail"] == detail


def test_delete(client, token):
    row_id = _add(client, token, code="CM1102").json()["id"]
    res = client.delete(f"/api/completed/{row_id}", headers=auth_header(token))
    assert res.status_code == 204
    assert _list(client, token) == []

    # 삭제한 뒤에는 다시 추가할 수 있음 / 이미 지운 id 는 404
    assert _add(client, token, code="CM1102").status_code == 201
    res = client.delete(f"/api/completed/{row_id}", headers=auth_header(token))
    assert res.status_code == 404


def test_other_users_data_404(client, make_student):
    """남의 이수 내역은 보이지도 않고, 수정·삭제하면 404 (존재 여부를 알려주지 않음)"""
    owner = make_student("전문학사")
    other = make_student("전문학사")
    row_id = _add(client, owner, code="CM1102", grade="A+").json()["id"]

    res = client.patch(f"/api/completed/{row_id}", json={"grade": "F"}, headers=auth_header(other))
    assert res.status_code == 404
    assert res.json()["detail"] == "이수 내역을 찾을 수 없습니다"
    res = client.delete(f"/api/completed/{row_id}", headers=auth_header(other))
    assert res.status_code == 404
    assert _list(client, other) == []

    # 주인의 데이터는 그대로
    assert [(i["id"], i["grade"]) for i in _list(client, owner)] == [(row_id, "A+")]


# =========================================================================
# GET /api/courses
# =========================================================================


def test_courses_common_and_my_major_only(client, token):
    _add(client, token, code="CM1102")

    res = client.get("/api/courses", headers=auth_header(token))
    assert res.status_code == 200, res.text
    courses = res.json()
    codes = {c["code"] for c in courses}

    assert {c["major"] for c in courses} <= {"공통", "SW융합전공"}
    assert "CM1203" in codes  # IT융합개론 (SW융합전공)
    assert "CM1102" in codes  # 웹프로그래밍기초 (공통)
    assert "CM1201" not in codes  # 3D모델링기초 (게임개발전공) → 제외
    # 이미 등록한 과목만 completed=true
    assert [c["code"] for c in courses if c["completed"]] == ["CM1102"]


def test_admin_cannot_use_student_apis(client, admin):
    for url in ("/api/courses", "/api/diagnose/me"):
        res = client.get(url, headers=auth_header(admin["token"]))
        assert res.status_code == 400, url
        assert res.json()["detail"] == "학생 계정만 사용할 수 있습니다"


# =========================================================================
# GET /api/diagnose/me · GET /api/grades/summary
# =========================================================================


def test_diagnose_me_matches_post_diagnose(client, token):
    """
    저장한 이수 내역으로 진단한 결과 == 같은 과목을 POST /api/diagnose 에 넣은 결과.
    F 받은 과목은 이수로 치지 않으므로 POST 쪽에는 넣지 않습니다.
    """
    codes = _sw_terms_1_to_4_codes()
    res = client.post(
        "/api/completed/bulk",
        json={"taken_year": 1, "taken_semester": "1", "items": [{"code": c, "grade": "A0"} for c in codes]},
        headers=auth_header(token),
    )
    assert res.status_code == 201, res.text
    assert _add(client, token, name="글쓰기", credits=2, category="교양선택", taken_year=2).status_code == 201
    # 정보처리특론(전공필수)을 F → 진단에서는 아직 안 들은 과목
    assert _add(client, token, code="CM3107", grade="F", taken_year=3).status_code == 201

    mine = client.get("/api/diagnose/me", headers=auth_header(token))
    assert mine.status_code == 200, mine.text

    completed = [{"code": c} for c in codes] + [{"name": "글쓰기", "credits": 2, "category": "교양선택"}]
    posted = client.post("/api/diagnose", json={"completed": completed}, headers=auth_header(token))
    assert posted.status_code == 200, posted.text

    assert mine.json() == posted.json()
    assert mine.json()["total"]["completed"] == 75  # 73 + 글쓰기 2 (F 과목 3학점은 빠짐)
    assert "정보처리특론" in {m["name"] for m in mine.json()["required"]["missing"]}


def test_grades_summary(client, token):
    _add(client, token, code="CM1102", grade="A+")  # 공통 전공선택 3학점
    _add(client, token, code="CM1101", grade="B0")  # 공통 교양선택 2학점
    _add(client, token, code="CM1207", grade="F", taken_semester="2")  # 전공선택 3학점
    _add(client, token, name="글쓰기", credits=2, category="교양필수", grade="P", taken_semester="여름")

    res = client.get("/api/grades/summary", headers=auth_header(token))
    assert res.status_code == 200, res.text
    assert res.json() == {
        "gpa": 2.44,  # (4.5×3 + 3.0×2 + 0×3) / 8 = 19.5 / 8 = 2.4375
        "major_gpa": 2.25,  # (4.5×3 + 0×3) / 6
        "earned_credits": 7,  # 3 + 2 + 2(P), F 제외
        "by_category": {"전공필수": 0, "전공선택": 3, "교양": 4},
        "terms": [
            {"year": 1, "semester": "1", "gpa": 3.9, "earned_credits": 5},
            {"year": 1, "semester": "여름", "gpa": None, "earned_credits": 2},
            {"year": 1, "semester": "2", "gpa": 0.0, "earned_credits": 0},
        ],
    }


def test_grades_summary_empty(client, token):
    res = client.get("/api/grades/summary", headers=auth_header(token))
    assert res.status_code == 200
    assert res.json()["gpa"] is None
    assert res.json()["earned_credits"] == 0
