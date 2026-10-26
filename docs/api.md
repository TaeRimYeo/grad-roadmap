# API 명세

모든 오류 응답은 `{"detail": "한국어 메시지"}` 형식.

## POST /api/auth/signup — 회원가입

```json
// 요청
{
  "email": "kim@gtec.ac.kr",
  "password": "abcd1234",
  "name": "김경기",
  "student_no": "2025123456",
  "department_id": 1,
  "program_id": 1,
  "major_id": 1,
  "admission_year": 2025
}

// 201 응답
{ "id": 7, "email": "kim@gtec.ac.kr", "name": "김경기", "role": "student" }
```

| 오류 | 메시지 |
|---|---|
| 409 | 이미 가입된 이메일입니다 |
| 422 | 입력 형식 오류 |

비밀번호 규칙: 8자 이상, 영문과 숫자 모두 포함
role은 서버에서 무조건 `student`로 고정 (요청값 무시)

## POST /api/auth/login — 로그인

```json
// 요청
{ "email": "kim@gtec.ac.kr", "password": "abcd1234" }

// 200 응답
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": { "id": 7, "name": "김경기", "role": "student" }
}
```

| 오류 | 메시지 |
|---|---|
| 401 | 이메일 또는 비밀번호가 올바르지 않습니다 |

어느 쪽이 틀렸는지 구분하지 않음 (보안)
성공 시 `users.last_login_at` 갱신

## GET /api/auth/me — 내 정보

헤더: `Authorization: Bearer <토큰>`

```json
// 200 응답
{
  "id": 7, "email": "kim@gtec.ac.kr", "name": "김경기", "role": "student",
  "student_no": "2025123456", "admission_year": 2025,
  "department": "컴퓨터모바일융합과", "program": "전문학사", "major": "SW융합전공"
}
```

| 오류 | 메시지 |
|---|---|
| 401 | 로그인이 필요합니다 |
| 403 | 비활성화된 계정입니다 |

## GET /api/meta/signup-options — 회원가입 드롭다운

인증 없이 호출 가능.

```json
{
  "universities": [{ "id": 1, "name": "경기과학기술대학교" }],
  "departments":  [{ "id": 1, "university_id": 1, "name": "컴퓨터모바일융합과" }],
  "programs":     [{ "id": 1, "department_id": 1, "name": "전문학사" },
                   { "id": 2, "department_id": 1, "name": "전공심화" }],
  "majors":       [{ "id": 1, "department_id": 1, "name": "SW융합전공" },
                   { "id": 2, "department_id": 1, "name": "게임개발전공" }]
}
```

## GET /api/admin/ping — 관리자 권한 확인

| 호출자 | 응답 |
|---|---|
| 관리자 토큰 | 200 `{"ok": true}` |
| 학생 토큰 | 403 관리자 권한이 필요합니다 |
| 토큰 없음 | 401 로그인이 필요합니다 |

## POST /api/diagnose — 졸업 진단

헤더: `Authorization: Bearer <토큰>`

솔버를 쓰지 않고 "졸업까지 무엇을 더 들어야 하는지" 만 계산합니다.
학위과정·세부전공은 요청으로 받지 않고 **토큰의 사용자 정보**에서 가져옵니다.
교육과정은 사용자의 학위과정 + 입학년도로 고르고, 같은 입학년도가 없으면 그 학위과정의 가장 최근 교육과정을 씁니다.

```json
// 요청 — completed 는 두 종류를 섞어서 보낼 수 있음
{
  "completed": [
    { "code": "CM1108" },                                        // DB 에 있는 과목
    { "name": "글쓰기", "credits": 2, "category": "교양선택" }     // 직접 입력한 과목
  ]
}
```

- `code` 가 있으면 DB 과목. 학점·이수구분은 DB 값을 씁니다.
- `code` 가 없으면 직접 입력. `name`, `credits`(1~30), `category`(전공필수·전공선택·교양필수·교양선택) 모두 필요.
- 같은 과목(DB 과목은 code, 직접 입력은 name 기준)을 두 번 보내도 한 번만 계산합니다.

```json
// 200 응답
{
  "total":    { "completed": 73, "required": 110, "remaining": 37 },
  "major":    { "completed": 63, "required": 64,  "remaining": 1 },
  "required": {
    "completed": 0, "required": 9, "remaining": 9,
    "missing": [ { "code": "CM3107", "name": "정보처리특론", "credits": 3 }, ... ]
  },
  "major_elective_needed": 0,
  "free_needed": 28,
  "available": [
    { "code": "CM3108", "name": "캡스톤디자인1", "major": "공통", "category": "전공필수",
      "credits": 3, "offered": 1, "offered_label": "1학기", "term_index": 5 }, ...
  ],
  "prereq_warnings": [
    { "code": "CM3208", "name": "캡스톤디자인2", "prereq_code": "CM3108", "prereq_name": "캡스톤디자인1",
      "message": "캡스톤디자인2 — 캡스톤디자인1을 먼저 이수해야 합니다" }
  ],
  "unknown_codes": [],
  "graduatable": false,
  "placeholders": [
    { "code": "GE_A", "name": "교양 A", "category": "교양선택", "credits": 3,
      "offered": 3, "prereqs": [], "is_placeholder": true }, ...
  ]
}
```

| 필드 | 뜻 |
|---|---|
| `major_elective_needed` | 반드시 **전공선택**으로 채워야 하는 학점 = max(0, 남은 전공 − 남은 전필) |
| `free_needed` | 전공선택·교양 **아무거나**로 채워도 되는 학점 = max(0, 남은 총학점 − 남은 전필 − major_elective_needed) |
| `available` | 아직 안 들은 공통 + 내 전공 과목 (현장실습·학기제현장실습 제외) |
| `prereq_warnings` | `available` 중 선수과목을 아직 안 들은 과목 |
| `placeholders` | `free_needed` 를 채울 교양 가상 과목 후보. 개수 = ceil(free_needed / 2) + 2, 3학점·2학점 번갈아 |
| `offered` | 1 = 1학기, 2 = 2학기, 3 = 양학기 |

| 오류 | 메시지 |
|---|---|
| 401 | 로그인이 필요합니다 |
| 403 | 비활성화된 계정입니다 |
| 400 | 전공심화 과정 진단은 준비 중입니다 |
| 400 | 학위과정·세부전공 정보가 없는 계정입니다 (관리자 계정 등) |
| 404 | 적용할 교육과정이 없습니다 |
| 422 | 존재하지 않는 과목입니다: CM9999 (여러 개면 `, ` 로 이어서 표시) |
| 422 | 입력 형식 오류 (직접 입력 과목에 name·credits·category 누락 등) |

## GET /api/diagnose/me — 저장된 이수 내역으로 진단

헤더: `Authorization: Bearer <토큰>`

`GET /api/completed` 에 저장된 내 이수 내역으로 진단합니다. 응답 모양은 **POST /api/diagnose 와 같습니다.**
내부적으로 저장된 내역을 POST /api/diagnose 요청 본문 모양으로 바꿔 같은 계산 함수에 넘깁니다.

- **F 받은 과목은 진단에 넣지 않습니다** (= 아직 안 들은 과목, 다시 들어야 함)
- P·성적 없음 과목은 이수로 칩니다

| 오류 | 메시지 |
|---|---|
| 401 | 로그인이 필요합니다 |
| 400 | 학생 계정만 사용할 수 있습니다 (관리자 계정 등 학과가 없는 계정) |
| 400 | 전공심화 과정 진단은 준비 중입니다 |
| 404 | 적용할 교육과정이 없습니다 |

---

# 이수 내역 · 학점관리

아래 API는 모두 헤더 `Authorization: Bearer <토큰>` 필요. **자기 데이터만** 보고 고칠 수 있습니다.

## 공통 규칙

**들은 시기**
- `taken_year`: 학년 1~4
- `taken_semester`: `"1"`, `"2"`, `"여름"`, `"겨울"` (문자열. 숫자 `1`, `2` 로 보내도 받아줌)

**성적 (`grade`)**: `A+ A0 B+ B0 C+ C0 D+ D0 F P` 중 하나, 또는 `null`(성적 모름)

| 성적 | 평점 계산 | 취득학점 | 진단(이수 인정) |
|---|---|---|---|
| A+ ~ D0 | 점수대로 (A+ 4.5 … D0 1.0) | 포함 | 포함 |
| F | **0점으로 포함** | 제외 | 제외 (다시 들어야 함) |
| P | 제외 | 포함 | 포함 |
| null (성적 모름) | 제외 | 포함 | 포함 |

평점 = Σ(점수 × 학점) / Σ(평점 계산에 들어가는 과목 학점), 소수 둘째 자리 반올림.
평점 계산에 들어갈 과목이 하나도 없으면 `null`.

**중복 등록 금지 (409)**
- 학과 과목: 같은 `code` 가 이미 있으면 409
- 직접 입력 과목: 같은 이름이면 409. 이름은 **앞뒤·중간 공백을 모두 무시**하고 비교 (`"글 쓰기"` = `"글쓰기"`)
- 재수강은 새로 추가하지 않고 **PATCH 로 성적을 바꿉니다**

**통합 학기 번호(`taken_term`, 내부용)**
서버가 학년·학기로 자동 계산해 저장합니다 (로드맵 솔버용). 응답에는 나오지 않습니다.
- 정규학기: (학년 − 1) × 2 + 학기 → 1학년 1학기=1, 1학년 2학기=2, 2학년 1학기=3 …
- ⚠️ **계절학기: 학과 확인 필요 (임시 규칙)** — 여름 → 그 학년 1학기 번호, 겨울 → 그 학년 2학기 번호
  (예: 1학년 여름 → 1, 1학년 겨울 → 2). 학과 답변에 따라 바뀔 수 있음 (`backend/routers/completed.py` 의 `to_taken_term`)

## GET /api/completed — 내 이수 내역 목록

학년 → 학기(1학기 → 여름 → 2학기 → 겨울) 순, 같은 학기 안에서는 등록 순.

```json
// 200 응답
[
  { "id": 12, "code": "CM1102", "name": "웹프로그래밍기초", "major": "공통",
    "category": "전공선택", "credits": 3, "taken_year": 1, "taken_semester": "1",
    "grade": "A+", "is_custom": false },
  { "id": 13, "code": null, "name": "글쓰기", "major": null,
    "category": "교양선택", "credits": 2, "taken_year": 1, "taken_semester": "여름",
    "grade": null, "is_custom": true }
]
```

| 필드 | 뜻 |
|---|---|
| `code` | 학과 과목 코드. 직접 입력 과목은 `null` |
| `is_custom` | 직접 입력 과목(타과·교양)이면 `true` |
| `credits`, `category` | 학과 과목은 **등록할 때의 과목표 값**을 복사해 둔 것 |

## POST /api/completed — 1과목 추가

```json
// 요청 — 학과 과목 (학점·이수구분은 과목표 값을 씀)
{ "code": "CM1102", "taken_year": 1, "taken_semester": "1", "grade": "A+" }

// 요청 — 직접 입력 과목 (name·credits(1~30)·category 모두 필요)
{ "name": "글쓰기", "credits": 2, "category": "교양선택",
  "taken_year": 1, "taken_semester": "여름", "grade": null }

// 201 응답 — GET /api/completed 목록의 한 건과 같은 모양
```

- `grade` 는 빼거나 `null` 이면 성적 모름
- `code` 는 **내 교육과정** 과목에서 찾습니다. 다른 전공 과목도 등록 가능 (가상 과목은 불가)
- `category`: 전공필수·전공선택·교양필수·교양선택

| 오류 | 메시지 |
|---|---|
| 401 | 로그인이 필요합니다 |
| 400 | 학생 계정만 사용할 수 있습니다 |
| 409 | 이미 등록된 과목입니다: CM1102 (직접 입력이면 과목명) |
| 422 | 존재하지 않는 과목입니다: CM9999 |
| 422 | 학년은 1~4 중 하나여야 합니다 |
| 422 | 학기는 1, 2, 여름, 겨울 중 하나여야 합니다 |
| 422 | 성적은 A+, A0, B+, B0, C+, C0, D+, D0, F, P 중 하나여야 합니다 |
| 422 | 직접 입력한 과목은 과목명·학점·이수구분을 모두 입력해야 합니다 |

## POST /api/completed/bulk — 같은 학기 과목 여러 개 추가

예: "1학년 1학기 시간표 과목 전부 들었음". 학년·학기는 위에서 **한 번만** 보내고, `items` 에는 과목 정보와 성적만.

```json
// 요청 (items 1~100개)
{
  "taken_year": 1,
  "taken_semester": "1",
  "items": [
    { "code": "CM1101", "grade": "A+" },
    { "name": "글쓰기", "credits": 2, "category": "교양선택", "grade": null }
  ]
}

// 201 응답 — 저장된 과목 목록 (요청 순서대로, GET /api/completed 한 건과 같은 모양)
```

- **전부 저장 또는 전부 취소**: 하나라도 오류가 있으면 아무것도 저장하지 않습니다
- 이미 등록된 과목뿐 아니라 **요청 안에서 같은 과목이 두 번** 나와도 409
- 409 메시지에는 겹친 과목을 모두 표시: `이미 등록된 과목입니다: CM1101, 글쓰기`

오류는 POST /api/completed 와 같습니다.

## PATCH /api/completed/{id} — 성적·시기 수정

**보낸 필드만** 바뀝니다. 바꿀 수 있는 필드: `grade`, `taken_year`, `taken_semester`

```json
// 재수강 후 성적 바꾸기
{ "grade": "B+" }

// 성적 지우기 (성적 모름) — 필드를 빼는 것과 null 을 보내는 것은 다릅니다
{ "grade": null }

// 시기 바꾸기
{ "taken_year": 2, "taken_semester": "겨울" }

// 200 응답 — 수정된 한 건 (GET /api/completed 한 건과 같은 모양)
```

| 오류 | 메시지 |
|---|---|
| 401 | 로그인이 필요합니다 |
| 404 | 이수 내역을 찾을 수 없습니다 (없는 id 이거나 **남의 id**. 존재 여부를 알려주지 않기 위해 403 대신 404) |
| 422 | 수정할 항목(grade, taken_year, taken_semester)이 없습니다 |
| 422 | 학년·학기는 비울 수 없습니다 |
| 422 | 성적·학년·학기 형식 오류 (POST 와 같은 메시지) |

## DELETE /api/completed/{id} — 삭제

성공하면 **204** (본문 없음).

| 오류 | 메시지 |
|---|---|
| 401 | 로그인이 필요합니다 |
| 404 | 이수 내역을 찾을 수 없습니다 (없는 id 이거나 남의 id) |

## GET /api/courses — 과목 고르기 목록

이수 내역 입력 화면에서 과목을 고를 때 씁니다. 내 교육과정 중
- **공통 + 내 전공** 과목만 (다른 전공 과목은 제외. 단 POST 로 code 를 직접 보내면 등록은 가능)
- 가상 과목(`is_placeholder`) 제외

학기 번호(`term_index`) → 과목코드 순.

```json
// 200 응답
[
  { "code": "CM1101", "name": "수리능력", "major": "공통", "category": "교양선택",
    "credits": 2, "offered": 1, "offered_label": "1학기", "term_index": 1, "completed": true },
  ...
]
```

| 필드 | 뜻 |
|---|---|
| `completed` | 내 이수 내역에 이미 등록된 과목이면 `true` (F 로 등록된 과목도 `true`). 화면에서 '등록됨' 표시·409 방지용 |

| 오류 | 메시지 |
|---|---|
| 401 | 로그인이 필요합니다 |
| 400 | 학생 계정만 사용할 수 있습니다 |
| 404 | 적용할 교육과정이 없습니다 |

## GET /api/grades/summary — 학점 요약

```json
// 200 응답
{
  "gpa": 2.44,
  "major_gpa": 2.25,
  "earned_credits": 7,
  "by_category": { "전공필수": 0, "전공선택": 3, "교양": 4 },
  "terms": [
    { "year": 1, "semester": "1",    "gpa": 3.9,  "earned_credits": 5 },
    { "year": 1, "semester": "여름", "gpa": null, "earned_credits": 2 },
    { "year": 1, "semester": "2",    "gpa": 0.0,  "earned_credits": 0 }
  ]
}
```

| 필드 | 뜻 |
|---|---|
| `gpa` | 전체 평점 (4.5 만점). 계산할 성적이 없으면 `null` |
| `major_gpa` | 전공(전공필수+전공선택) 평점 |
| `earned_credits` | 취득학점 합계 (F 제외, P·성적 없음 포함) |
| `by_category` | 이수구분별 취득학점. `교양` = 교양필수 + 교양선택 |
| `terms` | 학기별 평점·취득학점. 학년 → 1학기 → 여름 → 2학기 → 겨울 순 |

이수 내역이 없으면 `gpa`·`major_gpa` 는 `null`, 학점은 0, `terms` 는 `[]`.

| 오류 | 메시지 |
|---|---|
| 401 | 로그인이 필요합니다 |
