"""
FastAPI 서버 진입점(entry point).

실행 방법 (backend 폴더에서):
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

  - --reload : 코드를 고치면 서버가 자동으로 재시작 (개발용)
  - --host 0.0.0.0 : 내 컴퓨터뿐 아니라 같은 와이파이의 다른 기기(휴대폰)에서도 접속 허용
                     (127.0.0.1 로 켜면 휴대폰에서 접속이 안 됩니다)

확인용 주소:
    http://localhost:8000/api/health   → 서버가 살아있는지
    http://localhost:8000/api/db-check → DB 까지 연결되는지
    http://localhost:8000/docs         → FastAPI 가 자동 생성해주는 API 문서
"""

import re

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from db import get_db
from routers import admin, auth, completed, courses, diagnose, grades, meta

# =========================================================================
# 1. 앱 생성
# =========================================================================

app = FastAPI(
    title="학기 로드맵 API",
    description="학생 이수 내역과 졸업요건을 바탕으로 학기별 수강 로드맵을 생성하는 API",
    version="0.1.0",
)


# =========================================================================
# 2. CORS 설정
# =========================================================================
#
# CORS 란?
#   브라우저는 보안을 위해 "지금 보고 있는 페이지의 주소" 와 "요청을 보내는 주소" 가
#   다르면 그 요청을 기본적으로 막아버립니다.
#   우리 프로젝트는 프론트(Vite, 5173 포트)와 백엔드(FastAPI, 8000 포트)의 포트가
#   다르므로 브라우저 입장에서는 '다른 출신(origin)' 입니다.
#   그래서 서버 쪽에서 "이 주소는 믿어도 된다" 고 명시적으로 허용해줘야 합니다.

app.add_middleware(
    CORSMiddleware,
    # 내 컴퓨터에서 개발할 때 쓰는 프론트 주소
    allow_origins=["http://localhost:5173"],
    # 같은 와이파이의 휴대폰에서 접속할 때를 위한 허용 규칙.
    # 휴대폰은 http://192.168.0.12:5173 처럼 내 PC 의 사설 IP 로 접속하는데,
    # 그 IP 는 공유기에 따라 계속 바뀌므로 하나씩 적을 수 없습니다.
    # 그래서 정규식으로 "192.168.x.y:5173 형태면 전부 허용" 이라고 지정합니다.
    #   \.      = 마침표 한 개 (정규식에서 . 은 '아무 글자' 라서 \ 로 막아줌)
    #   \d+     = 숫자 한 개 이상
    allow_origin_regex=r"http://192\.168\.\d+\.\d+:5173",
    # 나중에 로그인을 붙였을 때 쿠키/인증 헤더를 주고받을 수 있게 허용
    allow_credentials=True,
    # 모든 HTTP 메서드(GET, POST, PUT, DELETE ...) 허용
    allow_methods=["*"],
    # 모든 요청 헤더 허용
    allow_headers=["*"],
)


# =========================================================================
# 3. 입력 검증 오류(422) 응답 모양 통일
# =========================================================================
#
# 문제:
#   Pydantic 검사에 실패하면 FastAPI 는 기본으로 이런 응답을 보냅니다.
#       {"detail": [{"type": "...", "loc": ["body", "password"], "msg": "...", ...}]}
#   detail 이 '목록' 이고, 이메일 형식 오류 같은 메시지는 영어입니다.
#   하지만 docs/api.md 명세는 "모든 오류는 {"detail": "한국어 메시지"}" 입니다.
#
# 해결:
#   RequestValidationError(= 입력 검증 실패)가 났을 때 실행될 함수를 직접 등록해서
#   detail 을 '한국어 문자열 하나' 로 바꿔 보냅니다.
#     - 우리가 schemas.py 에서 직접 쓴 한국어 메시지(예: 비밀번호 규칙)가 있으면 그걸 보여주고
#     - 그 외(Pydantic 기본 영어 메시지)는 명세대로 "입력 형식 오류" 로 보냅니다.
#
# 참고: 라우터에서 직접 raise HTTPException(422, "...") 한 것은 처음부터 문자열이라
#       이 처리기를 거치지 않고 그대로 나갑니다.

# [가-힣] = 한글 음절 한 글자. 메시지에 한글이 있으면 '우리가 쓴 메시지' 로 판단합니다.
_HANGUL = re.compile(r"[가-힣]")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # exc.errors() : 실패한 항목들의 목록. 여러 개일 수 있으므로 한글 메시지를 먼저 찾습니다.
    korean_messages = [e["msg"] for e in exc.errors() if _HANGUL.search(str(e.get("msg", "")))]
    detail = korean_messages[0] if korean_messages else "입력 형식 오류"

    # 개발 중 원인을 알 수 있도록 원본 오류는 서버 터미널에만 남깁니다.
    print(f"[422 입력 오류] {request.method} {request.url.path}: {exc.errors()}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": detail},
    )


# =========================================================================
# 4. 라우터 등록
# =========================================================================
#
# 각 라우터 파일(routers/*.py)에 prefix(/api/auth 등)가 이미 들어 있으므로
# 여기서는 붙이기만 하면 됩니다.
app.include_router(auth.router)  # /api/auth/...  회원가입·로그인·내 정보
app.include_router(meta.router)  # /api/meta/...  드롭다운 선택지 (인증 불필요)
app.include_router(admin.router)  # /api/admin/... 관리자 전용
app.include_router(diagnose.router)  # /api/diagnose 졸업 진단 (로그인 필요)
app.include_router(completed.router)  # /api/completed 이수 내역 저장 (로그인 필요)
app.include_router(courses.router)  # /api/courses 과목 고르기 목록 (학생만)
app.include_router(grades.router)  # /api/grades/summary 학점 요약 (로그인 필요)


# =========================================================================
# 5. 상태 확인용 엔드포인트
# =========================================================================


@app.get("/api/health")
def health_check():
    """
    서버가 살아있는지만 확인하는 엔드포인트. DB 는 건드리지 않습니다.

    DB 가 죽어도 이 주소는 성공해야 정상입니다.
    그래야 문제가 생겼을 때 '서버가 죽었나? DB 가 죽었나?' 를 구분할 수 있습니다.
    """
    return {"status": "ok"}


@app.get("/api/db-check")
def db_check(db: Session = Depends(get_db)):
    """
    DB 연결까지 정상인지 확인하는 엔드포인트.

    Depends(get_db) 가 하는 일:
        FastAPI 가 이 함수를 실행하기 전에 get_db() 를 먼저 돌려서
        세션을 만들고, 그 세션을 db 라는 이름으로 넣어줍니다.
        응답이 끝나면 get_db() 의 finally 가 실행되어 세션이 닫힙니다.

    SELECT 1 을 쓰는 이유:
        테이블이 아직 없어도 동작하는, 가장 가볍고 안전한 쿼리이기 때문입니다.
        "DB 가 내 쿼리에 답을 해준다" 는 사실만 확인하면 목적을 달성한 것입니다.

    text() 로 감싸는 이유:
        SQLAlchemy 2.0 부터는 생 SQL 문자열을 그대로 넘길 수 없고,
        text() 로 "이건 내가 의도한 SQL 이다" 라고 표시해줘야 합니다.
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        # 실패 원인을 서버 터미널에만 자세히 남깁니다.
        # (DB 주소나 비밀번호가 에러 메시지에 섞여 나올 수 있어서 응답에는 넣지 않습니다)
        print(f"[db-check 실패] {type(e).__name__}: {e}")

        # 503 Service Unavailable = "서버는 떴는데 필요한 외부 서비스(DB)를 못 쓰는 상태".
        # 500(서버 내부 오류)보다 상황을 정확히 설명해주는 상태 코드입니다.
        raise HTTPException(
            status_code=503,
            detail="데이터베이스에 연결할 수 없습니다. .env 의 DATABASE_URL 과 네트워크 상태를 확인해주세요.",
        )

    return {"db": "ok"}
