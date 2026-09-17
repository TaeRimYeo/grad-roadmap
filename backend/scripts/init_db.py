import os
import sys

# Windows 콘솔(cp949)에서도 한글/이모지가 깨지지 않도록 출력 인코딩을 UTF-8로 강제합니다.
sys.stdout.reconfigure(encoding="utf-8")

# models.py 는 backend/ 폴더(이 스크립트의 상위 폴더)에 있으므로,
# import 가 가능하도록 상위 폴더를 경로에 추가합니다.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from sqlalchemy import create_engine

from models import Base

load_dotenv()
url = os.getenv("DATABASE_URL")

if not url:
    print("❌ .env 에서 DATABASE_URL 을 못 찾았습니다")
    sys.exit(1)

engine = create_engine(url)

# checkfirst=True(기본값): 이미 존재하는 테이블은 에러 없이 건너뛰고,
# 없는 테이블만 새로 생성합니다.
Base.metadata.create_all(engine, checkfirst=True)

print("✅ 테이블 생성 완료 (이미 있는 테이블은 건너뜀)")
for table in Base.metadata.sorted_tables:
    comment = table.comment or ""
    print(f"  - {table.name} ({comment})" if comment else f"  - {table.name}")
