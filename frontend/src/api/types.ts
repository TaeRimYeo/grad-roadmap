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
