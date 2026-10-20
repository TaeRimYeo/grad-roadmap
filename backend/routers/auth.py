"""
인증 API 라우터: 회원가입 / 로그인 / 내 정보.

    POST /api/auth/signup  (201)  회원가입
    POST /api/auth/login   (200)  로그인 → JWT 발급
    GET  /api/auth/me      (200)  내 정보 (로그인 필요)

[파일 이름 주의]
backend/auth.py        : 해싱·JWT·의존성 같은 '도구' 모음
backend/routers/auth.py: 그 도구를 써서 실제 API 주소를 만드는 '라우터' (이 파일)
이 파일 안의 `from auth import ...` 는 backend/auth.py 를 가리킵니다.
(이 파일 자신은 routers.auth 라는 이름이라 서로 헷갈리지 않습니다)
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, hash_password, verify_password
from db import get_db
from models import Department, Major, Program, User
from schemas import (
    LoginRequest,
    MeResponse,
    SignupRequest,
    SignupResponse,
    TokenResponse,
    UserBrief,
)

# prefix : 이 라우터의 모든 주소 앞에 자동으로 붙는 공통 경로
# tags   : /docs 화면에서 API 를 묶어 보여줄 그룹 이름
router = APIRouter(prefix="/api/auth", tags=["인증"])

# 명세에 정해진 오류 메시지는 오타가 나지 않도록 상수로 한 번만 적어둡니다.
EMAIL_TAKEN_MSG = "이미 가입된 이메일입니다"
LOGIN_FAILED_MSG = "이메일 또는 비밀번호가 올바르지 않습니다"

# 타이밍 공격 방지용 '가짜 해시' (아래 login 함수 설명 참고).
# 서버가 켜질 때 딱 한 번만 만들어 두고 계속 재사용합니다.
_DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing-0")


def _invalid_input(detail: str) -> HTTPException:
    """422(입력 형식 오류)를 한국어 메시지로 만드는 작은 도우미."""
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


# =========================================================================
# 1. 회원가입
# =========================================================================


@router.post(
    "/signup",
    # status_code=201 : "새 자원이 만들어졌다" 는 뜻. 가입 성공 시 200 대신 201 을 돌려줍니다.
    status_code=status.HTTP_201_CREATED,
    # response_model : 응답을 이 모양으로 걸러서 내보냄 → password_hash 가 절대 안 나감
    response_model=SignupResponse,
)
def signup(body: SignupRequest, db: Annotated[Session, Depends(get_db)]):
    """
    회원가입.

    body 는 이미 schemas.SignupRequest 검사(이메일 형식, 비밀번호 규칙 등)를 통과한 값입니다.
    여기서는 'DB 를 봐야만 알 수 있는' 것들만 검사합니다.
        1) 이메일 중복          → 409
        2) 학과/과정/전공 ID 가 실제로 있고, 서로 맞는 조합인지 → 422
    """
    # ---------------------------------------------------------------
    # 1) 이메일 중복 확인
    # ---------------------------------------------------------------
    # select(User.id).where(...) : "이 이메일을 가진 사용자의 id 를 찾아라"
    # db.scalar(...)             : 결과 첫 번째 값 하나만 꺼냄. 없으면 None.
    # (schemas 에서 이미 소문자로 바꿨으므로 그대로 비교하면 됩니다)
    if db.scalar(select(User.id).where(User.email == body.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN_MSG)

    # ---------------------------------------------------------------
    # 2) 소속 정보 확인 (다학과 구조 대비)
    # ---------------------------------------------------------------
    # db.get(모델, ID) : 기본키로 한 건 조회. 없으면 None.
    department = db.get(Department, body.department_id)
    if department is None:
        raise _invalid_input("존재하지 않는 학과입니다")

    # 학위과정·세부전공은 '존재하는지' 뿐 아니라 '고른 학과 소속인지' 도 봐야 합니다.
    # 예) A학과를 고르고 B학과의 전공 ID 를 보내는 잘못된 조합을 막음.
    program = db.get(Program, body.program_id)
    if program is None or program.department_id != department.id:
        raise _invalid_input("선택한 학과에 없는 학위과정입니다")

    major = db.get(Major, body.major_id)
    if major is None or major.department_id != department.id:
        raise _invalid_input("선택한 학과에 없는 세부전공입니다")

    # ---------------------------------------------------------------
    # 3) 사용자 저장
    # ---------------------------------------------------------------
    user = User(
        email=body.email,
        # 평문 비밀번호는 절대 저장하지 않고, 해시값만 저장합니다.
        password_hash=hash_password(body.password),
        name=body.name,
        # role 은 요청값과 상관없이 서버가 무조건 'student' 로 고정합니다.
        # (SignupRequest 에 role 필드가 없어서 애초에 요청값이 들어오지도 않습니다)
        role="student",
        # 대학교는 요청으로 받지 않고, 고른 학과가 속한 대학교로 자동으로 채웁니다.
        university_id=department.university_id,
        department_id=department.id,
        program_id=program.id,
        major_id=major.id,
        admission_year=body.admission_year,
        student_no=body.student_no,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # 위의 중복 확인과 commit 사이의 아주 짧은 틈에 같은 이메일로 동시에 가입하면
        # DB 의 unique 제약에 걸려 여기로 옵니다. 이 경우도 똑같이 409 로 응답합니다.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN_MSG)

    # refresh : DB 가 채워준 값(자동 증가 id, created_at 등)을 user 객체에 다시 읽어옴
    db.refresh(user)
    # User 객체를 그대로 돌려줘도 response_model(SignupResponse)이 4개 필드만 골라 내보냅니다.
    return user


# =========================================================================
# 2. 로그인
# =========================================================================


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    """
    로그인. 성공하면 액세스 토큰(JWT)과 간단한 사용자 정보를 돌려줍니다.

    [보안] 실패 이유를 구분하지 않습니다.
      "없는 이메일입니다" / "비밀번호가 틀렸습니다" 로 나눠 알려주면, 공격자가
      어떤 이메일이 가입돼 있는지 알아낼 수 있습니다. 그래서 둘 다 같은 401 메시지를 씁니다.
    """
    user = db.scalar(select(User).where(User.email == body.email))

    # [타이밍 공격 방지]
    # 이메일이 없을 때 바로 실패 처리하면 응답이 아주 빠르고,
    # 이메일이 있으면 Argon2 검사 때문에 느려집니다 → 시간 차이로 가입 여부가 드러남.
    # 그래서 사용자가 없어도 가짜 해시로 검사를 한 번 똑같이 돌려서 시간을 맞춥니다.
    if user is None:
        verify_password(body.password, _DUMMY_PASSWORD_HASH)
        password_ok = False
    else:
        password_ok = verify_password(body.password, user.password_hash)

    if not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=LOGIN_FAILED_MSG,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 비밀번호까지 맞았는데 비활성 계정이면 토큰을 주지 않습니다.
    # (토큰을 줘도 /me 등에서 어차피 403 이 나므로, 여기서 미리 알려주는 게 친절합니다.
    #  비밀번호를 아는 본인에게만 보이는 메시지라 가입 여부 노출 문제도 없습니다)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 계정입니다")

    # 마지막 로그인 시각 갱신. 서버 시간대와 무관하게 UTC 로 저장합니다.
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user),
        # model_validate(user) : SQLAlchemy User 객체에서 id·name·role 만 뽑아 UserBrief 로 변환
        user=UserBrief.model_validate(user),
    )


# =========================================================================
# 3. 내 정보
# =========================================================================


@router.get("/me", response_model=MeResponse)
def read_me(user: Annotated[User, Depends(get_current_user)]):
    """
    내 정보 조회.

    Depends(get_current_user) 가 토큰 검사(401)와 비활성 계정 검사(403)를
    모두 끝내고 '로그인한 사용자' 를 넣어주므로, 여기서는 응답만 만들면 됩니다.

    학과·과정·전공은 ID 가 아니라 이름으로 내려줍니다.
    user.department 처럼 relationship 으로 연결된 객체에서 .name 을 꺼내고,
    관리자처럼 소속이 없는 계정(None)은 None 그대로 둡니다.
    """
    return MeResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        student_no=user.student_no,
        admission_year=user.admission_year,
        department=user.department.name if user.department else None,
        program=user.program.name if user.program else None,
        major=user.major.name if user.major else None,
    )
