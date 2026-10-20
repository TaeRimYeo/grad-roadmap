"""
메타(기준 정보) API 라우터.

    GET /api/meta/signup-options  회원가입 화면 드롭다운 선택지

'메타' 란? 학생 개인 데이터가 아니라 대학교·학과·학위과정·세부전공처럼
모든 사용자에게 똑같이 보이는 '기준 정보' 를 말합니다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import Department, Major, Program, University
from schemas import SignupOptionsResponse

router = APIRouter(prefix="/api/meta", tags=["메타"])


@router.get("/signup-options", response_model=SignupOptionsResponse)
def get_signup_options(db: Annotated[Session, Depends(get_db)]):
    """
    회원가입 드롭다운에 들어갈 선택지를 한 번에 돌려줍니다.

    [인증 없이 호출 가능]
    회원가입은 '아직 로그인하지 않은 사람' 이 하는 것이므로
    get_current_user 의존성을 붙이지 않습니다. (비밀 정보가 없는 공개 데이터)

    [한 번에 네 목록을 다 주는 이유]
    학과 → 과정/전공 처럼 고를 때마다 서버에 다시 묻지 않아도 되도록,
    각 항목에 부모 ID(university_id, department_id)를 붙여 전부 내려줍니다.
    데이터가 몇 줄 안 되므로 한 번에 보내는 편이 빠르고 프론트 코드도 단순합니다.
    """
    # select(모델).order_by(모델.id) : 해당 테이블 전체를 id 순서대로 조회.
    #   정렬을 안 하면 DB 가 돌려주는 순서가 매번 같다는 보장이 없어서
    #   드롭다운 항목 순서가 들쭉날쭉해질 수 있습니다.
    # db.scalars(...).all() : 결과를 모델 객체 리스트로 받음 (예: [University, ...])
    universities = db.scalars(select(University).order_by(University.id)).all()
    departments = db.scalars(select(Department).order_by(Department.id)).all()
    programs = db.scalars(select(Program).order_by(Program.id)).all()
    majors = db.scalars(select(Major).order_by(Major.id)).all()

    # SQLAlchemy 객체 리스트를 그대로 담아 돌려주면, response_model(SignupOptionsResponse)이
    # 각 객체에서 스키마에 적힌 필드(id, name, 부모 ID)만 골라 JSON 으로 만들어줍니다.
    # → Program 의 total_terms, University 의 created_at 등은 응답에 나가지 않습니다.
    return {
        "universities": universities,
        "departments": departments,
        "programs": programs,
        "majors": majors,
    }
