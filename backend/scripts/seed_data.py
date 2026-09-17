"""
기초 데이터(시드) 등록 스크립트.

실행 방법 (backend/ 폴더에서):
    python scripts/seed_data.py

하는 일:
  [0] 기존 데이터 삭제 (여러 번 실행해도 중복이 쌓이지 않도록)
  [1] 대학교 / 학과 / 학위과정 / 세부전공 / 교육과정 기본 데이터 등록
  [2] data/courses.csv  -> courses 테이블
  [3] data/sections.csv -> sections 테이블

모든 작업은 하나의 트랜잭션으로 처리합니다.
중간에 에러가 나면 전체가 롤백되어, 데이터가 "반쯤 지워진" 상태로 남지 않습니다.
"""

import os
import sys

# Windows 콘솔(cp949)에서도 한글/이모지가 깨지지 않도록 출력 인코딩을 UTF-8로 강제합니다.
sys.stdout.reconfigure(encoding="utf-8")

# models.py 는 backend/ 폴더(이 스크립트의 상위 폴더)에 있으므로,
# import 가 가능하도록 상위 폴더를 경로에 추가합니다.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BACKEND_DIR)

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models import (
    University,
    Department,
    Program,
    Major,
    Curriculum,
    Course,
    Section,
)

# CSV 파일 경로 (실행 위치와 상관없이 backend/data/ 를 가리키도록 절대경로로 만듦)
COURSES_CSV = os.path.join(BACKEND_DIR, "data", "courses.csv")
SECTIONS_CSV = os.path.join(BACKEND_DIR, "data", "sections.csv")

# 교육과정 적용 입학년도
ADMISSION_YEAR = 2026

# 이수구분(category)이 비어 있는 과목에 임시로 넣을 값
DEFAULT_CATEGORY = "전공선택"
# 학점(credits)이 비어 있는 과목에 임시로 넣을 값.
# (courses.credits 는 NOT NULL 이라 비워둘 수 없음. 전공심화 7과목이 해당)
DEFAULT_CREDITS = 3


# =========================================================================
# 유틸 함수
# =========================================================================


def is_blank(value):
    """CSV 값이 비어있는지 확인. pandas 는 빈 칸을 NaN 으로 읽기 때문에 isna 로 검사합니다."""
    return pd.isna(value) or str(value).strip() == ""


def to_int_or_none(value):
    """
    숫자 값을 int 로 변환. 비어있으면 None.
    pandas 는 빈 칸이 섞인 숫자 컬럼을 float(3.0 등)로 읽기 때문에 int() 변환이 필요합니다.
    """
    if is_blank(value):
        return None
    return int(float(value))


def to_str_or_none(value):
    """문자열 값을 앞뒤 공백 제거해서 반환. 비어있으면 None."""
    if is_blank(value):
        return None
    return str(value).strip()


def to_bool(value):
    """'True'/'False' 문자열이나 bool 값을 파이썬 bool 로 변환."""
    if is_blank(value):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "y", "yes")


def append_note(note, extra):
    """기존 비고(note)에 문구를 ' · ' 로 이어붙입니다."""
    return f"{note} · {extra}" if note else extra


# =========================================================================
# [0] 기존 데이터 삭제
# =========================================================================


def clear_existing_data(session):
    """
    FK(외래키) 관계 때문에 "자식 테이블 -> 부모 테이블" 순서로 지워야 합니다.
    부모(예: courses)를 먼저 지우려 하면, 그걸 참조하는 자식(sections)이 남아있어
    FK 제약 위반 에러가 날 수 있습니다.

    참고: prerequisites / requirements 등 여기 없는 테이블은 DB 에 걸린
    ON DELETE CASCADE / SET NULL 설정에 따라 자동으로 정리됩니다.
    """
    delete_order = [Section, Course, Curriculum, Major, Program, Department, University]
    for model in delete_order:
        # query().delete() 는 행을 하나씩 불러오지 않고 DELETE 문 한 번으로 지웁니다.
        deleted = session.query(model).delete(synchronize_session=False)
        print(f"  - {model.__tablename__}: {deleted}행 삭제")


# =========================================================================
# [1] 기본 데이터 등록
# =========================================================================


def seed_base_data(session):
    """
    대학교 > 학과 > (학위과정, 세부전공) > 교육과정 을 등록하고,
    과목 등록 시 필요한 "학위과정 이름 -> 교육과정" 매핑을 반환합니다.
    """
    university = University(name="경기과학기술대학교")
    session.add(university)
    session.flush()  # flush: INSERT 를 DB 에 보내서 id 를 발급받음 (커밋은 아직 안 함)

    department = Department(university_id=university.id, name="컴퓨터모바일융합과")
    session.add(department)
    session.flush()

    # 학위과정: 전문학사(주간, 6학기) / 전공심화(야간, 2학기)
    associate = Program(
        department_id=department.id, name="전문학사", total_terms=6, is_night=False
    )
    advanced = Program(
        department_id=department.id, name="전공심화", total_terms=2, is_night=True
    )
    session.add_all([associate, advanced])

    # 세부전공
    session.add_all(
        [
            Major(department_id=department.id, name="SW융합전공"),
            Major(department_id=department.id, name="게임개발전공"),
        ]
    )
    session.flush()

    # 교육과정 (학위과정별 2026학년도)
    associate_curriculum = Curriculum(
        program_id=associate.id, admission_year=ADMISSION_YEAR, status="active"
    )
    advanced_curriculum = Curriculum(
        program_id=advanced.id, admission_year=ADMISSION_YEAR, status="active"
    )
    session.add_all([associate_curriculum, advanced_curriculum])
    session.flush()

    print("기본 데이터 등록 완료")

    # CSV 의 program 컬럼 값('전문학사'/'전공심화')으로 교육과정을 찾기 위한 딕셔너리
    return {
        "전문학사": associate_curriculum,
        "전공심화": advanced_curriculum,
    }


# =========================================================================
# [2] courses.csv -> courses
# =========================================================================


def seed_courses(session, curriculum_by_program):
    """
    courses.csv 를 읽어 courses 테이블에 넣고,
    분반 등록 시 필요한 "과목코드 -> Course" 매핑을 반환합니다.
    """
    # encoding='utf-8-sig': 엑셀에서 저장한 CSV 맨 앞의 BOM(보이지 않는 문자)을 제거해
    # 첫 컬럼 이름이 '﻿code' 처럼 깨지는 것을 방지합니다.
    df = pd.read_csv(COURSES_CSV, encoding="utf-8-sig")

    course_by_code = {}
    for _, row in df.iterrows():
        code = str(row["code"]).strip()
        program_name = str(row["program"]).strip()

        # program 값으로 어느 교육과정에 넣을지 결정
        curriculum = curriculum_by_program.get(program_name)
        if curriculum is None:
            print(f"  ⚠️ [{code}] 알 수 없는 program '{program_name}' -> 건너뜀")
            continue

        note = to_str_or_none(row["note"])

        # ★ 이수구분이 비어있으면 임시로 '전공선택' + 비고에 표시
        category = to_str_or_none(row["category"])
        if category is None:
            category = DEFAULT_CATEGORY
            note = append_note(note, "이수구분 미확인")

        # ★ credits 는 CSV 에서 3.0 같은 실수로 들어오므로 int 로 변환.
        #   비어있으면 NOT NULL 제약 때문에 임시값을 넣고 비고에 표시
        credits = to_int_or_none(row["credits"])
        if credits is None:
            credits = DEFAULT_CREDITS
            note = append_note(note, f"학점 미확인(임시 {DEFAULT_CREDITS}학점)")

        course = Course(
            curriculum_id=curriculum.id,
            code=code,
            name=str(row["name"]).strip(),
            major=str(row["major"]).strip(),
            category=category,
            credits=credits,
            offered=to_int_or_none(row["offered"]),
            # ★ term_index 가 비어있으면 None (교양 자리처럼 학기가 정해지지 않은 과목)
            term_index=to_int_or_none(row["term_index"]),
            is_placeholder=to_bool(row["is_placeholder"]),
            feature=to_str_or_none(row["feature"]),
            note=note,
        )
        session.add(course)

        # 같은 코드가 CSV 에 두 번 나오면 뒤의 것으로 덮어쓰게 되므로 경고
        if code in course_by_code:
            print(f"  ⚠️ 과목코드 '{code}' 가 CSV 에 중복되어 있습니다")
        course_by_code[code] = course

    # 분반에서 course.id 를 써야 하므로 여기서 flush 해서 id 를 발급받음
    session.flush()
    return course_by_code


# =========================================================================
# [3] sections.csv -> sections
# =========================================================================


def seed_sections(session, course_by_code):
    """sections.csv 를 읽어 sections 테이블에 넣고, 등록한 분반 수를 반환합니다."""
    df = pd.read_csv(SECTIONS_CSV, encoding="utf-8-sig")

    # 담당교수 컬럼 이름이 CSV 에 따라 'professor' 또는 'prof' 로 되어 있어 둘 다 지원
    professor_col = "professor" if "professor" in df.columns else "prof"

    # 요일/교시/시각은 sections 테이블에서 NOT NULL 이므로 반드시 있어야 함
    required_cols = ["day", "start_period", "end_period", "start_time", "end_time"]

    count = 0
    for _, row in df.iterrows():
        code = str(row["code"]).strip()

        # code 로 과목을 찾아 course_id 연결. 못 찾으면 경고 후 건너뜀
        course = course_by_code.get(code)
        if course is None:
            print(f"  ⚠️ [{code}] {row['name']}: courses 에 없는 과목코드 -> 분반 건너뜀")
            continue

        # 현장실습처럼 시간표가 없는 분반은 NOT NULL 컬럼을 채울 수 없으므로 건너뜀
        missing = [col for col in required_cols if is_blank(row[col])]
        if missing:
            print(
                f"  ⚠️ [{code}] {row['name']} {row['section_no']}분반: "
                f"시간표 정보 없음({', '.join(missing)}) -> 분반 건너뜀"
            )
            continue

        session.add(
            Section(
                course_id=course.id,
                section_no=to_int_or_none(row["section_no"]),
                day=str(row["day"]).strip(),
                # 교시도 CSV 에서 3.0 같은 실수로 들어오므로 int 변환
                start_period=to_int_or_none(row["start_period"]),
                end_period=to_int_or_none(row["end_period"]),
                start_time=str(row["start_time"]).strip(),
                end_time=str(row["end_time"]).strip(),
                room=to_str_or_none(row["room"]),
                professor=to_str_or_none(row[professor_col]),
            )
        )
        count += 1

    session.flush()
    return count


# =========================================================================
# 메인
# =========================================================================


def main():
    load_dotenv(os.path.join(BACKEND_DIR, ".env"))
    url = os.getenv("DATABASE_URL")
    if not url:
        print("❌ .env 에서 DATABASE_URL 을 못 찾았습니다")
        sys.exit(1)

    engine = create_engine(url)

    # session.begin(): with 블록이 정상 종료되면 commit, 예외가 나면 자동 rollback
    with Session(engine) as session, session.begin():
        print("기존 데이터 삭제 중...")
        clear_existing_data(session)

        curriculum_by_program = seed_base_data(session)
        course_by_code = seed_courses(session, curriculum_by_program)
        section_count = seed_sections(session, course_by_code)

        print(f"과목 {len(course_by_code)}개, 분반 {section_count}개 등록 완료")


if __name__ == "__main__":
    main()
