// 백엔드 응답·요청의 모양 (docs/api.md 기준)

// GET /api/auth/me
export type Me = {
  id: number
  email: string
  name: string
  role: 'student' | 'admin'
  student_no: string | null
  admission_year: number | null
  department: string | null
  program: string | null
  major: string | null
}

// POST /api/auth/login
export type LoginResponse = {
  access_token: string
  token_type: 'bearer'
  user: { id: number; name: string; role: string }
}

// POST /api/auth/signup 요청 (role 은 서버가 student 로 고정하므로 보내지 않는다)
export type SignupRequest = {
  email: string
  password: string
  name: string
  student_no: string
  department_id: number
  program_id: number
  major_id: number
  admission_year: number
}

// GET /api/meta/signup-options
export type SignupOptions = {
  universities: { id: number; name: string }[]
  departments: { id: number; university_id: number; name: string }[]
  programs: { id: number; department_id: number; name: string }[]
  majors: { id: number; department_id: number; name: string }[]
}

// ── 이수 내역 · 학점관리 ────────────────────────────────────────

// 성적. 백엔드 허용값과 똑같은 순서·목록 (docs/api.md "성적 (grade)")
// 성적 모름은 목록에 넣지 않고 null 로 표현한다
export const GRADES = ['A+', 'A0', 'B+', 'B0', 'C+', 'C0', 'D+', 'D0', 'F', 'P'] as const
export type Grade = (typeof GRADES)[number]

// 들은 학기. 서버는 문자열로 주고받는다
export const SEMESTERS = ['1', '2', '여름', '겨울'] as const
export type Semester = (typeof SEMESTERS)[number]

export type Category = '전공필수' | '전공선택' | '교양필수' | '교양선택'

// GET /api/completed 목록의 한 건 (POST·PATCH 응답도 같은 모양)
export type CompletedItem = {
  id: number
  code: string | null // 직접 입력 과목은 null
  name: string
  major: string | null
  category: Category
  credits: number
  taken_year: number
  taken_semester: Semester
  grade: Grade | null // null = 성적 모름
  is_custom: boolean
}

// GET /api/courses 목록의 한 건
export type CourseItem = {
  code: string
  name: string
  major: string
  category: Category
  credits: number
  offered: number // 1 = 1학기, 2 = 2학기, 3 = 양학기
  offered_label: string
  term_index: number // 1학년 1학기 = 1, 1학년 2학기 = 2 …
  completed: boolean // 이미 등록된 과목이면 true
}

// GET /api/grades/summary
export type GradesSummary = {
  gpa: number | null
  major_gpa: number | null
  earned_credits: number
  by_category: { 전공필수: number; 전공선택: number; 교양: number }
  terms: { year: number; semester: Semester; gpa: number | null; earned_credits: number }[]
}

// GET /api/diagnose/me (학점관리 화면에서 쓰는 필드만)
type CreditProgress = { completed: number; required: number; remaining: number }
export type DiagnoseResult = {
  total: CreditProgress
  major: CreditProgress
  required: CreditProgress & { missing: { code: string; name: string; credits: number }[] }
  graduatable: boolean
}

// POST /api/completed/bulk 요청
//   학과 과목은 code 만, 직접 입력 과목은 name·credits·category 를 보낸다
export type BulkItem =
  | { code: string; grade: Grade | null }
  | { name: string; credits: number; category: Category; grade: Grade | null }
export type BulkRequest = {
  taken_year: number
  taken_semester: Semester
  items: BulkItem[]
}
