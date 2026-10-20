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