"""
졸업 진단 API 라우터.

    POST /api/diagnose     (200)  요청 본문의 이수 내역 → 남은 학점·미이수 전필·들을 수 있는 과목·가상 과목
    GET  /api/diagnose/me  (200)  DB 에 저장된 내 이수 내역으로 같은 진단

[역할 나누기]
    계산은 전부 backend/diagnose.py(순수 함수)가 합니다. 이 파일은
        1) 로그인한 사용자의 학위과정·전공 확인
        2) DB 에서 과목·선수과목·졸업요건 읽기 (backend/curriculum.py 의 도우미 사용)
        3) 결과에 가상 과목(placeholder)을 붙여 응답 만들기
    만 합니다. 그래서 계산 규칙을 고칠 때는 이 파일이 아니라 diagnose.py 를 고칩니다.

[파일 이름 주의]
    backend/diagnose.py         : 계산 로직 (이 파일 안의 `from diagnose import diagnose`)
    backend/routers/diagnose.py : API 주소 (이 파일, routers.diagnose 라는 이름)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_student, get_current_user
from curriculum import find_curriculum, load_courses, load_prereqs, load_requirement
from db import get_db
from diagnose import diagnose
from grades import is_passed
from models import User
from placeholder import make_placeholders
from routers.completed import load_completed_rows
from schemas import DiagnoseRequest

router = APIRouter(prefix="/api", tags=["진단"])

# 이번 단계에서는 전공심화 진단을 지원하지 않습니다.
ADVANCED_PROGRAM = "전공심화"


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def run_diagnose(db: Session, user: User, completed: list[dict]) -> dict:
    """
    진단 한 번 실행하기. POST /api/diagnose 와 GET /api/diagnose/me 가 함께 씁니다.

    completed 는 diagnose() 가 받는 모양:
        [{"code": "CM1108"}, {"name": "글쓰기", "credits": 2, "category": "교양선택"}, ...]
    두 API 는 '이수 내역을 어디서 가져오느냐(요청 본문 / DB)' 만 다르고 나머지는 같습니다.
    """
    # ---- 1) 사용자 확인 ----
    if user.program is None or user.major is None:
        raise _bad_request("학위과정·세부전공 정보가 없는 계정입니다")
    if user.program.name == ADVANCED_PROGRAM:
        raise _bad_request("전공심화 과정 진단은 준비 중입니다")

    # ---- 2) DB 읽기 ----
    curriculum = find_curriculum(db, user)
    courses = load_courses(db, curriculum)
    prereqs = load_prereqs(db, curriculum)
    requirement = load_requirement(db, curriculum, courses)

    # ---- 3) 계산 (diagnose.py) ----
    result = diagnose(courses, prereqs, requirement, completed, user.major.name)

    # DB 에 없는 과목코드가 하나라도 있으면 계산 결과를 믿을 수 없으므로 422
    if result["unknown_codes"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="존재하지 않는 과목입니다: " + ", ".join(result["unknown_codes"]),
        )

    # ---- 4) 응답 조립: 가상 과목은 free_needed(아무 과목으로 채워도 되는 학점) 기준 ----
    result["placeholders"] = make_placeholders(result["free_needed"])
    return result


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
    return run_diagnose(db, user, body.to_plain())


def completed_for_diagnose(rows) -> list[dict]:
    """
    DB 의 이수 내역 행들을 POST /api/diagnose 요청 본문(completed)과 같은 모양으로 바꿉니다.
    GET /api/diagnose/me 와 로드맵 생성(routers/roadmap.py)이 함께 씁니다.

    F 받은 과목은 '이수하지 못한 과목' 이므로 넣지 않습니다 (= 다시 들어야 하는 과목으로 진단됨).
    """
    completed = []
    for row in rows:
        if not is_passed(row.grade):
            continue  # F → 진단 이수에서 제외
        if row.course is not None:
            completed.append({"code": row.course.code})
        elif row.custom_name:
            completed.append({"name": row.custom_name, "credits": row.credits, "category": row.category})
        # 과목표에서 과목이 삭제돼 course_id 가 비고 이름도 없는 행은 계산할 수 없으므로 건너뜀
    return completed


@router.get("/diagnose/me")
def get_my_diagnose(
    user: Annotated[User, Depends(get_current_student)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    저장된 이수 내역(GET /api/completed)으로 진단. 응답 모양은 POST /api/diagnose 와 같습니다.

    DB 의 이수 내역을 POST /api/diagnose 요청 본문과 같은 모양으로 바꿔서 run_diagnose() 에 넘깁니다.
    """
    return run_diagnose(db, user, completed_for_diagnose(load_completed_rows(db, user)))
