"""
과목 목록 API 라우터.

    GET /api/courses  (200)  내 학과·전공에서 고를 수 있는 과목 목록

이수 내역을 입력하는 화면에서 "어떤 과목을 들었는지" 고를 때 씁니다.
    - 공통 + 내 전공 과목만 (다른 전공 과목은 제외)
    - 가상 과목(is_placeholder) 제외
    - completed: 내 이수 내역에 이미 등록된 과목이면 true (F 로 등록된 과목도 true)
                 → 화면에서 '등록됨' 표시, 중복 추가(409) 방지에 사용
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import get_current_student
from curriculum import find_curriculum
from db import get_db
from diagnose import COMMON_MAJOR, OFFERED_LABELS
from models import CompletedCourse, Course, User

router = APIRouter(prefix="/api", tags=["과목"])


@router.get("/courses")
def list_courses(
    user: Annotated[User, Depends(get_current_student)],
    db: Annotated[Session, Depends(get_db)],
):
    """내 교육과정의 공통 + 내 전공 과목 (학기 순 → 과목코드 순)."""
    curriculum = find_curriculum(db, user)
    majors = [COMMON_MAJOR] + ([user.major.name] if user.major else [])

    courses = db.scalars(
        select(Course)
        .where(
            Course.curriculum_id == curriculum.id,
            Course.is_placeholder.is_(False),
            Course.major.in_(majors),
        )
        # nulls_last: 학기 번호가 없는 과목은 맨 뒤로
        .order_by(Course.term_index.asc().nulls_last(), Course.code)
    ).all()

    # 내가 이미 등록한 과목 ID 집합
    taken_ids = set(
        db.scalars(
            select(CompletedCourse.course_id).where(
                CompletedCourse.user_id == user.id, CompletedCourse.course_id.is_not(None)
            )
        )
    )

    return [
        {
            "code": c.code,
            "name": c.name,
            "major": c.major,
            "category": c.category,
            "credits": c.credits,
            "offered": c.offered,
            "offered_label": OFFERED_LABELS.get(c.offered, "미정"),
            "term_index": c.term_index,
            "completed": c.id in taken_ids,
        }
        for c in courses
    ]
