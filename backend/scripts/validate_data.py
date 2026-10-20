"""
원본 데이터 검증 스크립트.

실행 방법 (backend/ 폴더에서):
    python scripts/validate_data.py

하는 일:
  data/courses.csv, data/prerequisites.csv, data/requirements.json 을 읽어서
  솔버/진단에 넣기 전에 데이터에 모순이 없는지 7가지 항목을 검사합니다.

  [1] 과목코드 중복 없음
  [2] 선수과목 코드가 courses 에 실제로 존재
  [3] 선수과목 순환 없음 (A→B→A)
  [4] 선수과목이 후수과목보다 이른 학기에 개설 (term_index 비교)
  [5] required_courses 가 courses 에 있고 category 가 전공필수인가
  [6] 전공필수 학점 합 == 전공필수 최소학점(category_min.전공필수)
  [7] 전공별(공통+SW융합 / 공통+게임개발) 개설 전공 학점이 64학점 이상인가

문제가 있으면 항목마다 한국어로 출력하고,
마지막에 "검증 통과" 또는 "오류 N건" 을 출력합니다.
오류가 있으면 종료 코드 1 을 돌려주므로, 나중에 자동 검사(CI)에도 쓸 수 있습니다.
"""

import csv
import json
import os
import sys

# Windows 콘솔(cp949)에서도 한글이 깨지지 않도록 출력 인코딩을 UTF-8로 강제합니다.
sys.stdout.reconfigure(encoding="utf-8")

# data/ 폴더는 backend/ 폴더(이 스크립트의 상위 폴더) 아래에 있습니다.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BACKEND_DIR, "data")

PROGRAM = "전문학사"          # 솔버가 다루는 학위과정 (전공심화는 진단만 하므로 제외)
COMMON_MAJOR = "공통"         # 모든 세부전공이 들을 수 있는 과목의 major 값
MAJOR_CATEGORIES = ("전공필수", "전공선택")  # '전공' 학점으로 인정되는 이수구분

# 발견한 오류 메시지를 모아두는 리스트. 마지막에 개수를 셉니다.
errors = []


def error(msg):
    """오류를 기록하고 바로 화면에도 출력합니다."""
    errors.append(msg)
    print(f"  ✗ {msg}")


def ok(msg):
    print(f"  ✓ {msg}")


def read_csv(filename):
    """CSV 를 딕셔너리 리스트로 읽습니다.
    엑셀에서 저장한 CSV 는 맨 앞에 BOM(보이지 않는 문자)이 붙어 있어서
    encoding='utf-8-sig' 로 읽어야 첫 번째 컬럼 이름이 'code' 로 제대로 읽힙니다."""
    path = os.path.join(DATA_DIR, filename)
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def to_float(value):
    """'3.0' 같은 문자열을 숫자로 바꿉니다. 빈 칸(전공심화 미확인 학점 등)은 0 으로 봅니다."""
    value = (value or "").strip()
    return float(value) if value else 0.0


# ---------------------------------------------------------------------
# 데이터 읽기
# ---------------------------------------------------------------------
courses = read_csv("courses.csv")
prereqs = read_csv("prerequisites.csv")
with open(os.path.join(DATA_DIR, "requirements.json"), encoding="utf-8") as f:
    requirements = json.load(f)

program_req = requirements["programs"][PROGRAM]

# 과목코드 → 과목 행(딕셔너리). 코드로 과목 정보를 빠르게 찾기 위해 만듭니다.
# (코드가 중복되면 뒤의 행이 덮어쓰지만, 중복 자체는 [1]에서 오류로 잡습니다.)
course_by_code = {c["code"].strip(): c for c in courses}


# ---------------------------------------------------------------------
# [1] 과목코드 중복 없음
# ---------------------------------------------------------------------
print("[1] 과목코드 중복 검사")
seen = {}  # 코드 → 처음 등장한 줄 번호
before = len(errors)
for line_no, c in enumerate(courses, start=2):  # 1번 줄은 헤더이므로 2부터
    code = c["code"].strip()
    if code in seen:
        error(f"과목코드 {code} 가 중복됩니다 (courses.csv {seen[code]}번 줄, {line_no}번 줄)")
    else:
        seen[code] = line_no
if len(errors) == before:
    ok(f"과목 {len(courses)}개, 중복 없음")


# ---------------------------------------------------------------------
# [2] 선수과목 코드가 courses 에 실제로 존재
# ---------------------------------------------------------------------
print("[2] 선수과목 코드 존재 검사")
before = len(errors)
for line_no, p in enumerate(prereqs, start=2):
    course_code = p["course_code"].strip()
    prereq_code = p["prereq_code"].strip()
    if course_code not in course_by_code:
        error(f"prerequisites.csv {line_no}번 줄: 후수과목 {course_code} 가 courses.csv 에 없습니다")
    if prereq_code not in course_by_code:
        error(f"prerequisites.csv {line_no}번 줄: 선수과목 {prereq_code} 가 courses.csv 에 없습니다")
if len(errors) == before:
    ok(f"선수과목 관계 {len(prereqs)}개, 모든 코드가 존재함")


# ---------------------------------------------------------------------
# [3] 선수과목 순환 없음
# ---------------------------------------------------------------------
# 개념 설명:
#   선수과목 관계를 "선수과목 → 후수과목" 화살표로 그린 그래프로 생각합니다.
#   A→B→A 처럼 화살표를 따라가다 출발점으로 돌아오면 '순환'이고,
#   이 경우 어떤 과목도 먼저 들을 수 없어 솔버가 해를 찾지 못합니다.
#
#   깊이 우선 탐색(DFS)으로 화살표를 따라가면서 각 과목에 상태를 붙입니다.
#     - 미방문(없음) : 아직 안 가본 과목
#     - "visiting"  : 지금 따라가고 있는 경로 위에 있는 과목
#     - "done"      : 이 과목에서 출발하는 경로는 모두 확인 끝
#   따라가다가 "visiting" 과목을 다시 만나면 → 경로가 자기 자신으로 돌아왔으므로 순환!
print("[3] 선수과목 순환 검사")

# 그래프 만들기: 선수과목 코드 → [후수과목 코드, ...]
graph = {}
for p in prereqs:
    graph.setdefault(p["prereq_code"].strip(), []).append(p["course_code"].strip())

state = {}
found_cycles = []


def dfs(code, path):
    state[code] = "visiting"
    path.append(code)
    for nxt in graph.get(code, []):
        if state.get(nxt) == "visiting":
            # path 안에서 nxt 가 처음 나온 위치부터가 순환 구간입니다.
            cycle = path[path.index(nxt):] + [nxt]
            found_cycles.append(cycle)
        elif nxt not in state:
            dfs(nxt, path)
    path.pop()
    state[code] = "done"


for start in list(graph):
    if start not in state:
        dfs(start, [])

for cycle in found_cycles:
    error("선수과목 순환이 있습니다: " + " → ".join(cycle))
if not found_cycles:
    ok("순환 없음")


# ---------------------------------------------------------------------
# [4] 선수과목이 후수과목보다 이른 학기에 개설
# ---------------------------------------------------------------------
# term_index 는 1학년 1학기=1, 1학년 2학기=2, ... 처럼 '몇 번째 학기에 개설되는지'입니다.
# 선수과목의 term_index 가 후수과목보다 작아야(먼저 열려야) 순서대로 들을 수 있습니다.
print("[4] 선수과목 개설 학기 순서 검사")
before = len(errors)
for p in prereqs:
    course_code = p["course_code"].strip()
    prereq_code = p["prereq_code"].strip()
    # 코드가 없는 경우는 [2]에서 이미 오류로 잡았으므로 건너뜁니다.
    if course_code not in course_by_code or prereq_code not in course_by_code:
        continue
    course = course_by_code[course_code]
    prereq = course_by_code[prereq_code]
    course_term = int(course["term_index"])
    prereq_term = int(prereq["term_index"])
    if prereq_term >= course_term:
        error(
            f"{prereq['name']}({prereq_code}, {prereq_term}학기) 가 "
            f"{course['name']}({course_code}, {course_term}학기) 보다 먼저 개설되지 않습니다"
        )
if len(errors) == before:
    ok("모든 선수과목이 후수과목보다 이른 학기에 개설됨")


# ---------------------------------------------------------------------
# [5] required_courses 가 courses 에 있고 category 가 전공필수인가
# ---------------------------------------------------------------------
print("[5] 전공필수 과목 목록 검사")
before = len(errors)
required_codes = program_req["required_courses"]
for code in required_codes:
    if code not in course_by_code:
        error(f"required_courses 의 {code} 가 courses.csv 에 없습니다")
        continue
    course = course_by_code[code]
    if course["category"].strip() != "전공필수":
        error(
            f"required_courses 의 {course['name']}({code}) 이수구분이 "
            f"'{course['category']}' 입니다 (전공필수여야 함)"
        )
if len(errors) == before:
    ok(f"전공필수 {len(required_codes)}과목 모두 존재하고 이수구분이 전공필수")


# ---------------------------------------------------------------------
# [6] 전공필수 학점 합 == 전공필수 최소학점
# ---------------------------------------------------------------------
# courses.csv 에서 이수구분이 '전공필수'인 과목의 학점을 모두 더해 요건과 비교합니다.
# (required_courses 에 빠진 전공필수 과목이 있으면 여기서 합이 어긋나 드러납니다.)
print("[6] 전공필수 학점 합 검사")
required_min = program_req["category_min"]["전공필수"]
required_sum = sum(
    to_float(c["credits"])
    for c in courses
    if c["program"].strip() == PROGRAM and c["category"].strip() == "전공필수"
)
if required_sum != required_min:
    error(f"전공필수 학점 합이 {required_sum:g}학점입니다 (요건 {required_min}학점과 불일치)")
else:
    ok(f"전공필수 학점 합 {required_sum:g}학점 = 요건 {required_min}학점")


# ---------------------------------------------------------------------
# [7] 전공별 개설 전공 학점이 64학점 이상인가
# ---------------------------------------------------------------------
# 한 학생이 자기 전공(공통 + 본인 세부전공) 과목만 들어도 전공 64학점을 채울 수 있어야 합니다.
# 단, 학기제현장실습(18학점)은 선택하면 그 학기에 다른 과목을 못 듣는 '대체 경로'라서
# 합산하면 실제보다 부풀려집니다. 그래서 special_rules 의 학기제현장실습은 빼고 계산합니다.
print("[7] 전공별 개설 전공 학점 검사")
major_min = program_req["category_min"]["전공"]
excluded = {requirements["special_rules"]["학기제현장실습"]["code"]}

for major in requirements["majors"]:
    total = sum(
        to_float(c["credits"])
        for c in courses
        if c["program"].strip() == PROGRAM
        and c["category"].strip() in MAJOR_CATEGORIES
        and c["major"].strip() in (COMMON_MAJOR, major)
        and c["code"].strip() not in excluded
    )
    label = f"{COMMON_MAJOR}+{major}"
    if total < major_min:
        error(f"{label} 개설 전공 학점이 {total:g}학점으로 요건 {major_min}학점보다 부족합니다")
    else:
        ok(f"{label} 개설 전공 학점 {total:g}학점 (요건 {major_min}학점 이상, 학기제현장실습 제외)")


# ---------------------------------------------------------------------
# 결과 요약
# ---------------------------------------------------------------------
print()
if errors:
    print(f"오류 {len(errors)}건")
    sys.exit(1)
else:
    print("검증 통과")
