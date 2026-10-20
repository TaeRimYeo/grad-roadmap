"""
pytest 공통 fixture 모음.

[fixture 란? (초보자용)]
    테스트 함수가 매개변수 이름으로 "이거 필요해요" 라고 적으면,
    pytest 가 같은 이름의 fixture 함수를 먼저 실행해서 그 결과를 넣어주는 기능입니다.

        def test_something(client):   # ← client fixture 의 결과가 들어옴
            client.get(...)

    fixture 안에서 yield 를 쓰면
        yield 앞  = 테스트 전에 할 준비
        yield 뒤  = 테스트가 끝난 뒤 할 뒷정리 (테스트가 실패해도 실행됨)
    가 됩니다. (db.get_db() 의 yield 와 같은 원리)

[conftest.py 란?]
    pytest 가 자동으로 읽는 특별한 파일 이름입니다. 여기 둔 fixture 는
    import 하지 않아도 같은 폴더(tests/)의 모든 테스트 파일에서 쓸 수 있습니다.

[주의] 이 테스트는 실제 Neon DB 를 사용합니다.
    - 테스트 계정 이메일은 test_ + 무작위 문자열로 만들어 실제 계정과 겹치지 않게 하고
    - created_emails fixture 의 yield 뒤에서 만든 계정을 반드시 삭제합니다.
"""

import os
import sys
import uuid

import pytest

# 테스트 파일은 backend/tests/ 에 있지만 main.py, db.py 등은 backend/ 에 있습니다.
# 어느 폴더에서 pytest 를 실행해도 import 가 되도록 backend/ 폴더를 경로에 추가합니다.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from auth import hash_password  # noqa: E402
from db import SessionLocal  # noqa: E402
from main import app  # noqa: E402
from models import User  # noqa: E402

# 테스트에서 쓰는 비밀번호. 회원가입 규칙(8자 이상, 영문+숫자)을 만족합니다.
TEST_PASSWORD = "TestPass1234"


# =========================================================================
# 1. 서버 / 기준 정보
# =========================================================================


@pytest.fixture(scope="session")
def client():
    """
    FastAPI 앱에 요청을 보내는 가짜 브라우저.

    TestClient 는 실제로 uvicorn 서버를 켜지 않고도 app 에 직접 요청을 보내줍니다.
    scope="session" : 테스트 전체에서 딱 하나만 만들어 재사용합니다.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def signup_options(client):
    """
    회원가입에 쓸 학과·학위과정·세부전공 ID.

    ID 숫자를 코드에 고정하면 DB 를 다시 만들었을 때(시드 순서가 바뀌는 등) 테스트가 깨지므로,
    프론트와 똑같이 /api/meta/signup-options 로 받아서 '서로 맞는 조합' 을 고릅니다.
    """
    res = client.get("/api/meta/signup-options")
    assert res.status_code == 200, res.text
    data = res.json()

    # 학위과정과 세부전공이 둘 다 하나 이상 있는 첫 번째 학과를 고릅니다.
    for dept in data["departments"]:
        programs = [p for p in data["programs"] if p["department_id"] == dept["id"]]
        majors = [m for m in data["majors"] if m["department_id"] == dept["id"]]
        if programs and majors:
            return {
                "department_id": dept["id"],
                "program_id": programs[0]["id"],
                "major_id": majors[0]["id"],
            }

    pytest.fail("signup-options 에 학위과정·세부전공이 모두 있는 학과가 없습니다. 시드 데이터를 확인하세요.")


# =========================================================================
# 2. 테스트 계정 생성 / 삭제
# =========================================================================


@pytest.fixture
def created_emails():
    """
    이 테스트에서 만든 계정의 이메일을 모아두는 목록.

    테스트가 끝나면(yield 뒤) 목록에 있는 이메일의 계정을 DB 에서 전부 삭제합니다.
    회원가입 API 로 만들었든, DB 에 직접 넣었든 상관없이 이메일만 등록하면 지워집니다.
    """
    emails: list[str] = []
    yield emails

    # ---- 뒷정리: 테스트 성공/실패와 상관없이 실행됨 ----
    if emails:
        with SessionLocal() as db:
            db.execute(delete(User).where(User.email.in_(emails)))
            db.commit()


@pytest.fixture
def make_email(created_emails):
    """
    test_ + 무작위 문자열 이메일을 만들어주는 함수를 돌려줍니다.
    만든 이메일은 자동으로 created_emails 에 등록되어 테스트 후 삭제됩니다.

    uuid4().hex : 매번 다른 32자리 무작위 문자열 → 다른 테스트·실제 계정과 겹칠 일이 없음
    """

    def _make() -> str:
        email = f"test_{uuid.uuid4().hex[:16]}@example.com"
        created_emails.append(email)
        return email

    return _make


@pytest.fixture
def signup_payload(make_email, signup_options):
    """회원가입 요청 본문(JSON). 테스트마다 새 이메일을 씁니다."""
    return {
        "email": make_email(),
        "password": TEST_PASSWORD,
        "name": "테스트학생",
        "student_no": "20240001",
        "admission_year": 2024,
        **signup_options,  # department_id, program_id, major_id
    }


def login(client, email: str, password: str = TEST_PASSWORD) -> str:
    """로그인해서 access_token 을 돌려주는 도우미 함수 (fixture 아님)."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def auth_header(token: str) -> dict:
    """요청 헤더 모양: {"Authorization": "Bearer <토큰>"}"""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def student(client, signup_payload):
    """
    회원가입 API 로 만든 학생 계정 + 로그인 토큰.

    돌려주는 값: {"email", "password", "name", "token"}
    """
    res = client.post("/api/auth/signup", json=signup_payload)
    assert res.status_code == 201, res.text
    return {
        "email": signup_payload["email"],
        "password": signup_payload["password"],
        "name": signup_payload["name"],
        "token": login(client, signup_payload["email"]),
    }


@pytest.fixture
def admin(client, make_email):
    """
    관리자 계정 + 로그인 토큰.

    회원가입 API 는 무조건 student 로만 만들므로(스스로 관리자가 되는 것 차단),
    scripts/create_admin.py 처럼 DB 에 직접 role='admin' 으로 넣습니다.
    """
    email = make_email()
    with SessionLocal() as db:
        db.add(
            User(
                email=email,
                password_hash=hash_password(TEST_PASSWORD),
                name="테스트관리자",
                role="admin",
                is_active=True,
            )
        )
        db.commit()

    return {"email": email, "name": "테스트관리자", "token": login(client, email)}
