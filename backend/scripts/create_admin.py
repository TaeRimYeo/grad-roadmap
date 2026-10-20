"""
관리자(admin) 계정 생성 스크립트.

사용법 (backend/ 폴더에서 실행):
    python scripts/create_admin.py 이메일 비밀번호 이름

예:
    python scripts/create_admin.py admin@gtec.ac.kr MyPass1234 관리자

[중요] 이 스크립트가 관리자를 만드는 '유일한' 경로입니다.
    회원가입 API(POST /api/auth/signup)는 요청에 role 을 받지 않고 무조건
    'student' 로 저장하도록 막아두었습니다 (schemas.SignupRequest 참고).
    그래서 웹에서는 아무도 스스로 관리자가 될 수 없고, 서버(DB)에 직접 접근할 수 있는
    사람만 이 스크립트로 관리자를 만들 수 있습니다.

동작:
    - 처음 보는 이메일  → role='admin' 사용자를 새로 만든다
    - 이미 있는 이메일  → 새로 만들지 않고 role 만 'admin' 으로 바꾼다
                          (비밀번호·이름은 건드리지 않음)
"""

import os
import sys

# Windows 콘솔(cp949)에서도 한글이 깨지지 않도록 출력 인코딩을 UTF-8로 강제합니다.
sys.stdout.reconfigure(encoding="utf-8")

# db.py, auth.py, models.py 는 backend/ 폴더(이 스크립트의 상위 폴더)에 있으므로,
# import 가 가능하도록 상위 폴더를 경로에 추가합니다.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from auth import hash_password  # 회원가입 API 와 똑같은 방식(Argon2)으로 해싱해야 로그인이 됩니다
from db import SessionLocal
from models import User

USAGE = """사용법: python scripts/create_admin.py 이메일 비밀번호 이름

  이메일   : 로그인에 쓸 이메일 (예: admin@gtec.ac.kr)
  비밀번호 : 로그인 비밀번호
  이름     : 표시할 이름 (예: 관리자)

예: python scripts/create_admin.py admin@gtec.ac.kr MyPass1234 관리자"""


def main() -> None:
    # sys.argv[0] 은 스크립트 이름이므로, 실제 인자는 3개 → 총 길이 4 여야 합니다.
    if len(sys.argv) != 4:
        print("❌ 인자 개수가 맞지 않습니다.\n")
        print(USAGE)
        sys.exit(1)

    # 이메일은 회원가입·로그인과 똑같이 '앞뒤 공백 제거 + 소문자' 로 맞춥니다.
    # (schemas._normalize_email 과 같은 규칙. 안 맞추면 로그인 시 이메일을 못 찾습니다)
    email = sys.argv[1].strip().lower()
    password = sys.argv[2]
    name = sys.argv[3].strip()

    # 최소한의 형식 검사 (DB 컬럼 길이: email 255, name 50)
    if "@" not in email or len(email) > 255:
        print(f"❌ 이메일 형식이 올바르지 않습니다: {email}")
        sys.exit(1)
    if not password:
        print("❌ 비밀번호가 비어 있습니다.")
        sys.exit(1)
    if not name or len(name) > 50:
        print("❌ 이름은 1~50자로 입력해주세요.")
        sys.exit(1)

    # with 블록이 끝나면 세션이 자동으로 닫힙니다 (db.get_db 의 finally 와 같은 역할).
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))

        if user is not None:
            # ---- 이미 있는 이메일: role 만 admin 으로 변경 ----
            if user.role == "admin":
                print(f"ℹ️  {email} 은(는) 이미 관리자입니다. 변경할 내용이 없습니다.")
                return
            old_role = user.role
            user.role = "admin"
            db.commit()
            print(f"✅ 기존 사용자 {email} 의 권한을 '{old_role}' → 'admin' 으로 바꿨습니다.")
            print("   (비밀번호와 이름은 기존 값 그대로 유지됩니다. 입력한 비밀번호는 사용되지 않았습니다)")
            return

        # ---- 새 관리자 생성 ----
        # 관리자는 소속이 없어도 되므로 university_id, department_id, program_id,
        # major_id, admission_year, student_no 는 전부 넣지 않습니다 → DB 에 NULL 로 저장.
        admin = User(
            email=email,
            password_hash=hash_password(password),
            name=name,
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)  # DB 가 채워준 id 를 다시 읽어옵니다
        print(f"✅ 관리자 계정을 만들었습니다. (id={admin.id}, 이메일={email}, 이름={name})")


if __name__ == "__main__":
    main()
