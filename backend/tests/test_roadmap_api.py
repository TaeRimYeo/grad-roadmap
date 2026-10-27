"""
로드맵 API 테스트.

    POST /api/roadmap/generate, POST·GET /api/roadmaps, GET·DELETE /api/roadmaps/{id}

[주의] 실제 Neon DB 를 사용합니다. (conftest.py 설명 참고)
    테스트 계정은 make_email 로 만들어서 테스트가 끝나면 자동으로 삭제되고,
    그 계정의 이수 내역·로드맵도 ON DELETE CASCADE 로 함께 지워집니다.

[시간] generate 는 솔버를 한 번 돌리므로 요청 한 번에 1초 남짓 걸립니다.
    저장·목록 테스트는 솔버가 필요 없으므로 가짜 plan(FAKE_PLAN)으로 빠르게 합니다.
"""

import csv
import os
from datetime import datetime

from conftest import auth_header

from db import SessionLocal
from models import Roadmap
from routers.roadmap import KST, MAX_SAVED_ROADMAPS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# 저장 API 는 plan 의 terms(목록)·total_terms(숫자)만 확인하므로 이 정도면 충분합니다.
FAKE_PLAN = {
    "start_term": 5,
    "feasible": True,
    "message": None,
    "reasons": [],
    "total_terms": 2,
    "placeholder_count": 0,
    "summary": {},
    "terms": [],
}


# =========================================================================
# 도우미 함수
# =========================================================================


def _sw_codes_by_term(last_term: int) -> dict[int, list[str]]:
    """courses.csv 에서 1 ~ last_term 학기의 공통+SW 과목 code 를 학기별로 (현장실습 제외)"""
    by_term: dict[int, list[str]] = {}
    with open(os.path.join(DATA_DIR, "courses.csv"), encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if (
                r["program"] == "전문학사"
                and r["major"] in ("공통", "SW융합전공")
                and 1 <= int(r["term_index"]) <= last_term
                and "현장실습" not in r["name"]
            ):
                by_term.setdefault(int(r["term_index"]), []).append(r["code"])
    return by_term


def _add_term(client, headers, term: int, items: list[dict]):
    """통합 학기 번호(term) 한 학기의 과목들을 이수 내역에 등록. 1 → 1학년 1학기, 4 → 2학년 2학기"""
    res = client.post(
        "/api/completed/bulk",
        json={"taken_year": (term + 1) // 2, "taken_semester": "1" if term % 2 else "2", "items": items},
        headers=headers,
    )
    assert res.status_code == 201, res.text


def _add_sw_courses(client, headers, last_term: int):
    """1 ~ last_term 학기 과목을 각 학기에 들은 것으로 등록"""
    for term, codes in sorted(_sw_codes_by_term(last_term).items()):
        _add_term(client, headers, term, [{"code": c} for c in codes])


def _generate(client, headers, body=None):
    res = client.post("/api/roadmap/generate", json=body, headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def _save(client, headers, **body):
    return client.post("/api/roadmaps", json={"start_term": 5, "plan": FAKE_PLAN, **body}, headers=headers)


# =========================================================================
# 생성 (POST /api/roadmap/generate)
# =========================================================================


def test_generate_start_term_auto_freshman(client, make_student):
    """이수 내역이 없으면 1학기부터. 정규 6학기를 모두 배치."""
    headers = auth_header(make_student("전문학사"))

    data = _generate(client, headers)  # 본문 없이 요청

    assert data["start_term"] == 1
    assert data["feasible"] is True
    assert data["message"] is None
    assert [t["term"] for t in data["terms"]] == [1, 2, 3, 4, 5, 6]
    assert data["summary"]["total_remaining"] == 110


def test_generate_start_term_auto_after_term_4(client, make_student):
    """
    1~4학기를 들었으면 5학기(3학년 1학기)부터.
    응답에 진단 요약·분반(sections)·conflicts 가 붙는지도 확인합니다.
    """
    headers = auth_header(make_student("전문학사"))
    _add_sw_courses(client, headers, last_term=4)

    data = _generate(client, headers, {})

    assert data["start_term"] == 5
    assert data["feasible"] is True and data["reasons"] == []
    assert [t["term"] for t in data["terms"]] == [5, 6]
    assert data["total_terms"] == 2

    # 진단 요약 (test_diagnose_api 의 같은 이수 내역과 같은 값)
    assert data["summary"]["total_remaining"] == 37
    assert data["summary"]["major_remaining"] == 1
    assert {m["name"] for m in data["summary"]["required_missing"]} == {"정보처리특론", "캡스톤디자인1", "캡스톤디자인2"}

    for term in data["terms"]:
        assert isinstance(term["conflicts"], list)
        for course in term["courses"]:
            if course["is_placeholder"]:
                assert course["sections"] == []  # 가상 과목은 시간표 없음
    # 캡스톤디자인1 은 sections.csv 에 분반이 있으므로 요일·교시·강의실이 붙어 있어야 함
    capstone = next(c for t in data["terms"] for c in t["courses"] if c["name"] == "캡스톤디자인1")
    assert capstone["sections"]
    assert {"section_no", "day", "start_period", "end_period", "start_time", "end_time", "room", "professor"} <= set(
        capstone["sections"][0]
    )


def test_generate_start_term_counts_failed_course(client, make_student):
    """
    F 받은 과목도 '그 학기를 다녔다' 로 보고 시작 학기를 계산합니다. (진단에서는 F 를 미이수로 봄)
    1~4학기 + 3학년 1학기에 정보처리특론 F → 시작 학기 6, 정보처리특론은 여전히 남은 전필
    """
    headers = auth_header(make_student("전문학사"))
    _add_sw_courses(client, headers, last_term=4)
    _add_term(client, headers, 5, [{"code": "CM3107", "grade": "F"}])

    data = _generate(client, headers)

    assert data["start_term"] == 6
    assert "정보처리특론" in {m["name"] for m in data["summary"]["required_missing"]}


def test_generate_start_term_given(client, make_student):
    """요청에 start_term 을 주면 이수 내역과 관계없이 그 학기부터"""
    headers = auth_header(make_student("전문학사"))
    _add_sw_courses(client, headers, last_term=4)

    data = _generate(client, headers, {"start_term": 6})

    assert data["start_term"] == 6
    assert data["terms"][0]["term"] == 6


def test_generate_start_term_out_of_range_422(client, make_student):
    headers = auth_header(make_student("전문학사"))
    res = client.post("/api/roadmap/generate", json={"start_term": 9}, headers=headers)
    assert res.status_code == 422
    assert res.json()["detail"] == "시작 학기는 1~8 사이여야 합니다"


def test_generate_already_graduated(client, make_student):
    """졸업요건을 모두 채웠으면 terms 빈 목록 + 안내 문구"""
    headers = auth_header(make_student("전문학사"))
    _add_sw_courses(client, headers, last_term=6)
    # 학과 과목만으로 모자란 총학점은 직접 입력 교양 한 건으로 채웁니다.
    remaining = client.get("/api/diagnose/me", headers=headers).json()["total"]["remaining"]
    if remaining:
        _add_term(client, headers, 6, [{"name": "학교공통교양", "credits": remaining, "category": "교양선택"}])
    assert client.get("/api/diagnose/me", headers=headers).json()["graduatable"] is True

    data = _generate(client, headers)

    assert data["terms"] == []
    assert data["total_terms"] == 0
    assert data["message"] == "이미 졸업 요건을 모두 채웠습니다"
    assert data["start_term"] == 7
    assert data["summary"]["total_remaining"] == 0


# =========================================================================
# 저장 · 목록 · 상세 · 삭제
# =========================================================================


def test_save_list_detail_delete(client, make_student):
    """실제 generate 결과를 저장 → 목록 → 상세(plan 그대로) → 삭제 → 404"""
    headers = auth_header(make_student("전문학사"))
    _add_sw_courses(client, headers, last_term=4)
    plan = _generate(client, headers)

    res = client.post("/api/roadmaps", json={"title": "3학년 계획", "start_term": 5, "plan": plan}, headers=headers)
    assert res.status_code == 201, res.text
    saved = res.json()
    assert saved["title"] == "3학년 계획"
    assert saved["start_term"] == 5
    assert saved["total_terms"] == 2

    items = client.get("/api/roadmaps", headers=headers).json()
    assert [i["id"] for i in items] == [saved["id"]]
    assert set(items[0]) == {"id", "title", "start_term", "total_terms", "created_at"}

    detail = client.get(f"/api/roadmaps/{saved['id']}", headers=headers).json()
    assert detail["plan"] == plan
    assert detail["title"] == "3학년 계획"

    res = client.delete(f"/api/roadmaps/{saved['id']}", headers=headers)
    assert res.status_code == 204
    assert client.get(f"/api/roadmaps/{saved['id']}", headers=headers).status_code == 404
    assert client.get("/api/roadmaps", headers=headers).json() == []


def test_save_default_title_and_newest_first(client, make_student):
    """제목이 없거나 공백이면 '날짜 로드맵'. 목록은 최신순."""
    headers = auth_header(make_student("전문학사"))
    first = _save(client, headers).json()
    second = _save(client, headers, title="   ").json()

    expected = f"{datetime.now(KST).date().isoformat()} 로드맵"
    assert first["title"] == expected
    assert second["title"] == expected

    items = client.get("/api/roadmaps", headers=headers).json()
    assert [i["id"] for i in items] == [second["id"], first["id"]]


def test_save_invalid_plan_422(client, make_student):
    headers = auth_header(make_student("전문학사"))
    res = client.post("/api/roadmaps", json={"start_term": 5, "plan": {"foo": 1}}, headers=headers)
    assert res.status_code == 422
    assert res.json()["detail"] == "plan 은 로드맵 생성 결과(terms, total_terms 포함)여야 합니다"


def test_other_users_roadmap_404(client, make_student):
    """남의 로드맵 id 로 상세·삭제 → 404 (있다는 사실도 알려주지 않음)"""
    owner = auth_header(make_student("전문학사"))
    other = auth_header(make_student("전문학사"))
    roadmap_id = _save(client, owner).json()["id"]

    for res in (
        client.get(f"/api/roadmaps/{roadmap_id}", headers=other),
        client.delete(f"/api/roadmaps/{roadmap_id}", headers=other),
    ):
        assert res.status_code == 404
        assert res.json()["detail"] == "로드맵을 찾을 수 없습니다"

    # 주인 쪽에서는 그대로 남아 있음
    assert client.get(f"/api/roadmaps/{roadmap_id}", headers=owner).status_code == 200
    assert client.get("/api/roadmaps", headers=other).json() == []


def test_save_limit_409(client, make_student):
    """20개까지 저장되고 21번째는 409"""
    headers = auth_header(make_student("전문학사"))
    user_id = client.get("/api/auth/me", headers=headers).json()["id"]

    # 19개는 DB 에 바로 넣고(빠르게), 20번째는 API 로 저장 → 성공해야 함
    with SessionLocal() as db:
        db.add_all(
            Roadmap(user_id=user_id, title=f"로드맵{i}", start_term=5, total_terms=2, params_json={}, result_json=FAKE_PLAN)
            for i in range(MAX_SAVED_ROADMAPS - 1)
        )
        db.commit()
    assert _save(client, headers).status_code == 201

    res = _save(client, headers)
    assert res.status_code == 409
    assert res.json()["detail"] == "로드맵은 최대 20개까지 저장할 수 있습니다"
    assert len(client.get("/api/roadmaps", headers=headers).json()) == MAX_SAVED_ROADMAPS


# =========================================================================
# 권한
# =========================================================================


def test_admin_cannot_use_roadmap_apis(client, admin):
    headers = auth_header(admin["token"])
    for res in (
        client.post("/api/roadmap/generate", headers=headers),
        client.get("/api/roadmaps", headers=headers),
        client.post("/api/roadmaps", json={"start_term": 5, "plan": FAKE_PLAN}, headers=headers),
        client.get("/api/roadmaps/1", headers=headers),
        client.delete("/api/roadmaps/1", headers=headers),
    ):
        assert res.status_code == 400
        assert res.json()["detail"] == "학생 계정만 사용할 수 있습니다"


def test_roadmap_without_token_401(client):
    res = client.post("/api/roadmap/generate")
    assert res.status_code == 401
    assert res.json()["detail"] == "로그인이 필요합니다"
