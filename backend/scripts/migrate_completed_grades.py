"""
completed_courses 테이블에 학점관리용 컬럼을 추가하는 마이그레이션 스크립트.

실행 방법 (backend 폴더에서):
    python scripts/migrate_completed_grades.py

[마이그레이션이란? (초보자용)]
    이미 데이터가 들어 있는 DB 테이블의 '모양'을 바꾸는 작업입니다.
    init_db.py(create_all)는 "없는 테이블만 새로 만든다" 라서, 이미 있는 테이블에
    컬럼을 추가해주지 않습니다. 그래서 ALTER TABLE 을 직접 실행합니다.

[여러 번 실행해도 안전한 이유]
    - ADD COLUMN IF NOT EXISTS      : 컬럼이 이미 있으면 건너뜀
    - CREATE UNIQUE INDEX IF NOT EXISTS : 인덱스가 이미 있으면 건너뜀
    - 학년·학기 채우기는 taken_year 가 비어 있는 행에만 함
    기존 데이터는 지우지 않습니다.

[추가하는 것]
    taken_year      INTEGER     들은 학년 (1~4)
    taken_semester  VARCHAR(2)  들은 학기 ('1', '2', '여름', '겨울')
    grade           VARCHAR(2)  성적 (A+ ~ F, P). NULL = 성적 모름
    created_at      TIMESTAMPTZ 등록 시각

    uq_completed_user_course      : 같은 학생이 같은 학과 과목(course_id)을 두 번 등록 못 하게
    uq_completed_user_custom_name : 같은 학생이 같은 이름의 직접 입력 과목을 두 번 등록 못 하게
                                    (공백을 모두 지운 이름으로 비교. '글 쓰기' = '글쓰기')

[부분 유니크 인덱스 (초보자용)]
    'WHERE ...' 가 붙은 유니크 인덱스는 조건에 맞는 행끼리만 중복을 검사합니다.
    학과 과목 행(course_id 있음)과 직접 입력 행(course_id 없음)을 각각 따로 검사하기 위해 씁니다.
    중복 판정(409)은 API 에서 먼저 하고, 이 인덱스는 '동시에 두 번 요청' 같은 상황의 최종 안전장치입니다.
"""

import os
import sys

# Windows 콘솔(cp949)에서도 한글이 깨지지 않도록 출력 인코딩을 UTF-8로 강제합니다.
sys.stdout.reconfigure(encoding="utf-8")

# models.py, db.py 는 backend/ 폴더(이 스크립트의 상위 폴더)에 있습니다.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402

from db import engine  # noqa: E402

# 공백을 모두 지운 이름. 정규식 \s = 공백 문자 한 개, 'g' = 전부 바꾸기.
# (API 쪽 비교 규칙인 routers/completed.py 의 _name_key() 와 같은 규칙)
NAME_KEY_SQL = r"regexp_replace(custom_name, '\s', '', 'g')"

ADD_COLUMNS = [
    "ALTER TABLE completed_courses ADD COLUMN IF NOT EXISTS taken_year INTEGER",
    "ALTER TABLE completed_courses ADD COLUMN IF NOT EXISTS taken_semester VARCHAR(2)",
    "ALTER TABLE completed_courses ADD COLUMN IF NOT EXISTS grade VARCHAR(2)",
    "ALTER TABLE completed_courses ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()",
]

# 기존 행의 taken_term(통합 학기 번호)으로 학년·학기를 채웁니다.
#   1 → 1학년 1학기, 2 → 1학년 2학기, 3 → 2학년 1학기 ...
# 기존 데이터에는 계절학기 정보가 없으므로 정규학기로만 채웁니다.
BACKFILL = """
UPDATE completed_courses
   SET taken_year = (taken_term + 1) / 2,
       taken_semester = CASE WHEN taken_term % 2 = 1 THEN '1' ELSE '2' END
 WHERE taken_year IS NULL
"""

# 인덱스를 만들기 전에 중복이 있는지 검사합니다. 중복이 있으면 인덱스 생성이 실패하기 때문입니다.
DUP_COURSE = """
SELECT user_id, course_id, count(*) FROM completed_courses
 WHERE course_id IS NOT NULL
 GROUP BY user_id, course_id HAVING count(*) > 1
"""
DUP_NAME = f"""
SELECT user_id, {NAME_KEY_SQL} AS name_key, count(*) FROM completed_courses
 WHERE course_id IS NULL
 GROUP BY user_id, name_key HAVING count(*) > 1
"""

CREATE_INDEXES = [
    """CREATE UNIQUE INDEX IF NOT EXISTS uq_completed_user_course
         ON completed_courses (user_id, course_id) WHERE course_id IS NOT NULL""",
    f"""CREATE UNIQUE INDEX IF NOT EXISTS uq_completed_user_custom_name
         ON completed_courses (user_id, ({NAME_KEY_SQL})) WHERE course_id IS NULL""",
]


def main():
    # engine.begin(): 블록이 끝나면 commit, 중간에 에러가 나면 전부 rollback (전부 성공 또는 전부 취소)
    with engine.begin() as conn:
        for sql in ADD_COLUMNS:
            conn.execute(text(sql))
        filled = conn.execute(text(BACKFILL)).rowcount
        print(f"✅ 컬럼 추가 완료 (학년·학기를 채운 기존 행: {filled}개)")

        dup_course = conn.execute(text(DUP_COURSE)).all()
        dup_name = conn.execute(text(DUP_NAME)).all()
        print(f"🔎 중복 검사: 같은 학과 과목 {len(dup_course)}건, 같은 이름 직접 입력 과목 {len(dup_name)}건")
        if dup_course or dup_name:
            for row in dup_course:
                print(f"   - user_id={row[0]} course_id={row[1]} ({row[2]}개)")
            for row in dup_name:
                print(f"   - user_id={row[0]} 이름='{row[1]}' ({row[2]}개)")
            # 예외를 던지면 engine.begin() 이 위의 컬럼 추가까지 전부 되돌립니다.
            raise SystemExit("❌ 중복 행이 있어 인덱스를 만들 수 없습니다. 중복을 정리한 뒤 다시 실행하세요.")

        for sql in CREATE_INDEXES:
            conn.execute(text(sql))
        print("✅ 중복 방지 인덱스 생성 완료")

    # ---- 결과 확인 ----
    with engine.connect() as conn:
        print("\n[completed_courses 컬럼]")
        for name, dtype, nullable in conn.execute(
            text(
                "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
                "WHERE table_name = 'completed_courses' ORDER BY ordinal_position"
            )
        ):
            print(f"  - {name:15} {dtype:25} {'NULL 허용' if nullable == 'YES' else 'NOT NULL'}")
        print("\n[completed_courses 인덱스]")
        for (name,) in conn.execute(text("SELECT indexname FROM pg_indexes WHERE tablename = 'completed_courses'")):
            print(f"  - {name}")


if __name__ == "__main__":
    main()
