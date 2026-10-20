"""
졸업 진단(diagnose) 로직.

[진단이란? (초보자용)]
    "졸업하려면 앞으로 무엇을 더 들어야 하나?" 를 계산하는 기능입니다.
    학기별 배치(로드맵)는 솔버(CP-SAT)가 하지만, 진단은 단순한 더하기·빼기라서
    솔버를 쓰지 않습니다.

[남은 학점을 세 덩어리로 나누는 이유]
    남은 총학점을 아래처럼 "반드시 채워야 하는 순서" 대로 나눕니다.

        남은 총학점 = 남은 전공필수 학점          ← 정해진 과목(정보처리특론 등)
                    + major_elective_needed       ← 반드시 전공선택으로 채울 학점
                    + free_needed                 ← 전공선택·교양 아무거나

    예) 신입생: 총 110 = 전필 9 + 전선 55 + 자유 46
        - 전공은 64학점 필요한데 전필 9학점이 전공에 포함되므로 전선은 64 - 9 = 55
        - 나머지 110 - 9 - 55 = 46 은 아무 과목으로 채워도 됨
        → 교양 가상 과목(placeholder)은 free_needed(46) 기준으로만 만듭니다.

이 파일은 DB·FastAPI 를 import 하지 않는 순수 함수만 둡니다.
(DB 에서 읽어오는 일, HTTP 요청·응답 처리는 API 쪽에서 합니다.)

[입력 모양]
    courses  : [{"code", "name", "major", "category", "credits", "offered", "term_index", ("program")}, ...]
    prereqs  : [("CM1108", "CM1210"), ...]          # (선수 code, 후수 code)
    requirement : {"total_credits": 110, "major_min": 64, "required_courses": ["CM3107", ...]}
    completed : [{"code": "CM1108"}, {"name": "글쓰기", "credits": 2, "category": "교양선택"}, ...]
    major    : "SW융합전공" 또는 "게임개발전공"
"""

# 전공학점에 들어가는 이수구분 (전공필수 + 전공선택)
MAJOR_CATEGORIES = {"전공필수", "전공선택"}

# 모든 전공이 들을 수 있는 과목의 major 값
COMMON_MAJOR = "공통"

# available(추천 후보)에서 빼는 과목.
# 현장실습은 학생이 직접 고르는 선택 과목이라 자동 추천 대상이 아닙니다.
EXCLUDED_NAMES = {"학기제현장실습", "현장실습"}

# 전공심화(야간 4학년) 과목은 전문학사 진단 대상이 아님
ADVANCED_PROGRAM = "전공심화"

# 개설 학기 번호 → 화면에 보여줄 이름
OFFERED_LABELS = {1: "1학기", 2: "2학기", 3: "양학기"}


# =========================================================================
# 작은 도우미 함수
# =========================================================================


def _num(value) -> int | float:
    """
    학점을 보기 좋게 바꿉니다. CSV 의 3.0 → 3, 2.5 → 2.5 그대로.
    값이 비어 있으면(전공심화 과목은 학점 미확인) 0 으로 봅니다.
    """
    if value is None or value == "":
        return 0
    value = float(value)
    return int(value) if value.is_integer() else value


def _eul_reul(word: str) -> str:
    """
    단어 뒤에 붙을 조사 '을' / '를' 을 고릅니다. (받침 있으면 '을', 없으면 '를')

        파이썬프로그래밍기초 → 를,  C#프로그래밍 → 을,  캡스톤디자인1(일) → 을

    [한글 받침 계산]
        한글 글자는 유니코드에서 '가'(0xAC00)부터 규칙적으로 배치되어 있어서
        (글자코드 - 0xAC00) % 28 이 0 이면 받침이 없는 글자입니다.
    """
    if not word:
        return "을(를)"
    last = word[-1]
    if "가" <= last <= "힣":
        return "을" if (ord(last) - 0xAC00) % 28 else "를"
    if last.isdigit():
        # 숫자를 읽었을 때 받침이 있는 것: 영 일 삼 육 칠 팔
        return "을" if last in "013678" else "를"
    return "을(를)"  # 영어 등은 판단이 어려우므로 둘 다 표시


def _is_advanced(course: dict) -> bool:
    """전공심화 과목인지 확인. program 값이 없으면 term_index 7 이상(4학년)으로 판단합니다."""
    if course.get("program"):
        return course["program"] == ADVANCED_PROGRAM
    return int(course.get("term_index") or 0) >= 7


# =========================================================================
# 1단계: 이수 내역 정리
# =========================================================================


def _normalize_completed(completed: list[dict], course_by_code: dict) -> tuple[list[dict], set, list]:
    """
    두 종류가 섞인 이수 내역을 같은 모양({code, name, credits, category})으로 정리합니다.

        {"code": "CM1108"}                                    → courses 에서 학점·이수구분을 찾아 채움
        {"name": "글쓰기", "credits": 2, "category": "교양선택"} → 직접 입력한 과목, 그대로 사용

    같은 과목이 두 번 들어오면 한 번만 셉니다.
        - DB 과목은 code 가 같으면 중복
        - 직접 입력 과목은 name 이 같으면 중복

    돌려주는 값:
        items         : 정리된 이수 과목 목록 (중복 제거됨)
        done_codes    : 이수한 DB 과목 code 집합 (available·선수과목 확인용)
        unknown_codes : DB 에 없는 code 목록 (계산에서 제외. API 에서 422 로 알려줄 예정)
    """
    items = []
    done_codes = set()
    done_names = set()  # 직접 입력 과목 중복 확인용
    unknown_codes = []

    for entry in completed:
        code = entry.get("code")

        if code:
            # ---- DB 에 있는 과목 ----
            if code in done_codes:
                continue  # 중복 → 건너뜀
            course = course_by_code.get(code)
            if course is None:
                if code not in unknown_codes:
                    unknown_codes.append(code)
                continue
            done_codes.add(code)
            items.append(
                {
                    "code": code,
                    "name": course["name"],
                    "credits": _num(course.get("credits")),
                    "category": course.get("category"),
                }
            )
        else:
            # ---- 직접 입력한 과목 (주로 교양) ----
            name = (entry.get("name") or "").strip()
            if not name or name in done_names:
                continue  # 이름이 없거나 중복 → 건너뜀
            done_names.add(name)
            items.append(
                {
                    "code": None,
                    "name": name,
                    "credits": _num(entry.get("credits")),
                    "category": entry.get("category"),
                }
            )

    return items, done_codes, unknown_codes


# =========================================================================
# 메인 함수
# =========================================================================


def diagnose(courses: list[dict], prereqs: list, requirement: dict, completed: list[dict], major: str) -> dict:
    """
    이수 내역과 졸업요건을 비교해서 남은 학점, 미이수 전필, 들을 수 있는 과목 등을 계산합니다.
    출력 모양은 파일 맨 아래 return 문을 참고하세요.
    """
    course_by_code = {c["code"]: c for c in courses}

    # ---- 1단계: 이수 내역 정리 ----
    items, done_codes, unknown_codes = _normalize_completed(completed, course_by_code)

    # ---- 2단계: 총학점 / 전공학점 ----
    total_done = sum(item["credits"] for item in items)
    # 다른 전공 과목을 들었어도 전공학점으로 인정합니다. (전공 구분은 soft 규칙)
    major_done = sum(item["credits"] for item in items if item["category"] in MAJOR_CATEGORIES)

    total_required = requirement["total_credits"]
    major_required = requirement["major_min"]
    total_remaining = max(0, total_required - total_done)
    major_remaining = max(0, major_required - major_done)

    # ---- 3단계: 전공필수 ----
    required_codes = requirement["required_courses"]
    required_credits = sum(_num(course_by_code[c].get("credits")) for c in required_codes if c in course_by_code)
    required_done = sum(
        _num(course_by_code[c].get("credits")) for c in required_codes if c in course_by_code and c in done_codes
    )
    missing_required = [
        {"code": c, "name": course_by_code[c]["name"], "credits": _num(course_by_code[c].get("credits"))}
        for c in required_codes
        if c in course_by_code and c not in done_codes
    ]
    required_remaining = sum(m["credits"] for m in missing_required)

    # ---- 4단계: 남은 학점 나누기 (파일 맨 위 설명 참고) ----
    # 전공은 전필을 포함하므로, 남은 전공학점에서 남은 전필을 빼면 '반드시 전선으로 채울 학점'
    major_elective_needed = max(0, major_remaining - required_remaining)
    # 남은 총학점에서 전필과 필수 전선을 빼고 남는 학점 → 전선·교양 아무거나
    free_needed = max(0, total_remaining - required_remaining - major_elective_needed)

    # ---- 5단계: 들을 수 있는 과목 (available) ----
    available = []
    for c in courses:
        if c["code"] in done_codes:
            continue  # 이미 들은 과목
        if c.get("major") not in (COMMON_MAJOR, major):
            continue  # 다른 전공 과목 (기본 추천에서만 제외, 수강 자체는 가능)
        if _is_advanced(c):
            continue  # 전공심화 과목
        if c["name"] in EXCLUDED_NAMES:
            continue  # 현장실습 (학생이 직접 선택)
        offered = int(c.get("offered") or 0)
        available.append(
            {
                "code": c["code"],
                "name": c["name"],
                "major": c.get("major"),
                "category": c.get("category"),
                "credits": _num(c.get("credits")),
                "offered": offered,
                "offered_label": OFFERED_LABELS.get(offered, "미정"),
                "term_index": int(c.get("term_index") or 0),
            }
        )

    # ---- 6단계: 선수과목 경고 ----
    # 후수 code → [선수 code, ...]  (한 과목에 선수과목이 여러 개일 수도 있으므로 목록으로)
    prereqs_of: dict[str, list[str]] = {}
    for before, after in prereqs:
        prereqs_of.setdefault(after, []).append(before)

    prereq_warnings = []
    for c in available:
        for before in prereqs_of.get(c["code"], []):
            if before in done_codes:
                continue  # 선수과목을 이미 들음
            before_name = course_by_code[before]["name"] if before in course_by_code else before
            prereq_warnings.append(
                {
                    "code": c["code"],
                    "name": c["name"],
                    "prereq_code": before,
                    "prereq_name": before_name,
                    "message": f"{c['name']} — {before_name}{_eul_reul(before_name)} 먼저 이수해야 합니다",
                }
            )

    # ---- 7단계: 졸업 가능 여부 ----
    graduatable = total_remaining == 0 and major_remaining == 0 and not missing_required

    return {
        "total": {"completed": total_done, "required": total_required, "remaining": total_remaining},
        "major": {"completed": major_done, "required": major_required, "remaining": major_remaining},
        "required": {
            "completed": required_done,
            "required": required_credits,
            "remaining": required_remaining,
            "missing": missing_required,
        },
        "major_elective_needed": major_elective_needed,
        "free_needed": free_needed,
        "available": available,
        "prereq_warnings": prereq_warnings,
        "unknown_codes": unknown_codes,
        "graduatable": graduatable,
    }
