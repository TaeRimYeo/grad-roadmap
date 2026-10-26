"""
인증(로그인) 담당 모듈.

이 파일이 하는 일은 크게 세 가지입니다.
  1) 비밀번호 해싱      : hash_password / verify_password  (pwdlib + Argon2)
  2) JWT 발급과 검증    : create_access_token / decode_token (PyJWT)
  3) FastAPI 의존성 함수 : get_current_user / require_admin
                          → 라우터에서 Depends(...) 로 붙이면 "로그인한 사람만", "관리자만" 이 된다

라우터에서 쓰는 예:

    @app.get("/api/me")
    def read_me(user: User = Depends(get_current_user)):
        return {"email": user.email}

    @app.post("/api/admin/courses")
    def create_course(admin: User = Depends(require_admin)):
        ...
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.orm import Session

from db import get_db
from models import User

# =========================================================================
# 0. 설정값 읽기 (.env)
# =========================================================================

# db.py 와 마찬가지로 backend/.env 를 읽어 환경변수로 등록합니다.
# (이미 로드되어 있어도 다시 불러서 문제 될 것은 없습니다)
load_dotenv()

# SECRET_KEY: JWT 서명에 쓰는 '서버만 아는 비밀 열쇠'.
# 이 값이 새어나가면 누구나 관리자 토큰을 만들 수 있으므로 절대 코드/깃에 올리지 않습니다.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY 가 없습니다. backend/.env 파일에 SECRET_KEY 를 설정해주세요."
    )

# 토큰 유효 시간(분). .env 에 없으면 기본 60분으로 둡니다.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# 서명 알고리즘. HS256 = "SECRET_KEY 하나로 서명하고 같은 키로 검증" 하는 방식.
# 서버 한 대가 발급도 하고 검증도 하는 우리 구조에 가장 단순하고 알맞습니다.
ALGORITHM = "HS256"


# =========================================================================
# 1. 비밀번호 해싱 (pwdlib + Argon2)
# =========================================================================

# PasswordHash 는 "어떤 해시 알고리즘을 쓸지" 를 묶어둔 도구입니다.
# 튜플에 Argon2Hasher 하나만 넣었으므로 해싱·검증 모두 Argon2 로 합니다.
# (나중에 알고리즘을 바꾸고 싶으면 이 튜플 앞쪽에 새 해셔를 추가하면 됩니다)
password_hasher = PasswordHash((Argon2Hasher(),))


def hash_password(plain: str) -> str:
    """
    평문 비밀번호 → 해시 문자열.

    결과는 대략 이렇게 생겼습니다:
        $argon2id$v=19$m=65536,t=3,p=4$<솔트>$<해시값>
    알고리즘 이름, 설정값(메모리·반복 횟수), 솔트가 문자열 안에 함께 들어 있어서
    DB 의 users.password_hash 컬럼에 이 문자열 하나만 저장하면 됩니다.
    같은 비밀번호라도 솔트가 매번 랜덤이라 호출할 때마다 결과가 달라지는 게 정상입니다.
    """
    return password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    로그인 시 입력한 평문 비밀번호가 저장된 해시와 맞는지 확인.

    해시는 되돌릴 수 없으므로 "해시를 풀어서 비교" 하는 게 아니라,
    저장된 해시 안의 솔트·설정으로 입력값을 똑같이 한 번 더 해싱해서 결과가 같은지 봅니다.
    """
    try:
        return password_hasher.verify(plain, hashed)
    except UnknownHashError:
        # DB 에 들어있는 값이 Argon2 해시 형식이 아닌 경우(예: 테스트용으로 평문을 넣어둔 경우).
        # 에러로 서버를 터뜨리지 않고 "비밀번호 불일치" 로 처리합니다.
        return False


# =========================================================================
# 2. JWT 발급과 검증 (PyJWT)
# =========================================================================


def create_access_token(user: User) -> str:
    """
    로그인에 성공한 사용자에게 줄 액세스 토큰(JWT)을 만든다.

    payload(토큰 안에 담기는 내용):
        sub  : 사용자 ID. JWT 표준상 sub 는 문자열이어야 해서 str() 로 변환합니다.
        role : 'student' | 'admin'. 프론트에서 메뉴를 나눌 때 참고용으로 씁니다.
               (실제 권한 판정은 서버가 DB 의 role 로 다시 확인합니다 → require_admin)
        exp  : 만료 시각. PyJWT 가 decode 할 때 이 시각이 지났으면 자동으로 거부합니다.

    주의: payload 는 암호화가 아니라 누구나 읽을 수 있는 인코딩입니다.
          비밀번호 같은 민감 정보는 절대 넣지 않습니다.
    """
    # 서버 시간대와 상관없이 일관되도록 UTC 기준으로 계산합니다.
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": expire_at,  # PyJWT 가 datetime 을 알아서 숫자(유닉스 시각)로 바꿔줍니다
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    JWT 를 검증하고 payload(dict)를 돌려준다.

    검증 실패 시 예외가 발생합니다 (호출하는 쪽에서 처리):
        jwt.ExpiredSignatureError : exp 가 지난 토큰 (만료)
        jwt.InvalidTokenError     : 서명 불일치(위조), 형식 오류, 필수 항목 누락 등
                                    ※ ExpiredSignatureError 도 InvalidTokenError 의 한 종류
    """
    return jwt.decode(
        token,
        SECRET_KEY,
        # algorithms 를 반드시 명시합니다. 이걸 빼거나 넓게 열어두면
        # 공격자가 헤더에 "alg: none"(서명 없음)을 적어 검증을 우회하는 고전적 공격이 가능해집니다.
        algorithms=[ALGORITHM],
        # exp, sub 가 아예 없는 토큰은 우리가 발급한 게 아니므로 거부합니다.
        options={"require": ["exp", "sub"]},
    )


# =========================================================================
# 3. FastAPI 의존성 함수
# =========================================================================

# HTTPBearer 는 요청의 "Authorization: Bearer <토큰>" 헤더에서 토큰을 꺼내주는 도구입니다.
# 이걸 의존성으로 쓰면 FastAPI 가 /docs 화면에 자물쇠 모양 [Authorize] 버튼을 만들어줍니다.
#
# auto_error=False 로 둔 이유:
#   기본값(True)이면 헤더가 없을 때 FastAPI 가 영어 메시지("Not authenticated")로
#   알아서 에러를 내버립니다. False 로 두면 헤더가 없을 때 None 을 넘겨주므로,
#   우리가 직접 한국어 메시지로 401 을 낼 수 있습니다.
bearer_scheme = HTTPBearer(auto_error=False, description="로그인 후 받은 액세스 토큰")


def _unauthorized(detail: str) -> HTTPException:
    """401 에러를 만드는 작은 도우미. 메시지만 바꿔가며 여러 곳에서 씁니다."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        # HTTP 표준: 401 응답에는 "어떤 방식으로 인증해야 하는지" 를 이 헤더로 알려줍니다.
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """
    현재 요청을 보낸 사용자를 찾아 돌려주는 의존성 함수.

    처리 순서:
        1) Authorization 헤더에 Bearer 토큰이 있는가?      없으면 401
        2) 토큰이 진짜이고 만료되지 않았는가?              아니면 401
        3) 토큰의 sub(사용자 ID)로 DB 에서 사용자를 찾았는가? 없으면 401
        4) 활성화된 계정인가?                              아니면 403

    401 vs 403 차이:
        401 Unauthorized : "당신이 누군지 모르겠다" → 다시 로그인하면 해결될 수 있음
        403 Forbidden    : "누군지는 알지만 허락할 수 없다" → 다시 로그인해도 해결 안 됨
    """
    # 1) 토큰 존재 확인
    if credentials is None:
        raise _unauthorized("로그인이 필요합니다")

    # 2) 토큰 검증 (서명·만료)
    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        # 만료 에러는 InvalidTokenError 의 하위 종류라서 반드시 먼저 잡아야 합니다.
        # (순서를 바꾸면 만료도 전부 "유효하지 않은 토큰" 으로 처리됨)
        raise _unauthorized("로그인이 만료되었습니다. 다시 로그인해주세요")
    except jwt.InvalidTokenError:
        raise _unauthorized("유효하지 않은 인증 토큰입니다")

    # 3) sub → 정수 사용자 ID 로 변환 후 DB 조회
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise _unauthorized("유효하지 않은 인증 토큰입니다")

    # db.get(모델, 기본키): 기본키로 한 건 조회. 없으면 None.
    user = db.get(User, user_id)
    if user is None:
        # 토큰은 진짜인데 그 사이 계정이 삭제된 경우 등
        raise _unauthorized("사용자를 찾을 수 없습니다")

    # 4) 비활성 계정 차단
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다",
        )

    return user


def get_current_student(user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    학과·학위과정이 있는 계정(학생)만 통과시키는 의존성 함수.

    과목 목록·진단처럼 "내 학과의 교육과정" 이 있어야 하는 API 에 붙입니다.
    관리자 계정은 학과가 없으므로 400 으로 막습니다.
    (권한 문제라기보다 '이 계정으로는 계산할 재료가 없다' 는 뜻이라 403 대신 400)
    """
    if user.department_id is None or user.program_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="학생 계정만 사용할 수 있습니다",
        )
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    관리자만 통과시키는 의존성 함수.

    get_current_user 를 먼저 거치므로 로그인·활성 여부 검사는 이미 끝난 상태입니다.
    여기서는 role 만 확인합니다. role 은 토큰 payload 가 아니라 DB 에서 방금 읽은 값을
    쓰므로, 관리자 권한을 회수하면 기존 토큰으로도 즉시 관리자 기능을 못 쓰게 됩니다.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다",
        )
    return user
