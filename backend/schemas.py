"""
API 요청/응답의 '모양'을 정의하는 모듈 (Pydantic 모델).

models.py 와의 차이 (초보자용):
  - models.py  : DB 테이블 모양 (SQLAlchemy). password_hash 처럼 밖에 보이면 안 되는 값도 있다.
  - schemas.py : API 로 주고받는 JSON 모양 (Pydantic). 클라이언트가 보내도 되는 값,
                 클라이언트에게 보여줘도 되는 값만 골라서 정의한다.

FastAPI 는 라우터 함수의 매개변수 타입이 Pydantic 모델이면
  1) 요청 JSON 을 이 모델로 변환하면서 타입·형식을 검사하고
  2) 검사에 실패하면 라우터 함수를 실행하지 않고 바로 422 응답을 보냅니다.
그래서 라우터 안에서는 "값이 이미 올바르다" 고 믿고 로직만 짜면 됩니다.
"""

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic_core import PydanticCustomError

# =========================================================================
# 0. 공통 도우미
# =========================================================================


def _normalize_email(value: str) -> str:
    """
    이메일 앞뒤 공백 제거 + 소문자 통일.

    이렇게 하지 않으면 'Kim@Test.com' 과 'kim@test.com' 이 서로 다른 계정으로
    가입될 수 있고, 로그인할 때도 대소문자를 정확히 맞춰야 하는 불편이 생깁니다.
    가입(SignupRequest)과 로그인(LoginRequest) 양쪽에 똑같이 적용해야 서로 맞습니다.
    """
    return value.strip().lower()


# =========================================================================
# 1. 요청(Request) 스키마 : 클라이언트 → 서버
# =========================================================================


class SignupRequest(BaseModel):
    """
    회원가입 요청.

    [role 이 없는 이유]
    Pydantic 은 기본적으로 모델에 정의되지 않은 필드를 '조용히 버립니다'.
    그래서 누군가 요청에 "role": "admin" 을 끼워 보내도 이 모델에는 들어오지 않고,
    서버(라우터)가 무조건 'student' 로 저장합니다. → 스스로 관리자가 되는 것 차단.
    """

    # EmailStr: '아이디@도메인' 형식인지 검사해주는 특수 타입 (email-validator 패키지 필요)
    # max_length 는 DB 컬럼 길이(String(255))와 맞춰서, DB 에러가 나기 전에 미리 걸러냅니다.
    email: EmailStr = Field(max_length=255, description="로그인용 이메일")
    # 비밀번호 상세 규칙은 아래 validate_password 에서 검사합니다.
    # max_length=128: 너무 긴 문자열을 해싱시키면 서버가 느려질 수 있어서 상한을 둡니다.
    password: str = Field(max_length=128, description="8자 이상, 영문+숫자 포함")
    name: str = Field(min_length=1, max_length=50, description="이름")
    # 학번은 계산에 쓰지 않고 앞자리 0 이 있을 수도 있어서 문자열 (models.User.student_no 참고)
    student_no: str = Field(min_length=1, max_length=20, description="학번")
    # gt=0 : 0 보다 커야 함. DB 의 ID 는 1 부터 시작하므로 0·음수는 형식 오류(422)로 바로 거릅니다.
    # "형식은 맞지만 DB 에 없는 ID" 인지는 여기서 알 수 없으므로 라우터에서 DB 를 조회해 확인합니다.
    department_id: int = Field(gt=0, description="학과 ID (signup-options 에서 받은 값)")
    program_id: int = Field(gt=0, description="학위과정 ID (전문학사/전공심화)")
    major_id: int = Field(gt=0, description="세부전공 ID")
    admission_year: int = Field(ge=2000, le=2100, description="입학년도 (예: 2024)")

    # ---------------------------------------------------------------------
    # 필드 검증기(field_validator)
    #   "이 필드 값이 들어오면 이 함수를 한 번 거쳐라" 라는 뜻입니다.
    #   mode="before" : 타입 검사 '전에' 실행 (원본 값을 다듬을 때)
    #   mode="after"  : 타입 검사 '후에' 실행 (기본값. 이미 str 로 확정된 값을 검사할 때)
    # ---------------------------------------------------------------------

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        # 문자열이 아닌 값(숫자 등)은 건드리지 않고 EmailStr 검사에 맡깁니다.
        return _normalize_email(value) if isinstance(value, str) else value

    @field_validator("name", "student_no", mode="before")
    @classmethod
    def strip_text(cls, value):
        # "  홍길동  " → "홍길동". 공백만 있는 값은 빈 문자열이 되어 min_length=1 에 걸립니다.
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """
        비밀번호 규칙: 8자 이상 + 영문 1자 이상 + 숫자 1자 이상.

        [ValueError 대신 PydanticCustomError 를 쓰는 이유]
        ValueError("메시지") 로 던지면 응답 메시지가 "Value error, 메시지" 처럼
        영어 접두어가 붙어서 나갑니다. PydanticCustomError 는 우리가 쓴 문장이
        그대로 msg 에 들어가서 프론트에서 바로 화면에 보여주기 좋습니다.
          첫 번째 인자 : 에러 종류 이름(type). 프론트가 에러를 구분할 때 쓸 수 있음
          두 번째 인자 : 사용자에게 보여줄 메시지
        """
        if len(value) < 8:
            raise PydanticCustomError("password_too_short", "비밀번호는 8자 이상이어야 합니다")
        # re.search: 문자열 어딘가에 패턴이 하나라도 있으면 매치
        #   [A-Za-z] = 영문 대소문자 한 글자
        #   \d       = 숫자 한 글자
        if not re.search(r"[A-Za-z]", value):
            raise PydanticCustomError("password_no_letter", "비밀번호에 영문자를 1자 이상 포함해야 합니다")
        if not re.search(r"\d", value):
            raise PydanticCustomError("password_no_digit", "비밀번호에 숫자를 1자 이상 포함해야 합니다")
        return value


class LoginRequest(BaseModel):
    """
    로그인 요청.

    비밀번호 규칙(8자 이상 등)은 여기서 검사하지 않습니다.
    규칙을 검사하면 "형식이 틀렸다(422)" 와 "비밀번호가 틀렸다(401)" 가 구분되어
    불필요한 정보를 주게 되고, 나중에 규칙이 바뀌었을 때 기존 사용자가 로그인을 못 하게 됩니다.
    로그인에서는 "DB 에 저장된 해시와 맞는가" 만 보면 충분합니다.
    """

    email: EmailStr
    password: str = Field(max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        # 가입할 때와 똑같이 소문자로 맞춰야 같은 계정을 찾을 수 있습니다.
        return _normalize_email(value) if isinstance(value, str) else value


# =========================================================================
# 2. 응답(Response) 스키마 : 서버 → 클라이언트
# =========================================================================


class SignupResponse(BaseModel):
    """
    회원가입 성공(201) 응답.

    라우터가 SQLAlchemy User 객체를 그대로 return 해도, response_model 로 이 스키마를
    지정해두면 FastAPI 가 여기 적힌 4개 필드만 골라서 JSON 으로 내보냅니다.
    → password_hash 같은 값이 실수로 응답에 섞여 나갈 일이 없습니다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: str  # 가입 직후에는 항상 'student'


class UserBrief(BaseModel):
    """로그인 응답에 함께 실어 보내는 최소한의 사용자 정보."""

    # from_attributes=True:
    #   dict 뿐 아니라 SQLAlchemy 객체(User)의 속성(user.id, user.name ...)에서도
    #   값을 읽어 올 수 있게 해줍니다. → UserBrief.model_validate(user) 로 바로 변환 가능.
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: str  # 'student' | 'admin'


class TokenResponse(BaseModel):
    """로그인 성공 응답."""

    access_token: str
    # OAuth2 표준 관례상 소문자 "bearer". 프론트는 요청 헤더에
    # "Authorization: Bearer <access_token>" 형태로 붙여 보내면 됩니다.
    token_type: str = "bearer"
    user: UserBrief


class MeResponse(BaseModel):
    """
    GET /api/auth/me 응답 = 내 정보.

    department / program / major 는 ID 가 아니라 '이름 문자열' 로 내려줍니다.
    (화면에 바로 표시하기 위함. 라우터에서 user.department.name 등으로 채웁니다)

    관리자 계정은 학번·소속이 없을 수 있으므로(models.User 에서 nullable)
    해당 필드들은 None(JSON 에서는 null) 을 허용합니다.
    """

    id: int
    email: str
    name: str
    role: str
    student_no: str | None = None
    admission_year: int | None = None
    department: str | None = None  # 예: "컴퓨터모바일융합과"
    program: str | None = None  # 예: "전문학사"
    major: str | None = None  # 예: "SW융합전공"


# =========================================================================
# 3. 메타(드롭다운 선택지) 스키마 : GET /api/meta/signup-options
# =========================================================================
#
# 회원가입 화면의 드롭다운(대학교 → 학과 → 학위과정/세부전공)을 채우는 데이터입니다.
# 각 항목이 '부모 ID'(university_id, department_id)를 함께 갖고 있어서,
# 프론트는 "학과를 고르면 그 학과의 학위과정·세부전공만 보여주기" 를
# 서버에 다시 묻지 않고 filter 한 번으로 처리할 수 있습니다.
# (다학과 구조: 학과가 늘어나도 이 응답 모양은 그대로입니다)


class UniversityOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str  # 예: "경기과학기술대학교"


class DepartmentOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    university_id: int  # 어느 대학교의 학과인지
    name: str  # 예: "컴퓨터모바일융합과"


class ProgramOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int  # 어느 학과의 학위과정인지
    name: str  # 예: "전문학사", "전공심화"


class MajorOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int  # 어느 학과의 세부전공인지
    name: str  # 예: "SW융합전공", "게임개발전공"


class SignupOptionsResponse(BaseModel):
    """GET /api/meta/signup-options 응답 전체."""

    universities: list[UniversityOption]
    departments: list[DepartmentOption]
    programs: list[ProgramOption]
    majors: list[MajorOption]
