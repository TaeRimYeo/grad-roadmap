"""
가상 과목(placeholder) 생성기.

[placeholder 란? (초보자용)]
    교양은 학교 공통 과목이 너무 많아서 "어떤 과목을 들을지" 미리 정할 수 없습니다.
    그래서 과목명 대신 "3학점짜리 빈 자리", "2학점짜리 빈 자리" 를 여러 개 만들어 두고,
    나중에 솔버(CP-SAT)가 그중 몇 개를 골라 학기에 배치하게 합니다.

[왜 필요한 것보다 많이 만드나?]
    예를 들어 7학점이 필요하면 3+2+2 도 되고 3+3+... 처럼 조합이 여러 가지입니다.
    후보를 딱 맞게 만들면 솔버가 고를 여지가 없으므로 "여유 있게" 만들고,
    솔버가 학기별 학점 제약(15~22학점)에 맞춰 알맞은 조합을 고르게 합니다.

    후보 개수 = ceil(필요학점 / 2) + 2
    → 전부 2학점만 골라도 필요학점을 채울 수 있는 개수 + 여유 2개

이 파일은 DB·FastAPI 를 import 하지 않는 순수 함수만 둡니다.
"""

import math

# 가상 과목 학점 단위. 3학점과 2학점을 번갈아 만듭니다.
CREDIT_UNITS = (3, 2)

# 양학기 개설 (1=1학기, 2=2학기, 3=양학기). courses.csv 의 offered 와 같은 규칙.
OFFERED_BOTH = 3


def _letters(index: int) -> str:
    """
    0, 1, 2, ... 를 A, B, ..., Z, AA, AB, ... 로 바꿉니다. (엑셀 열 이름과 같은 방식)

    후보가 최대 57개(110학점 기준)까지 생기므로 알파벳 26자로는 모자랍니다.

        0 → A,  25 → Z,  26 → AA,  27 → AB
    """
    result = ""
    n = index + 1  # 1부터 세는 방식으로 바꿔야 계산이 깔끔합니다.
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def make_placeholders(need_credits: int, category: str = "교양선택") -> list[dict]:
    """
    필요 학점(need_credits)을 채울 가상 과목 후보 목록을 만듭니다.

    - 후보 개수 = ceil(need / 2) + 2
    - 3학점, 2학점을 번갈아 만듭니다 (A=3, B=2, C=3, ...).
      개수가 홀수면 3학점이 하나 더 많습니다.
    - need 가 0 이하면 채울 학점이 없으므로 빈 목록을 돌려줍니다.

    예) need=28 → 16개 (3학점 8개 + 2학점 8개, 합 40학점)
    """
    if need_credits <= 0:
        return []

    count = math.ceil(need_credits / 2) + 2

    placeholders = []
    for i in range(count):
        letter = _letters(i)
        placeholders.append(
            {
                "code": f"GE_{letter}",
                "name": f"교양 {letter}",
                "category": category,
                "credits": CREDIT_UNITS[i % 2],  # 짝수 번째는 3학점, 홀수 번째는 2학점
                "offered": OFFERED_BOTH,
                "prereqs": [],  # 가상 과목은 선수과목이 없음
                "is_placeholder": True,
            }
        )
    return placeholders
