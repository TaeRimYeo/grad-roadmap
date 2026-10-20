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