"""
졸업 진단 API 라우터.

    POST /api/diagnose  (200)  이수 내역 → 남은 학점·미이수 전필·들을 수 있는 과목·가상 과목

[역할 나누기]
    계산은 전부 backend/diagnose.py(순수 함수)가 합니다. 이 파일은
        1) 로그인한 사용자의 학위과정·전공 확인
        2) DB 에서 과목·선수과목·졸업요건을 읽어 diagnose() 가 받는 모양(dict)으로 바꾸기
        3) 결과에 가상 과목(placeholder)을 붙여 응답 만들기
    만 합니다. 그래서 계산 규칙을 고칠 때는 이 파일이 아니라 diagnose.py 를 고칩니다.

[파일 이름 주의]
    backend/diagnose.py         : 계산 로직 (이 파일 안의 `from diagnose import diagnose`)
    backend/routers/diagnose.py : API 주소 (이 파일, routers.diagnose 라는 이름)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from auth import get_current_user
from db import get_db
from diagnose import diagnose
from models import Course, Curriculum, Prerequisite, Requirement, RequirementCategory, User
from placeholder import make_placeholders
from schemas import DiagnoseRequest

router = APIRouter(prefix="/api", tags=["진단"])

# 이번 단계에서는 전공심화 진단을 지원하지 않습니다.
ADVANCED_PROGRAM = "전공심화"


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


# =========================================================================
# DB 읽기 도우미
# =========================================================================


def _find_curriculum(db: Session, user: User) -> Curriculum:
    """
    사용자에게 적용할 교육과정을 고릅니다.

        1순위: 같은 학위과정 + 같은 입학년도
        2순위: 같은 학위과정의 가장 최근 교육과정
               (아직 해당 입학년도 교육과정이 DB 에 등록되지 않은 경우를 위한 대비)
    """
    curricula = db.scalars(
        select(Curriculum)
        .where(Curriculum.program_id == user.program_id, Curriculum.status == "active")
        .order_by(Curriculum.admission_year.desc())
    ).all()
    if not curricula:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="적용할 교육과정이 없습니다")

    for curriculum in curricula:
        if curriculum.admission_year == user.admission_year:
            return curriculum
    return curricula[0]  # 입학년도 내림차순이므로 첫 번째가 가장 최근


def _load_courses(db: Session, curriculum: Curriculum) -> list[dict]:
    """교육과정의 실제 과목(가상 과목 제외)을 diagnose() 가 받는 dict 모양으로 읽습니다."""
    rows = db.scalars(
        select(Course)
        .where(Course.curriculum_id == curriculum.id, Course.is_placeholder.is_(False))
        .order_by(Course.code)
    ).all()
    program_name = curriculum.program.name
    return [
        {
            "code": c.code,
            "name": c.name,
            "program": program_name,
            "major": c.major,
            "category": c.category,
            "credits": c.credits,
            "offered": c.offered,
            "term_index": c.term_index,
        }
        for c in rows
    ]


def _load_prereqs(db: Session, curriculum: Curriculum) -> list[tuple[str, str]]:
    """
    선수과목 관계를 (선수 code, 후수 code) 목록으로 읽습니다.

    [aliased 가 필요한 이유]
        prerequisites 한 행에는 과목 ID 가 두 개(course_id, prereq_course_id) 있습니다.
        각각의 code 를 얻으려면 courses 테이블을 '두 번' 붙여야 하는데,
        같은 테이블을 두 번 쓰려면 서로 다른 별명(After, Before)을 붙여 구분해야 합니다.
    """
    After = aliased(Course)  # 후수과목 (들으려는 과목)
    Before = aliased(Course)  # 선수과목 (먼저 들어야 하는 과목)
    rows = db.execute(
        select(Before.code, After.code)
        # 고르는 열(Before.code, After.code)에 prerequisites 가 없으므로
        # "prerequisites 테이블에서 출발해 join 한다" 고 직접 알려줘야 합니다.
        .select_from(Prerequisite)
        .join(After, Prerequisite.course_id == After.id)
        .join(Before, Prerequisite.prereq_course_id == Before.id)
        .where(After.curriculum_id == curriculum.id)
    ).all()
    return [(before, after) for before, after in rows]


def _load_requirement(db: Session, curriculum: Curriculum, courses: list[dict]) -> dict:
    """
    졸업요건을 diagnose() 가 받는 모양으로 만듭니다.

        total_credits    : requirements.total_credits
        major_min        : requirement_categories 의 '전공' 행 (전필+전선 합산 최소학점)
        required_courses : 이 교육과정에서 이수구분이 '전공필수' 인 과목 code 목록
                           (전필 목록을 따로 저장하는 테이블이 없으므로 과목의 이수구분으로 판단)
    """
    requirement = db.scalar(select(Requirement).where(Requirement.curriculum_id == curriculum.id))
    if requirement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="적용할 교육과정이 없습니다")

    major_min = db.scalar(
        select(RequirementCategory.min_credits).where(
            RequirementCategory.requirement_id == requirement.id,
            RequirementCategory.category == "전공",
        )
    )
    return {
        "total_credits": requirement.total_credits,
        "major_min": major_min or 0,  # '전공' 요건이 없는 학과라면 0 으로 봄
        "required_courses": [c["code"] for c in courses if c["category"] == "전공필수"],
    }


# =========================================================================
# API
# =========================================================================


@router.post("/diagnose")
def post_diagnose(
    body: DiagnoseRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    졸업 진단. 응답 모양은 docs/api.md 의 POST /api/diagnose 참고.

    학위과정·세부전공은 요청이 아니라 토큰의 사용자 정보(user)에서 가져옵니다.
    (요청으로 받으면 다른 전공으로 바꿔 보내는 등 사용자 정보와 어긋날 수 있음)
    """
    # ---- 1) 사용자 확인 ----
    if user.program is None or user.major is None:
        raise _bad_request("학위과정·세부전공 정보가 없는 계정입니다")
    if user.program.name == ADVANCED_PROGRAM:
        raise _bad_request("전공심화 과정 진단은 준비 중입니다")

    # ---- 2) DB 읽기 ----
    curriculum = _find_curriculum(db, user)
    courses = _load_courses(db, curriculum)
    prereqs = _load_prereqs(db, curriculum)
    requirement = _load_requirement(db, curriculum, courses)

    # ---- 3) 계산 (diagnose.py) ----
    result = diagnose(courses, prereqs, requirement, body.to_plain(), user.major.name)

    # DB 에 없는 과목코드가 하나라도 있으면 계산 결과를 믿을 수 없으므로 422
    if result["unknown_codes"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="존재하지 않는 과목입니다: " + ", ".join(result["unknown_codes"]),
        )

    # ---- 4) 응답 조립: 가상 과목은 free_needed(아무 과목으로 채워도 되는 학점) 기준 ----
    result["placeholders"] = make_placeholders(result["free_needed"])
    return result
