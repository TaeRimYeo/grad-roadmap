"""
로드맵 생성 로직 (진단 결과 → 솔버 → 시간표 정보 붙이기).

[흐름]
    1) 진단(diagnose) 결과로 "이미 졸업 가능한지" 먼저 확인
    2) 시작 학기(start_term) 확인
    3) 솔버(solve_roadmap)로 학기별 배치
    4) 배치된 실제 과목마다 분반(sections)을 붙이고, 학기마다 시간 겹침 경고(conflicts)를 만듦
    5) 진단 요약(남은 총학점·전공학점·전필)을 붙여 응답 모양 완성

[라우터와의 역할 나누기]
    routers/roadmap.py 는 DB 에서 값을 읽어 이 파일의 함수에 넘기기만 합니다.
    이 파일은 DB·FastAPI 를 import 하지 않는 순수 함수만 둡니다. (diagnose.py, solver.py 와 같은 원칙)
    그래서 잘못된 입력은 HTTPException 이 아니라 RoadmapError 로 알리고, 라우터가 400 으로 바꿉니다.

[입력 모양]
    diagnosis       : routers/diagnose.run_diagnose() 의 결과 (diagnose() + placeholders)
    prereqs         : [("CM1108", "CM1210"), ...]
    done_codes      : 이수 완료한 과목 code 목록 (F 제외)
    term_rule       : requirements.json 의 term_credit_rule
    sections_by_code: {"CM1101": [{"section_no", "day", "start_period", ...}, ...], ...}
"""

from datetime import date

from solver import MAX_EXTRA_TERMS, solve_roadmap
from timetable import find_conflicts

GRADUATED_MESSAGE = "이미 졸업 요건을 모두 채웠습니다"


class RoadmapError(ValueError):
    """로드맵을 만들 수 없는 입력 (라우터에서 400 으로 바꿉니다)"""


def max_term(term_rule: dict) -> int:
    """배치할 수 있는 마지막 학기 번호. 정규 6학기 + 추가 2학기 = 8"""
    return int(term_rule["regular_terms"]) + MAX_EXTRA_TERMS


def next_start_term(taken_terms: list[int]) -> int:
    """
    이수 내역의 가장 늦은 학기 다음 학기. 이수 내역이 없으면 1 (신입생).

    F 받은 과목도 넣어야 합니다. (그 학기에 학교를 다닌 것이므로 다음 학기부터 계획)
    """
    terms = [t for t in taken_terms if t]
    return max(terms) + 1 if terms else 1


def summarize(diagnosis: dict) -> dict:
    """진단 결과 중 로드맵 화면에 보여줄 요약만 골라냅니다."""
    return {
        "total_remaining": diagnosis["total"]["remaining"],
        "major_remaining": diagnosis["major"]["remaining"],
        "required_missing": diagnosis["required"]["missing"],
    }


def _attach_sections(terms: list[dict], sections_by_code: dict) -> list[dict]:
    """
    솔버 결과의 각 학기·과목에 분반 목록(sections)을 붙이고, 학기마다 conflicts 를 만듭니다.
    가상 과목은 시간표가 없으므로 sections 는 빈 목록입니다.
    """
    result = []
    for term in terms:
        courses = [
            dict(c, sections=[] if c["is_placeholder"] else list(sections_by_code.get(c["code"], [])))
            for c in term["courses"]
        ]
        result.append(dict(term, courses=courses, conflicts=find_conflicts(courses)))
    return result


def build_roadmap(
    diagnosis: dict,
    prereqs: list,
    done_codes,
    term_rule: dict,
    sections_by_code: dict,
    start_term: int,
) -> dict:
    """
    로드맵 하나를 만듭니다. (저장은 하지 않음)

    돌려주는 값:
        {"start_term": 5, "feasible": True, "message": None, "reasons": [],
         "total_terms": 2, "placeholder_count": 3,
         "summary": {"total_remaining", "major_remaining", "required_missing"},
         "terms": [{"term", "label", "credits", "courses": [... + "sections"], "conflicts": [...]}]}
    """
    base = {"start_term": start_term, "summary": summarize(diagnosis)}

    # ---- 1) 이미 졸업 가능 → 솔버를 부를 필요 없음 ----
    # (시작 학기 검사보다 먼저 합니다. 4학년까지 다 들은 학생은 시작 학기가 9 가 되기 때문)
    if diagnosis["graduatable"]:
        return {
            **base,
            "feasible": True,
            "message": GRADUATED_MESSAGE,
            "reasons": [],
            "total_terms": 0,
            "placeholder_count": 0,
            "terms": [],
        }

    # ---- 2) 시작 학기 범위 ----
    last = max_term(term_rule)
    if start_term > last:
        raise RoadmapError("더 이상 배치할 수 있는 학기가 없습니다")
    if start_term < 1:
        raise RoadmapError(f"시작 학기는 1~{last} 사이여야 합니다")

    # ---- 3) 솔버 ----
    solved = solve_roadmap(diagnosis["available"], prereqs, done_codes, diagnosis, start_term, term_rule)

    # ---- 4) 분반·겹침 경고 붙이기 ----
    return {
        **base,
        "feasible": solved["feasible"],
        "message": None,
        "reasons": solved["reasons"],
        "total_terms": solved["total_terms"],
        "placeholder_count": solved["placeholder_count"],
        "terms": _attach_sections(solved["terms"], sections_by_code),
    }


def default_title(today: date) -> str:
    """제목 없이 저장할 때 쓰는 이름. 예: '2026-10-27 로드맵'"""
    return f"{today.isoformat()} 로드맵"
