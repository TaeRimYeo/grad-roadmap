"""
학점 요약 API 라우터.

    GET /api/grades/summary  (200)  전체·전공 평점, 학기별 평점·취득학점, 이수구분별 학점

계산은 전부 backend/grades.py(순수 함수)가 합니다.
이 파일은 DB 에서 내 이수 내역을 읽어 grades.summarize() 에 넘기기만 합니다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_user
from db import get_db
from grades import summarize
from models import User
from routers.completed import load_completed_rows

router = APIRouter(prefix="/api/grades", tags=["학점"])


@router.get("/summary")
def grade_summary(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """학점 요약. 응답 모양은 docs/api.md 의 GET /api/grades/summary 참고."""
    items = [
        {
            "credits": row.credits,
            "category": row.category,
            "grade": row.grade,
            "taken_year": row.taken_year,
            "taken_semester": row.taken_semester,
        }
        for row in load_completed_rows(db, user)
    ]
    return summarize(items)
