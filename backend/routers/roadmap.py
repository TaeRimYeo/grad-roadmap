"""
로드맵 API 라우터.

    POST   /api/roadmap/generate   (200)  저장된 이수 내역으로 로드맵 생성 (저장 안 함)
    POST   /api/roadmaps           (201)  생성 결과 저장
    GET    /api/roadmaps           (200)  내 저장 목록 (최신순)
    GET    /api/roadmaps/{id}      (200)  하나 상세 (plan 전체)
    DELETE /api/roadmaps/{id}      (204)  삭제

[역할 나누기]
    계산은 전부 순수 함수가 합니다.
        진단        : backend/diagnose.py   (routers/diagnose.run_diagnose 를 통해 /diagnose/me 와 같은 방식으로)
        학기 배치   : backend/solver.py
        시간 겹침   : backend/timetable.py
        위 셋 묶기  : backend/roadmap.py
    이 파일은 DB 에서 값을 읽어 넘기고, 결과를 저장·조회만 합니다.

[자기 데이터만 접근하기]
    routers/completed.py 와 같은 원칙입니다. 남의 로드맵 id 는 '없는 id' 와 똑같이 404 를 돌려줍니다.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth import get_current_student
from curriculum import find_curriculum, load_prereqs, load_sections, load_term_rule
from db import get_db
from models import Roadmap, User
from roadmap import RoadmapError, build_roadmap, default_title, next_start_term
from routers.completed import load_completed_rows
from routers.diagnose import completed_for_diagnose, run_diagnose
from schemas import RoadmapGenerateRequest, RoadmapSaveRequest

router = APIRouter(prefix="/api", tags=["로드맵"])

# 학생 한 명이 저장할 수 있는 로드맵 수
MAX_SAVED_ROADMAPS = 20

# 한국 시간 (UTC+9). 기본 제목의 날짜와 응답의 created_at 을 한국 날짜 기준으로 맞춥니다.
# zoneinfo("Asia/Seoul") 은 Windows 에 tzdata 패키지가 없으면 동작하지 않아서 고정 시차를 씁니다.
KST = timezone(timedelta(hours=9))


# =========================================================================
# 도우미 함수
# =========================================================================


def _get_my_roadmap(db: Session, user: User, roadmap_id: int) -> Roadmap:
    """내 로드맵 하나. 없거나 남의 것이면 404."""
    roadmap = db.scalar(select(Roadmap).where(Roadmap.id == roadmap_id, Roadmap.user_id == user.id))
    if roadmap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="로드맵을 찾을 수 없습니다")
    return roadmap


def _brief(roadmap: Roadmap) -> dict:
    """목록에 보여줄 한 건 (plan 제외)"""
    return {
        "id": roadmap.id,
        "title": roadmap.title,
        "start_term": roadmap.start_term,
        "total_terms": roadmap.total_terms,
        "created_at": roadmap.created_at.astimezone(KST).isoformat(),
    }


# =========================================================================
# API
# =========================================================================


@router.post("/roadmap/generate")
def generate_roadmap(
    user: Annotated[User, Depends(get_current_student)],
    db: Annotated[Session, Depends(get_db)],
    body: RoadmapGenerateRequest | None = None,
):
    """
    저장된 이수 내역(GET /api/completed)으로 로드맵을 만듭니다. 저장은 하지 않습니다.
    응답 모양은 docs/api.md 의 POST /api/roadmap/generate 참고.
    """
    # ---- 1) 이수 내역 → 진단 (GET /api/diagnose/me 와 같은 함수) ----
    rows = load_completed_rows(db, user)
    completed = completed_for_diagnose(rows)  # F 제외
    diagnosis = run_diagnose(db, user, completed)  # 전공심화·학과 없는 계정은 여기서 400

    # ---- 2) 솔버에 필요한 나머지 값 읽기 ----
    curriculum = find_curriculum(db, user)
    prereqs = load_prereqs(db, curriculum)
    sections_by_code = load_sections(db, curriculum)
    term_rule = load_term_rule(user.program.name)

    # 시작 학기: 요청에 있으면 그 값, 없으면 이수 내역(F 포함)의 가장 늦은 학기 + 1
    if body is not None and body.start_term is not None:
        start_term = body.start_term
    else:
        start_term = next_start_term([row.taken_term for row in rows])
    done_codes = [c["code"] for c in completed if "code" in c]

    # ---- 3) 계산 (roadmap.py) ----
    try:
        return build_roadmap(diagnosis, prereqs, done_codes, term_rule, sections_by_code, start_term)
    except RoadmapError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/roadmaps", status_code=status.HTTP_201_CREATED)
def save_roadmap(
    body: RoadmapSaveRequest,
    user: Annotated[User, Depends(get_current_student)],
    db: Annotated[Session, Depends(get_db)],
):
    """generate 결과를 저장합니다. 학생당 최대 MAX_SAVED_ROADMAPS 개."""
    # 같은 학생이 동시에 두 번 저장해서 20개를 넘기는 일을 막기 위해 내 users 행을 잠급니다.
    # (FOR UPDATE: 이 트랜잭션이 끝날 때까지 다른 요청은 같은 행을 잠그려면 기다려야 함)
    db.execute(select(User.id).where(User.id == user.id).with_for_update())
    count = db.scalar(select(func.count()).select_from(Roadmap).where(Roadmap.user_id == user.id))
    if count >= MAX_SAVED_ROADMAPS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"로드맵은 최대 {MAX_SAVED_ROADMAPS}개까지 저장할 수 있습니다",
        )

    roadmap = Roadmap(
        user_id=user.id,
        title=body.title or default_title(datetime.now(KST).date()),
        start_term=body.start_term,
        total_terms=body.plan["total_terms"],
        params_json={"start_term": body.start_term},
        result_json=body.plan,
    )
    db.add(roadmap)
    db.commit()
    db.refresh(roadmap)  # DB 가 채운 id·created_at 을 다시 읽어옴
    return _brief(roadmap)


@router.get("/roadmaps")
def list_roadmaps(
    user: Annotated[User, Depends(get_current_student)],
    db: Annotated[Session, Depends(get_db)],
):
    """내 저장 목록. 최신순 (같은 시각이면 id 큰 것 먼저)."""
    rows = db.scalars(
        select(Roadmap).where(Roadmap.user_id == user.id).order_by(Roadmap.created_at.desc(), Roadmap.id.desc())
    ).all()
    return [_brief(r) for r in rows]


@router.get("/roadmaps/{roadmap_id}")
def get_roadmap(
    roadmap_id: int,
    user: Annotated[User, Depends(get_current_student)],
    db: Annotated[Session, Depends(get_db)],
):
    """하나 상세. 목록 항목 + plan(저장한 generate 응답 전체)."""
    roadmap = _get_my_roadmap(db, user, roadmap_id)
    return {**_brief(roadmap), "plan": roadmap.result_json}


@router.delete("/roadmaps/{roadmap_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_roadmap(
    roadmap_id: int,
    user: Annotated[User, Depends(get_current_student)],
    db: Annotated[Session, Depends(get_db)],
):
    roadmap = _get_my_roadmap(db, user, roadmap_id)
    db.delete(roadmap)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
