"""
이수 내역(들은 과목·성적) 저장 API 라우터.

    GET    /api/completed          (200)  내 이수 내역 목록 (학년·학기 순)
    POST   /api/completed          (201)  1과목 추가
    POST   /api/completed/bulk     (201)  같은 학기 과목 여러 개 한 번에 추가
    PATCH  /api/completed/{id}     (200)  성적·시기 수정
    DELETE /api/completed/{id}     (204)  삭제

[자기 데이터만 접근하기]
    모든 조회에 "user_id == 로그인한 사람" 조건을 붙입니다.
    남의 id 로 수정·삭제하면 '그런 행이 없다' 와 똑같이 404 를 돌려줍니다.
    (403 을 주면 "그 id 의 이수 내역이 존재는 한다" 는 정보가 새어 나가기 때문)

[중복 등록 막기]
    - 학과 과목  : 같은 course_id 가 이미 있으면 409
    - 직접 입력  : 공백을 모두 지운 이름이 같으면 409 ('글 쓰기' = '글쓰기')
    재수강은 새로 추가하지 않고 PATCH 로 성적을 바꿉니다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from auth import get_current_student, get_current_user
from curriculum import find_curriculum
from db import get_db
from grades import term_sort_key
from models import CompletedCourse, Course, User
from schemas import CompletedBulkItem, CompletedBulkRequest, CompletedCreate, CompletedUpdate

router = APIRouter(prefix="/api/completed", tags=["이수 내역"])

DUPLICATE_MESSAGE = "이미 등록된 과목입니다"


# =========================================================================
# 도우미 함수
# =========================================================================


def to_taken_term(year: int, semester: str) -> int:
    """
    학년·학기 → 통합 학기 번호(taken_term). 1학년 1학기=1, 1학년 2학기=2, 2학년 1학기=3 ...

    [학과 확인 필요] 계절학기 변환은 아직 학과에 확인하지 않은 '임시 규칙' 입니다.
        여름 → 그 학년 1학기 번호,  겨울 → 그 학년 2학기 번호
        (예: 1학년 여름 → 1,  1학년 겨울 → 2)
    학과 답변에 따라 바뀔 수 있습니다. 바뀌면 이 함수와 docs/api.md 를 함께 고치세요.
    """
    base = (year - 1) * 2
    if semester in ("1", "여름"):  # 학과 확인 필요: 여름 → 1학기
        return base + 1
    return base + 2  # "2", "겨울" (학과 확인 필요: 겨울 → 2학기)


def name_key(name: str) -> str:
    """
    직접 입력 과목 이름 비교용 값. 앞뒤·중간 공백을 모두 지웁니다.
        "  글 쓰기 " → "글쓰기"
    (DB 인덱스 uq_completed_user_custom_name 도 같은 규칙: scripts/migrate_completed_grades.py)
    """
    return "".join(name.split())


def load_completed_rows(db: Session, user: User) -> list[CompletedCourse]:
    """
    내 이수 내역 전체를 학년·학기 순으로 읽습니다. (같은 학기 안에서는 등록 순)
    진단(GET /api/diagnose/me)과 학점 요약(GET /api/grades/summary)도 이 함수를 씁니다.

    joinedload: 과목(course) 정보를 한 번의 쿼리로 같이 가져옵니다.
                (없으면 행마다 row.course 를 읽을 때 쿼리가 한 번씩 더 나감)
    """
    rows = db.scalars(
        select(CompletedCourse)
        .options(joinedload(CompletedCourse.course))
        .where(CompletedCourse.user_id == user.id)
        .order_by(CompletedCourse.id)
    ).all()
    # 학기 순서(1 → 여름 → 2 → 겨울)는 문자열 정렬로 안 되므로 파이썬에서 정렬합니다.
    # sorted 는 순서가 같은 항목끼리는 원래 순서(id 순)를 유지합니다.
    return sorted(rows, key=lambda r: term_sort_key(r.taken_year or 0, r.taken_semester or ""))


def to_response(row: CompletedCourse) -> dict:
    """DB 행 → 응답 JSON 한 건."""
    course = row.course
    return {
        "id": row.id,
        "code": course.code if course else None,  # 직접 입력 과목은 null
        "name": course.name if course else row.custom_name,
        "major": course.major if course else None,
        "category": row.category,
        "credits": row.credits,
        "taken_year": row.taken_year,
        "taken_semester": row.taken_semester,
        "grade": row.grade,
        "is_custom": course is None,
    }


def _get_my_row(db: Session, user: User, completed_id: int) -> CompletedCourse:
    """내 이수 내역 한 건. 없거나 남의 것이면 똑같이 404."""
    row = db.scalar(
        select(CompletedCourse).where(CompletedCourse.id == completed_id, CompletedCourse.user_id == user.id)
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="이수 내역을 찾을 수 없습니다")
    return row


def _create_rows(
    db: Session, user: User, items: list[CompletedBulkItem], taken_year: int, taken_semester: str
) -> list[CompletedCourse]:
    """
    POST 1과목·bulk 공통 저장 로직. 하나라도 문제가 있으면 아무것도 저장하지 않습니다.

        1) code 를 내 교육과정 과목에서 찾기    → 없으면 422
        2) 이미 등록됐거나, 요청 안에서 겹치면  → 409 (겹친 과목을 메시지에 표시)
        3) 전부 통과하면 한 번에 commit
    """
    # ---- 내 교육과정의 실제 과목 (code → Course) ----
    # 다른 전공 과목도 등록할 수 있습니다 (전공 구분은 soft 규칙). 가상 과목은 '들은 과목' 이 될 수 없으므로 제외.
    curriculum = find_curriculum(db, user)
    course_by_code = {
        c.code: c
        for c in db.scalars(
            select(Course).where(Course.curriculum_id == curriculum.id, Course.is_placeholder.is_(False))
        )
    }

    # ---- 이미 등록된 과목 ----
    existing = db.scalars(select(CompletedCourse).where(CompletedCourse.user_id == user.id)).all()
    taken_course_ids = {r.course_id for r in existing if r.course_id is not None}
    taken_name_keys = {name_key(r.custom_name) for r in existing if r.course_id is None and r.custom_name}

    unknown_codes: list[str] = []
    duplicates: list[str] = []  # 409 메시지에 보여줄 code 또는 과목명
    rows: list[CompletedCourse] = []
    taken_term = to_taken_term(taken_year, taken_semester)

    for item in items:
        if item.code:
            # ---- 학과 과목: 학점·이수구분은 과목표 값을 복사해 둡니다 ----
            course = course_by_code.get(item.code)
            if course is None:
                unknown_codes.append(item.code)
                continue
            if course.id in taken_course_ids:
                duplicates.append(item.code)
                continue
            taken_course_ids.add(course.id)  # 같은 요청 안에서 또 나오면 중복으로 잡히게
            rows.append(
                CompletedCourse(
                    user_id=user.id,
                    course_id=course.id,
                    credits=course.credits,
                    category=course.category,
                    taken_term=taken_term,
                    taken_year=taken_year,
                    taken_semester=taken_semester,
                    grade=item.grade,
                )
            )
        else:
            # ---- 직접 입력 과목 ----
            key = name_key(item.name)
            if key in taken_name_keys:
                duplicates.append(item.name)
                continue
            taken_name_keys.add(key)
            rows.append(
                CompletedCourse(
                    user_id=user.id,
                    custom_name=item.name,
                    credits=item.credits,
                    category=item.category,
                    taken_term=taken_term,
                    taken_year=taken_year,
                    taken_semester=taken_semester,
                    grade=item.grade,
                )
            )

    if unknown_codes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="존재하지 않는 과목입니다: " + ", ".join(unknown_codes),
        )
    if duplicates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{DUPLICATE_MESSAGE}: " + ", ".join(duplicates),
        )

    db.add_all(rows)
    try:
        db.commit()
    except IntegrityError:
        # 위에서 검사한 직후에 같은 과목이 다른 요청으로 먼저 저장된 경우 (DB 유니크 인덱스가 막아줌)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_MESSAGE)

    # commit 뒤에는 id 등이 DB 값으로 다시 채워집니다. 응답에 과목 정보(row.course)가 필요하므로 새로 읽습니다.
    for row in rows:
        db.refresh(row)
    return rows


# =========================================================================
# API
# =========================================================================


@router.get("")
def list_completed(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """내 이수 내역 목록 (학년·학기 순)."""
    return [to_response(row) for row in load_completed_rows(db, user)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_completed(
    body: CompletedCreate,
    user: Annotated[User, Depends(get_current_student)],
    db: Annotated[Session, Depends(get_db)],
):
    """1과목 추가. 같은 과목이 이미 있으면 409."""
    rows = _create_rows(db, user, [body], body.taken_year, body.taken_semester)
    return to_response(rows[0])


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def create_completed_bulk(
    body: CompletedBulkRequest,
    user: Annotated[User, Depends(get_current_student)],
    db: Annotated[Session, Depends(get_db)],
):
    """같은 학기에 들은 과목 여러 개를 한 번에 추가. 하나라도 문제가 있으면 전부 저장하지 않습니다."""
    rows = _create_rows(db, user, body.items, body.taken_year, body.taken_semester)
    return [to_response(row) for row in rows]


@router.patch("/{completed_id}")
def update_completed(
    completed_id: int,
    body: CompletedUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """성적·들은 시기 수정. 요청에 넣은 필드만 바뀝니다 (schemas.CompletedUpdate 설명 참고)."""
    row = _get_my_row(db, user, completed_id)

    for field in body.model_fields_set:  # 요청에 실제로 들어 있던 필드만
        setattr(row, field, getattr(body, field))
    # 학년·학기가 바뀌었을 수 있으므로 통합 학기 번호도 다시 계산합니다.
    row.taken_term = to_taken_term(row.taken_year, row.taken_semester)

    db.commit()
    db.refresh(row)
    return to_response(row)


@router.delete("/{completed_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_completed(
    completed_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """삭제. 성공하면 본문 없이 204."""
    row = _get_my_row(db, user, completed_id)
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
