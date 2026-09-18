

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

# declarative_base() 로 만든 Base 클래스는 "이 클래스를 상속하면 DB 테이블이 된다"는
# 표시입니다. 아래에서 정의하는 모든 테이블 클래스는 반드시 Base 를 상속받습니다.
Base = declarative_base()


# =========================================================================
# 1. 학교 조직 구조
#    대학교 > 학과 > (학위과정 / 세부전공) > 교육과정(입학년도별 커리큘럼)
# =========================================================================


class University(Base):
    """대학교. 예: 경기과학기술대학교"""

    __tablename__ = "universities"
    __table_args__ = {"comment": "대학교 정보"}

    id = Column(Integer, primary_key=True, comment="대학교 고유 ID (자동 증가)")
    name = Column(String(100), nullable=False, comment="대학교 이름 (예: 경기과학기술대학교)")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="레코드가 생성된 시각 (DB가 자동으로 채워줌)",
    )

    # 이 대학교에 속한 학과 목록. university.departments 로 접근 가능.
    # cascade="all, delete-orphan": 대학교가 삭제되면 딸린 학과도 함께 정리한다는 뜻.
    departments = relationship(
        "Department",
        back_populates="university",
        cascade="all, delete-orphan",
    )
    # 이 대학교 소속으로 가입한 사용자 목록 (학생/관리자).
    users = relationship("User", back_populates="university")


class Department(Base):
    """학과. 예: 컴퓨터모바일융합과"""

    __tablename__ = "departments"
    __table_args__ = {"comment": "학과 정보"}

    id = Column(Integer, primary_key=True, comment="학과 고유 ID")
    university_id = Column(
        Integer,
        ForeignKey("universities.id", ondelete="CASCADE"),
        nullable=False,
        comment="이 학과가 속한 대학교 ID (universities.id 참조)",
    )
    name = Column(String(100), nullable=False, comment="학과 이름 (예: 컴퓨터모바일융합과)")

    university = relationship("University", back_populates="departments")
    # 이 학과가 운영하는 학위과정들 (전문학사 / 전공심화)
    programs = relationship(
        "Program", back_populates="department", cascade="all, delete-orphan"
    )
    # 이 학과의 세부전공들 (SW융합전공 / 게임개발전공)
    majors = relationship(
        "Major", back_populates="department", cascade="all, delete-orphan"
    )
    users = relationship("User", back_populates="department")


class Program(Base):
    """
    학위과정. 우리 학과는 2개의 학위과정이 있습니다.
      - 전문학사: 주간, 총 6학기
      - 전공심화: 야간, 총 2학기 (전문학사 취득 후 진학)
    """

    __tablename__ = "programs"
    __table_args__ = {"comment": "학위과정 정보 (전문학사/전공심화)"}

    id = Column(Integer, primary_key=True, comment="학위과정 고유 ID")
    department_id = Column(
        Integer,
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        comment="이 학위과정이 속한 학과 ID",
    )
    name = Column(String(50), nullable=False, comment="학위과정 이름 (예: 전문학사, 전공심화)")
    total_terms = Column(
        Integer, nullable=False, comment="총 학기 수 (전문학사=6, 전공심화=2)"
    )
    is_night = Column(
        Boolean, nullable=False, default=False, comment="야간 과정 여부 (전공심화=True)"
    )

    department = relationship("Department", back_populates="programs")
    # 이 학위과정에 속한 교육과정들 (입학년도별로 여러 개 존재)
    curricula = relationship(
        "Curriculum", back_populates="program", cascade="all, delete-orphan"
    )
    users = relationship("User", back_populates="program")


class Major(Base):
    """
    세부전공. 예: SW융합전공, 게임개발전공.
    주의: 실제로는 전공이 학생을 강하게 제한하지 않습니다.
    (잔여석이 있으면 타 전공 과목도 수강 가능 = hard 제약 아님)
    그래서 이 테이블은 "전공 선택" 정도의 참고용 정보로 사용됩니다.
    """

    __tablename__ = "majors"
    __table_args__ = {"comment": "세부전공 정보 (SW융합전공/게임개발전공)"}

    id = Column(Integer, primary_key=True, comment="세부전공 고유 ID")
    department_id = Column(
        Integer,
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        comment="이 세부전공이 속한 학과 ID",
    )
    name = Column(String(50), nullable=False, comment="세부전공 이름 (예: SW융합전공)")

    department = relationship("Department", back_populates="majors")
    users = relationship("User", back_populates="major")


class Curriculum(Base):
    """
    교육과정. "몇 학년도에 입학한 학생이 따라야 하는 커리큘럼"을 의미합니다.
    같은 학위과정이라도 입학년도가 다르면 교육과정이 달라질 수 있습니다.
    """

    __tablename__ = "curricula"
    __table_args__ = {"comment": "교육과정 정보 (입학년도별 커리큘럼)"}

    id = Column(Integer, primary_key=True, comment="교육과정 고유 ID")
    program_id = Column(
        Integer,
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        comment="이 교육과정이 속한 학위과정 ID",
    )
    admission_year = Column(Integer, nullable=False, comment="적용 입학년도 (예: 2024)")
    status = Column(
        String(20),
        nullable=False,
        default="active",
        comment="교육과정 상태 (예: active=현재 운영중, draft=준비중, archived=폐지)",
    )

    program = relationship("Program", back_populates="curricula")
    # 이 교육과정에 속한 과목들
    courses = relationship(
        "Course", back_populates="curriculum", cascade="all, delete-orphan"
    )
    # 이 교육과정의 졸업요건 (보통 1개만 존재 -> uselist=False 로 리스트가 아닌
    # 단일 객체로 다룰 수 있게 함)
    requirement = relationship(
        "Requirement",
        back_populates="curriculum",
        cascade="all, delete-orphan",
        uselist=False,
    )


# =========================================================================
# 2. 과목 관련 (과목 / 선수과목 / 분반)
# =========================================================================


class Course(Base):
    """
    과목(과목 카탈로그) 하나. 특정 교육과정 안에 속한 과목 정보입니다.
    is_placeholder=True 인 과목은 실제 과목이 아니라 "교양 자리를 채우기 위한
    가상 과목"을 의미합니다. (예: 시간표 상 교양 몇 학점을 들어야 하는 자리)
    """

    __tablename__ = "courses"
    __table_args__ = (
        # major, category, offered 는 정해진 값만 허용하도록 DB 레벨에서 제한합니다.
        CheckConstraint(
            "major IN ('공통', 'SW융합전공', '게임개발전공')", name="ck_courses_major"
        ),
        CheckConstraint(
            "category IN ('전공필수', '전공선택', '교양필수', '교양선택')",
            name="ck_courses_category",
        ),
        CheckConstraint("offered IN (1, 2, 3)", name="ck_courses_offered"),
        {"comment": "과목(교과목) 정보"},
    )

    id = Column(Integer, primary_key=True, comment="과목 고유 ID")
    curriculum_id = Column(
        Integer,
        ForeignKey("curricula.id", ondelete="CASCADE"),
        nullable=False,
        comment="이 과목이 속한 교육과정 ID",
    )
    code = Column(String(20), nullable=False, comment="과목 코드 (예: CM1101)")
    name = Column(String(100), nullable=False, comment="과목명 (예: 웹프로그래밍기초)")
    major = Column(
        String(20),
        nullable=False,
        comment="개설 전공 구분: '공통' | 'SW융합전공' | '게임개발전공' "
        "(단, 잔여석 있으면 타 전공도 수강 가능하므로 강한 제약은 아님)",
    )
    category = Column(
        String(20),
        nullable=False,
        comment="이수 구분: 전공필수 | 전공선택 | 교양필수 | 교양선택",
    )
    credits = Column(Integer, nullable=False, comment="학점")
    offered = Column(
        Integer,
        nullable=False,
        comment="개설 학기 구분: 1=1학기만 개설, 2=2학기만 개설, 3=양 학기 모두 개설",
    )
    term_index = Column(
        Integer,
        nullable=True,
        comment="전문학사 통합 학기 번호 (1~6). 교양 자리처럼 특정 학기가 없으면 NULL 가능",
    )
    year_hint = Column(
        Integer,
        nullable=True,
        comment="추천 수강 학년 힌트 (참고용, 필수 제약 아님)",
    )
    is_placeholder = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="가상 과목(교양 자리 채우기용) 여부. True면 실제 존재하는 과목이 아님",
    )
    feature = Column(
        String(50), nullable=True, comment="과목 특징 (예: 전공기초, 직업기초 등)"
    )
    note = Column(Text, nullable=True, comment="비고 (자유 텍스트)")

    curriculum = relationship("Curriculum", back_populates="courses")

    # 이 과목의 분반(시간표) 목록
    sections = relationship(
        "Section", back_populates="course", cascade="all, delete-orphan"
    )

    # 이 과목을 "들으려면 미리 들어야 하는" 선수과목 관계.
    # prerequisites 테이블에서 course_id == 이 과목.id 인 행들이 여기 해당됨.
    # foreign_keys 를 명시하는 이유: Prerequisite 테이블에는 courses 를 가리키는
    # FK가 2개(course_id, prereq_course_id)라서, 어떤 컬럼 기준 관계인지
    # SQLAlchemy 에게 알려줘야 하기 때문입니다.
    prerequisite_links = relationship(
        "Prerequisite",
        foreign_keys="Prerequisite.course_id",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    # 반대로, 이 과목이 "다른 과목의 선수과목으로 지정된" 관계.
    required_by_links = relationship(
        "Prerequisite",
        foreign_keys="Prerequisite.prereq_course_id",
        back_populates="prereq_course",
    )

    # 이 과목을 수강 완료로 기록한 학생들의 이력
    completed_by = relationship("CompletedCourse", back_populates="course")


class Prerequisite(Base):
    """
    선수과목 관계 테이블.
    한 행 = "course_id 과목을 들으려면, prereq_course_id 과목을 먼저 들어야 한다".
    """

    __tablename__ = "prerequisites"
    __table_args__ = (
        UniqueConstraint(
            "course_id", "prereq_course_id", name="uq_prerequisites_pair"
        ),
        {"comment": "과목 간 선수과목(선이수) 관계"},
    )

    id = Column(Integer, primary_key=True, comment="선수과목 관계 고유 ID")
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        comment="선수과목이 필요한 대상 과목 ID",
    )
    prereq_course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        comment="먼저 들어야 하는 선수과목 ID",
    )

    course = relationship(
        "Course", foreign_keys=[course_id], back_populates="prerequisite_links"
    )
    prereq_course = relationship(
        "Course", foreign_keys=[prereq_course_id], back_populates="required_by_links"
    )


class Section(Base):
    """
    분반(시간표) 정보. 같은 과목이라도 여러 분반(1분반, 2분반 ...)이 있을 수 있고,
    분반마다 요일/시간/강의실/교수가 다릅니다.
    """

    __tablename__ = "sections"
    __table_args__ = {"comment": "과목 분반(시간표) 정보"}

    id = Column(Integer, primary_key=True, comment="분반 고유 ID")
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        comment="이 분반이 속한 과목 ID",
    )
    section_no = Column(Integer, nullable=False, comment="분반 번호 (1분반, 2분반 ...)")
    day = Column(String(10), nullable=False, comment="요일 (예: 월, 화, 수 ...)")
    start_period = Column(Integer, nullable=False, comment="시작 교시")
    end_period = Column(Integer, nullable=False, comment="종료 교시")
    # 시간은 "HH:MM" 형태의 문자열로 저장합니다 (예: "09:00").
    # Time 타입 대신 문자열을 쓰는 이유는 원본 데이터(csv)가 문자열 형태이고,
    # 화면에 그대로 표시하기 편해서입니다.
    start_time = Column(String(5), nullable=False, comment="시작 시각 (예: '09:00')")
    end_time = Column(String(5), nullable=False, comment="종료 시각 (예: '10:50')")
    room = Column(String(50), nullable=True, comment="강의실")
    professor = Column(String(50), nullable=True, comment="담당 교수명")

    course = relationship("Course", back_populates="sections")


# =========================================================================
# 3. 졸업 요건
# =========================================================================


class Requirement(Base):
    """
    교육과정별 졸업요건. 교육과정(Curriculum) 1개당 보통 1개의 요건이 있습니다.
    """

    __tablename__ = "requirements"
    __table_args__ = {"comment": "교육과정별 졸업요건 (총 학점, 학기별 상한/하한 등)"}

    id = Column(Integer, primary_key=True, comment="졸업요건 고유 ID")
    curriculum_id = Column(
        Integer,
        ForeignKey("curricula.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 교육과정 1개당 요건 1개 (1:1 관계)
        comment="이 요건이 적용되는 교육과정 ID (1:1 관계)",
    )
    total_credits = Column(Integer, nullable=False, comment="졸업에 필요한 총 이수 학점")
    max_credits_per_term = Column(
        Integer, nullable=True, comment="한 학기에 신청 가능한 최대 학점 (제한 없으면 NULL)"
    )
    min_credits_per_term = Column(
        Integer, nullable=True, comment="한 학기에 신청해야 하는 최소 학점 (제한 없으면 NULL)"
    )

    curriculum = relationship("Curriculum", back_populates="requirement")
    # 이 요건 안의 세부 카테고리별 최소 이수 학점 목록
    # (예: 전공필수 30학점 이상, 교양선택 12학점 이상 ...)
    categories = relationship(
        "RequirementCategory",
        back_populates="requirement",
        cascade="all, delete-orphan",
    )


class RequirementCategory(Base):
    """졸업요건 중 '카테고리별 최소 이수 학점' 한 줄을 표현합니다."""

    __tablename__ = "requirement_categories"
    __table_args__ = (
        # '전공' = 전공필수 + 전공선택 합산 조건 (예: 전공 64학점 이상)
        CheckConstraint(
            "category IN ('전공필수', '전공선택', '전공', '교양필수', '교양선택')",
            name="ck_requirement_categories_category",
        ),
        {"comment": "졸업요건의 카테고리별 최소 이수 학점"},
    )

    id = Column(Integer, primary_key=True, comment="레코드 고유 ID")
    requirement_id = Column(
        Integer,
        ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=False,
        comment="이 카테고리 조건이 속한 졸업요건 ID",
    )
    category = Column(
        String(20),
        nullable=False,
        comment="이수 구분: 전공필수 | 전공선택 | 전공(전공필수+전공선택 합산) | 교양필수 | 교양선택",
    )
    min_credits = Column(Integer, nullable=False, comment="이 카테고리에서 최소로 채워야 하는 학점")

    requirement = relationship("Requirement", back_populates="categories")


# =========================================================================
# 4. 사용자 및 학습 이력
# =========================================================================


class User(Base):
    """서비스 사용자. 학생(student) 또는 관리자(admin)."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('student', 'admin')", name="ck_users_role"),
        {"comment": "서비스 사용자 (학생/관리자)"},
    )

    id = Column(Integer, primary_key=True, comment="사용자 고유 ID")
    email = Column(String(255), nullable=False, unique=True, comment="로그인용 이메일 (중복 불가)")
    password_hash = Column(
        String(255), nullable=False, comment="비밀번호 해시값 (평문 비밀번호는 저장하지 않음)"
    )
    name = Column(String(50), nullable=False, comment="사용자 이름")
    role = Column(
        String(10), nullable=False, default="student", comment="권한: 'student' | 'admin'"
    )

    # 학생의 소속 정보. 관리자 계정은 소속이 없을 수도 있으므로 전부 nullable.
    # ondelete="SET NULL": 소속(예: 학과)이 삭제돼도 사용자 계정 자체는 남기고,
    # 소속 정보만 비워둡니다 (사용자를 함부로 같이 지우지 않기 위함).
    university_id = Column(
        Integer,
        ForeignKey("universities.id", ondelete="SET NULL"),
        nullable=True,
        comment="소속 대학교 ID",
    )
    department_id = Column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        comment="소속 학과 ID",
    )
    program_id = Column(
        Integer,
        ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
        comment="소속 학위과정 ID (전문학사/전공심화)",
    )
    major_id = Column(
        Integer,
        ForeignKey("majors.id", ondelete="SET NULL"),
        nullable=True,
        comment="소속 세부전공 ID (참고용, 강한 제약 아님)",
    )
    admission_year = Column(Integer, nullable=True, comment="입학년도")
    is_active = Column(Boolean, nullable=False, default=True, comment="계정 활성화 여부")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="가입 시각",
    )
    last_login_at = Column(
        DateTime(timezone=True), nullable=True, comment="마지막 로그인 시각"
    )

    university = relationship("University", back_populates="users")
    department = relationship("Department", back_populates="users")
    program = relationship("Program", back_populates="users")
    major = relationship("Major", back_populates="users")

    # 이 학생이 이수 완료한 과목 이력들
    completed_courses = relationship(
        "CompletedCourse", back_populates="user", cascade="all, delete-orphan"
    )
    # 이 학생이 생성한 로드맵(추천 결과)들
    roadmaps = relationship(
        "Roadmap", back_populates="user", cascade="all, delete-orphan"
    )
    # 이 사용자가 남긴 피드백들
    feedbacks = relationship(
        "Feedback", back_populates="user", cascade="all, delete-orphan"
    )
    # 이 사용자가 관리자로서 남긴 작업 로그들 (역할이 admin인 경우에 해당)
    audit_logs = relationship("AuditLog", back_populates="admin")


class CompletedCourse(Base):
    """
    학생의 과목 이수 이력 한 줄.
    course_id 가 NULL 인 경우는 "우리 DB에 없는 교양 과목을 학생이 직접
    수기로 입력한 경우"를 의미합니다. 이때는 custom_name 에 과목명을 직접 적습니다.
    """

    __tablename__ = "completed_courses"
    __table_args__ = {"comment": "학생의 과목 이수 이력"}

    id = Column(Integer, primary_key=True, comment="이수 이력 고유 ID")
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="이수한 학생(사용자) ID",
    )
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        comment="이수한 과목 ID. DB에 없는 과목을 직접 입력한 경우 NULL",
    )
    custom_name = Column(
        String(100),
        nullable=True,
        comment="course_id가 NULL일 때 사용하는 직접 입력 과목명",
    )
    credits = Column(Integer, nullable=False, comment="이수 학점")
    category = Column(
        String(20),
        nullable=False,
        comment="이수 구분 (전공필수/전공선택/교양필수/교양선택)",
    )
    taken_term = Column(Integer, nullable=False, comment="이수한 학기 번호 (통합 학기 기준)")

    user = relationship("User", back_populates="completed_courses")
    course = relationship("Course", back_populates="completed_by")


# =========================================================================
# 5. 로드맵 / 피드백 / 감사로그
# =========================================================================


class Roadmap(Base):
    """
    학생이 생성한 '수강 로드맵(추천 결과)' 한 건.
    params_json: 로드맵을 만들 때 사용한 입력값(조건)들을 그대로 저장.
    result_json: 계산된 추천 결과를 그대로 저장.
    -> 두 값 모두 구조가 자주 바뀔 수 있어서, 고정된 컬럼 대신 JSON으로 유연하게 저장합니다.
    """

    __tablename__ = "roadmaps"
    __table_args__ = {"comment": "학생이 생성한 수강 로드맵(추천 결과) 기록"}

    id = Column(Integer, primary_key=True, comment="로드맵 고유 ID")
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="이 로드맵을 생성한 사용자 ID",
    )
    # JSONB는 PostgreSQL 전용 타입으로, JSON 데이터를 효율적으로 저장/검색할 수 있게 해줍니다.
    params_json = Column(
        JSONB, nullable=False, comment="로드맵 생성에 사용된 입력 조건 (JSON)"
    )
    result_json = Column(
        JSONB, nullable=False, comment="생성된 로드맵 결과 (JSON)"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="로드맵 생성 시각",
    )

    user = relationship("User", back_populates="roadmaps")


class Feedback(Base):
    """사용자가 남긴 피드백/의견."""

    __tablename__ = "feedbacks"
    __table_args__ = {"comment": "사용자 피드백"}

    id = Column(Integer, primary_key=True, comment="피드백 고유 ID")
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="피드백을 남긴 사용자 ID",
    )
    content = Column(Text, nullable=False, comment="피드백 내용")
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        comment="처리 상태 (예: pending=대기, resolved=처리완료)",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="피드백 작성 시각",
    )

    user = relationship("User", back_populates="feedbacks")


class AuditLog(Base):
    """
    관리자 작업 감사 로그. "누가, 언제, 무엇을, 어느 테이블/레코드에 대해 했는지" 기록.
    target_table/target_id 는 여러 테이블을 대상으로 하기 때문에(다형적),
    특정 테이블 하나로 고정된 외래키(FK)를 걸 수 없어 그냥 값만 저장합니다.
    """

    __tablename__ = "audit_logs"
    __table_args__ = {"comment": "관리자 작업 감사 로그"}

    id = Column(Integer, primary_key=True, comment="로그 고유 ID")
    admin_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="작업을 수행한 관리자(사용자) ID",
    )
    action = Column(String(50), nullable=False, comment="수행한 작업 종류 (예: create, update, delete)")
    target_table = Column(
        String(50), nullable=False, comment="작업 대상이 된 테이블 이름 (예: 'courses')"
    )
    target_id = Column(
        Integer,
        nullable=True,
        comment="작업 대상 레코드의 ID (target_table 안에서의 ID)",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="작업 수행 시각",
    )

    admin = relationship("User", back_populates="audit_logs")
