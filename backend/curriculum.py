"""
교육과정·과목·졸업요건을 DB 에서 읽어오는 도우미 모음.

[이 파일을 따로 둔 이유]
    진단(routers/diagnose.py), 이수 내역(routers/completed.py), 과목 목록(routers/courses.py)이
    모두 "이 학생에게 적용할 교육과정은 무엇이고, 그 안의 과목은 무엇인가" 를 알아야 합니다.
    각 라우터에 같은 코드를 복사하지 않고 여기 한 곳에 둡니다.

[diagnose.py 와의 차이]
    backend/diagnose.py : 계산만 하는 순수 함수 (DB·FastAPI 모름)
    backend/curriculum.py (이 파일) : DB 에서 읽어서 diagnose() 가 받는 dict 모양으로 바꿈
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from models import Course, Curriculum, Prerequisite, Requirement, RequirementCategory, User


def find_curriculum(db: Session, user: User) -> Curriculum:
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


def load_courses(db: Session, curriculum: Curriculum) -> list[dict]:
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


def load_prereqs(db: Session, curriculum: Curriculum) -> list[tuple[str, str]]:
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


def load_requirement(db: Session, curriculum: Curriculum, courses: list[dict]) -> dict:
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
