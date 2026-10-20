"""
인증 API 테스트: 회원가입 / 로그인 / 내 정보 / 관리자 권한.

실행 방법 (backend 폴더에서, venv 활성화 후):
    python -m pytest tests -v

사용하는 fixture(client, signup_payload, student, admin 등)는 tests/conftest.py 에 있습니다.
테스트에서 만든 계정은 테스트가 끝나면 자동으로 삭제됩니다.
"""

from conftest import TEST_PASSWORD, auth_header

# =========================================================================
# 1. 회원가입
# =========================================================================


def test_signup_success(client, signup_payload):
    """회원가입 성공 → 201, role 은 항상 student"""
    res = client.post("/api/auth/signup", json=signup_payload)

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["role"] == "student"
    assert body["email"] == signup_payload["email"]
    # 비밀번호(해시 포함)는 응답에 절대 나오면 안 됩니다.
    assert "password" not in body and "password_hash" not in body


def test_signup_duplicate_email(client, signup_payload):
    """같은 이메일로 두 번 가입 → 두 번째는 409"""
    first = client.post("/api/auth/signup", json=signup_payload)
    assert first.status_code == 201, first.text

    second = client.post("/api/auth/signup", json=signup_payload)
    assert second.status_code == 409


def test_signup_password_too_short(client, signup_payload):
    """비밀번호 8자 미만 → 422"""
    signup_payload["password"] = "abc12"
    res = client.post("/api/auth/signup", json=signup_payload)

    assert res.status_code == 422
    assert res.json()["detail"] == "비밀번호는 8자 이상이어야 합니다"


def test_signup_password_no_digit(client, signup_payload):
    """비밀번호에 숫자 없음 → 422"""
    signup_payload["password"] = "abcdefghij"
    res = client.post("/api/auth/signup", json=signup_payload)

    assert res.status_code == 422
    assert res.json()["detail"] == "비밀번호에 숫자를 1자 이상 포함해야 합니다"


# =========================================================================
# 2. 로그인
# =========================================================================


def test_login_success(client, signup_payload):
    """가입한 계정으로 로그인 → 200, access_token 있음"""
    assert client.post("/api/auth/signup", json=signup_payload).status_code == 201

    res = client.post(
        "/api/auth/login",
        json={"email": signup_payload["email"], "password": TEST_PASSWORD},
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["access_token"]  # 빈 문자열이 아니어야 함
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client, student):
    """비밀번호 틀림 → 401"""
    res = client.post(
        "/api/auth/login",
        json={"email": student["email"], "password": "WrongPass999"},
    )
    assert res.status_code == 401


# =========================================================================
# 3. 내 정보 (/api/auth/me)
# =========================================================================


def test_me_with_token(client, student):
    """토큰으로 내 정보 조회 → 200, 이름이 가입할 때와 같음"""
    res = client.get("/api/auth/me", headers=auth_header(student["token"]))

    assert res.status_code == 200, res.text
    assert res.json()["name"] == student["name"]


def test_me_without_token(client):
    """토큰 없이 내 정보 조회 → 401"""
    res = client.get("/api/auth/me")
    assert res.status_code == 401


# =========================================================================
# 4. 관리자 권한 (/api/admin/ping)
# =========================================================================


def test_admin_ping_as_student(client, student):
    """학생 토큰으로 관리자 API → 403"""
    res = client.get("/api/admin/ping", headers=auth_header(student["token"]))
    assert res.status_code == 403


def test_admin_ping_as_admin(client, admin):
    """관리자 토큰으로 관리자 API → 200"""
    res = client.get("/api/admin/ping", headers=auth_header(admin["token"]))

    assert res.status_code == 200, res.text
    assert res.json() == {"ok": True}
