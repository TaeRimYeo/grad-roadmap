import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = os.getenv("DATABASE_URL")

if not url:
    print("❌ .env 에서 DATABASE_URL 을 못 찾았습니다")
    exit()

engine = create_engine(url)
with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print("✅ 연결 성공!")
    print(result.scalar())