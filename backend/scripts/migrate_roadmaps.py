"""
roadmaps 테이블에 로드맵 저장용 컬럼을 추가하는 마이그레이션 스크립트.

실행 방법 (backend 폴더에서):
    python scripts/migrate_roadmaps.py

[여러 번 실행해도 안전한 이유]
    - ADD COLUMN IF NOT EXISTS   : 컬럼이 이미 있으면 건너뜀
    - CREATE INDEX IF NOT EXISTS : 인덱스가 이미 있으면 건너뜀
    기존 데이터는 지우지 않습니다. (마이그레이션 개념은 scripts/migrate_completed_grades.py 참고)

[추가하는 것]
    title        VARCHAR(100)  로드맵 제목
    start_term   INTEGER       시작 학기 번호
    total_terms  INTEGER       학기 수

    ix_roadmaps_user_created : "내 로드맵 목록을 최신순으로" 조회(GET /api/roadmaps)를 빠르게 하는 인덱스
"""

import os
import sys

# Windows 콘솔(cp949)에서도 한글이 깨지지 않도록 출력 인코딩을 UTF-8로 강제합니다.
sys.stdout.reconfigure(encoding="utf-8")

# models.py, db.py 는 backend/ 폴더(이 스크립트의 상위 폴더)에 있습니다.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402

from db import engine  # noqa: E402

ADD_COLUMNS = [
    "ALTER TABLE roadmaps ADD COLUMN IF NOT EXISTS title VARCHAR(100)",
    "ALTER TABLE roadmaps ADD COLUMN IF NOT EXISTS start_term INTEGER",
    "ALTER TABLE roadmaps ADD COLUMN IF NOT EXISTS total_terms INTEGER",
]

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_roadmaps_user_created ON roadmaps (user_id, created_at DESC)",
]


def main():
    # engine.begin(): 블록이 끝나면 commit, 중간에 에러가 나면 전부 rollback
    with engine.begin() as conn:
        for sql in ADD_COLUMNS:
            conn.execute(text(sql))
        print("✅ 컬럼 추가 완료")
        for sql in CREATE_INDEXES:
            conn.execute(text(sql))
        print("✅ 인덱스 생성 완료")

    # ---- 결과 확인 ----
    with engine.connect() as conn:
        print("\n[roadmaps 컬럼]")
        for name, dtype, nullable in conn.execute(
            text(
                "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
                "WHERE table_name = 'roadmaps' ORDER BY ordinal_position"
            )
        ):
            print(f"  - {name:12} {dtype:25} {'NULL 허용' if nullable == 'YES' else 'NOT NULL'}")
        print("\n[roadmaps 인덱스]")
        for (name,) in conn.execute(text("SELECT indexname FROM pg_indexes WHERE tablename = 'roadmaps'")):
            print(f"  - {name}")
        count = conn.execute(text("SELECT count(*) FROM roadmaps")).scalar()
        print(f"\n기존 로드맵 행: {count}개")


if __name__ == "__main__":
    main()
