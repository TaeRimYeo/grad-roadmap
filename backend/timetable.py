"""
시간표 겹침 검사.

[무엇을 하나?]
    로드맵의 한 학기에 배치된 과목들의 분반(요일·교시)을 보고
    "두 과목을 동시에 들을 수 없는 경우" 를 찾아 경고 문장을 만듭니다.
    지금은 경고만 하고, 솔버 제약으로 쓰지는 않습니다.

[두 분반이 겹친다는 것]
    같은 요일이고, 교시 구간이 한 칸이라도 겹치면 겹친 것입니다.
        화 3~4교시 와 화 4~5교시 → 4교시가 겹침
        화 3~4교시 와 화 5~6교시 → 안 겹침 (4교시가 끝나고 5교시 시작)
    구간 [s1, e1] 과 [s2, e2] 가 겹치는 조건:  s1 <= e2 그리고 s2 <= e1

[분반이 여러 개인 과목]
    컴퓨터그래픽처럼 1분반(화)·2분반(목)이 있으면, 학생이 겹치지 않는 분반을 고를 수 있습니다.
    그래서 두 과목의 '모든 분반 조합' 이 겹칠 때만 경고합니다.
    (한계: 두 과목씩만 비교합니다. A-B, B-C, A-C 는 각각 피할 수 있는데
     세 과목을 한꺼번에 피할 분반 조합은 없는 경우는 아직 잡지 못합니다.)

이 파일은 DB·FastAPI 를 import 하지 않는 순수 함수만 둡니다.

[입력 모양]
    section : {"day": "화", "start_period": 3, "end_period": 4, ...}
    course  : {"name": "자바프로그래밍응용", "sections": [section, ...], ...}
"""

from itertools import combinations


def _has_batchim(word: str) -> bool | None:
    """
    단어의 마지막 글자에 받침이 있는지. 판단할 수 없으면(영어 등) None.

    한글 글자는 (글자코드 - 0xAC00) % 28 이 0 이면 받침이 없습니다. (diagnose._eul_reul 과 같은 원리)
    숫자는 읽었을 때 받침이 있는 것: 영 일 삼 육 칠 팔
    """
    if not word:
        return None
    last = word[-1]
    if "가" <= last <= "힣":
        return (ord(last) - 0xAC00) % 28 != 0
    if last.isdigit():
        return last in "013678"
    return None


def _wa_gwa(word: str) -> str:
    """조사 '과' / '와' 를 고릅니다. (받침 있으면 '과', 없으면 '와')  예: 자바프로그래밍응용과, 컴퓨터그래픽과"""
    batchim = _has_batchim(word)
    if batchim is None:
        return "와(과)"
    return "과" if batchim else "와"


def overlap(a: dict, b: dict) -> tuple[int, int] | None:
    """
    분반 두 개가 겹치면 겹치는 교시 구간 (시작, 끝) 을, 안 겹치면 None 을 돌려줍니다.

        화 3~4 / 화 4~5 → (4, 4)
        화 3~4 / 수 3~4 → None (요일이 다름)
        화 3~4 / 화 5~6 → None (끝교시 4 다음에 5 시작)
    """
    if a["day"] != b["day"]:
        return None
    start = max(int(a["start_period"]), int(b["start_period"]))
    end = min(int(a["end_period"]), int(b["end_period"]))
    if start > end:
        return None
    return start, end


def _period_text(day: str, start: int, end: int) -> str:
    """'화 3~4교시' / '화 4교시' 같은 문구"""
    if start == end:
        return f"{day} {start}교시"
    return f"{day} {start}~{end}교시"


def course_conflict(a: dict, b: dict) -> str | None:
    """
    두 과목을 동시에 들을 수 없으면 경고 문장을, 들을 수 있으면 None 을 돌려줍니다.

    - 둘 중 하나라도 분반 정보가 없으면(가상 과목 등) 판단할 수 없으므로 None
    - 겹치지 않는 분반 조합이 하나라도 있으면 None (학생이 그 분반을 고르면 됨)
    - 모든 조합이 겹치면, 첫 번째 조합의 겹치는 교시를 문장에 씁니다
    """
    sections_a = a.get("sections") or []
    sections_b = b.get("sections") or []
    if not sections_a or not sections_b:
        return None

    first_overlap = None
    for sa in sections_a:
        for sb in sections_b:
            hit = overlap(sa, sb)
            if hit is None:
                return None  # 이 분반 조합이면 겹치지 않음 → 경고 필요 없음
            if first_overlap is None:
                first_overlap = (sa["day"], *hit)

    day, start, end = first_overlap
    return f"{a['name']}{_wa_gwa(a['name'])} {b['name']}의 수업 시간이 겹칩니다 ({_period_text(day, start, end)})"


def find_conflicts(courses: list[dict]) -> list[str]:
    """
    한 학기 과목 목록에서 시간이 겹치는 과목 쌍을 모두 찾아 경고 문장 목록으로 돌려줍니다.
    combinations(courses, 2) : 과목 두 개씩 짝지은 모든 경우 (A-B, A-C, B-C ...)
    """
    conflicts = []
    for a, b in combinations(courses, 2):
        message = course_conflict(a, b)
        if message:
            conflicts.append(message)
    return conflicts
