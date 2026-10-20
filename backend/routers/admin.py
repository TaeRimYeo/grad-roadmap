"""
관리자 전용 API 라우터.

    GET /api/admin/ping  관리자 권한 확인용 (프론트가 관리자 메뉴를 보여줄지 판단할 때 등)

앞으로 과목·졸업요건 관리 같은 관리자 기능이 생기면 이 파일에 추가합니다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from auth import require_admin
from models import User

router = APIRouter(prefix="/api/admin", tags=["관리자"])


@router.get("/ping")
def admin_ping(admin: Annotated[User, Depends(require_admin)]):
    """
    관리자라면 {"ok": true} 를 돌려줍니다.

    실제 검사는 전부 require_admin 의존성이 합니다. 이 함수 본문이 실행됐다는 것 자체가
    "관리자 확인 통과" 라는 뜻입니다.
        토큰 없음/잘못됨 → 401 로그인이 필요합니다 (get_current_user 단계)
        비활성 계정     → 403 비활성화된 계정입니다 (get_current_user 단계)
        학생 계정       → 403 관리자 권한이 필요합니다 (require_admin 단계)

    admin 매개변수는 본문에서 쓰지 않지만, 이렇게 적어야 FastAPI 가 require_admin 을 실행합니다.
    """
    return {"ok": True}
