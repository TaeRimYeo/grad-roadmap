// 회원가입 화면 (시안 2·3번의 2단계 구조)
//
// 1단계: 이름 · 이메일 · 비밀번호 · 비밀번호 확인
// 2단계: 학교 → 학과 → 학위과정 · 세부전공, 학번 · 입학연도
//
// 학교·학과·학위과정·전공 선택지는 GET /api/meta/signup-options 에서 받아온다 (하드코딩 금지).
// 상위 항목을 고르면 그 아래 항목만 보이고, 상위를 바꾸면 하위 선택은 초기화된다.
//   학교 ─┬─ 학과 ─┬─ 학위과정
//         │        └─ 세부전공

import { useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Choice, Field, Input, PrimaryButton, ScreenTitle, SecondaryButton, Select } from '../components/kit'
import type { Option } from '../components/kit'
import { api } from '../api/client'
import type { SignupOptions } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { PasswordToggle } from './LoginPage'

// 입학연도 선택지: 올해부터 15년 전까지 (서버 허용 범위 2000~2100 안쪽)
const THIS_YEAR = new Date().getFullYear()
const YEAR_OPTIONS: Option[] = Array.from({ length: 16 }, (_, i) => {
  const y = THIS_YEAR - i
  return { value: y, label: String(y) }
})

// 서버와 같은 비밀번호 규칙 (backend/schemas.py validate_password). 미리 검사해서 왕복을 줄인다.
function checkPassword(pw: string): string | null {
  if (pw.length < 8) return '비밀번호는 8자 이상이어야 합니다'
  if (!/[A-Za-z]/.test(pw)) return '비밀번호에 영문자를 1자 이상 포함해야 합니다'
  if (!/\d/.test(pw)) return '비밀번호에 숫자를 1자 이상 포함해야 합니다'
  return null
}

export default function SignupPage() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState<1 | 2>(1)

  // ── 1단계 입력값 ──
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [password2, setPassword2] = useState('')
  const [showPw, setShowPw] = useState(false)

  // ── 2단계 입력값 (아직 안 골랐으면 null) ──
  const [universityId, setUniversityId] = useState<number | null>(null)
  const [departmentId, setDepartmentId] = useState<number | null>(null)
  const [programId, setProgramId] = useState<number | null>(null)
  const [majorId, setMajorId] = useState<number | null>(null)
  const [studentNo, setStudentNo] = useState('')
  const [admissionYear, setAdmissionYear] = useState<number | null>(null)

  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // ── 선택지 불러오기 ──
  const [options, setOptions] = useState<SignupOptions | null>(null)
  const [optionsError, setOptionsError] = useState('')
  const [reloadKey, setReloadKey] = useState(0) // 값을 바꾸면 아래 useEffect 가 다시 실행됨 (재시도)

  useEffect(() => {
    setOptionsError('')
    api<SignupOptions>('/api/meta/signup-options')
      .then((data) => {
        setOptions(data)
        // 학교가 하나뿐이면 미리 골라 둔다 (지금은 경기과학기술대학교 하나)
        if (data.universities.length === 1) pickUniversity(data.universities[0].id, data)
      })
      .catch((err) => setOptionsError(err.message))
    // pickUniversity 는 setState 만 부르므로 의존성에서 빼도 안전하다
  }, [reloadKey])

  // 상위 선택에 따라 걸러진 선택지. useMemo = 의존값이 바뀔 때만 다시 계산
  const universityOptions = useMemo<Option[]>(
    () => options?.universities.map((u) => ({ value: u.id, label: u.name })) ?? [],
    [options],
  )
  const departmentOptions = useMemo<Option[]>(
    () =>
      options?.departments
        .filter((d) => d.university_id === universityId)
        .map((d) => ({ value: d.id, label: d.name })) ?? [],
    [options, universityId],
  )
  const programOptions = useMemo<Option[]>(
    () =>
      options?.programs
        .filter((p) => p.department_id === departmentId)
        .map((p) => ({ value: p.id, label: p.name })) ?? [],
    [options, departmentId],
  )
  const majorOptions = useMemo<Option[]>(
    () =>
      options?.majors
        .filter((m) => m.department_id === departmentId)
        .map((m) => ({ value: m.id, label: m.name })) ?? [],
    [options, departmentId],
  )

  // 학교를 바꾸면 학과 이하 초기화. 그 학교 학과가 하나뿐이면 자동 선택
  function pickUniversity(id: number, data: SignupOptions | null = options) {
    setUniversityId(id)
    const depts = data?.departments.filter((d) => d.university_id === id) ?? []
    setDepartmentId(depts.length === 1 ? depts[0].id : null)
    setProgramId(null)
    setMajorId(null)
  }

  // 학과를 바꾸면 학위과정·전공 초기화
  function pickDepartment(id: number) {
    setDepartmentId(id)
    setProgramId(null)
    setMajorId(null)
  }

  // 학번: 숫자만 남긴다. 앞 4자리가 새로 정해지거나 바뀌면 입학연도를 자동으로 채운다.
  // 사용자가 입학연도를 직접 고친 뒤에는, 학번 앞 4자리가 다시 바뀌기 전까지 그 값을 유지한다.
  function changeStudentNo(raw: string) {
    const digits = raw.replace(/\D/g, '')
    const oldPrefix = studentNo.slice(0, 4)
    const newPrefix = digits.slice(0, 4)
    setStudentNo(digits)
    if (newPrefix.length === 4 && newPrefix !== oldPrefix) {
      const year = Number(newPrefix)
      // 선택지에 있는 연도일 때만 채운다 (예: 학번이 1234... 면 무시)
      if (YEAR_OPTIONS.some((o) => o.value === year)) setAdmissionYear(year)
    }
  }

  // ── 1단계 → 2단계 ──
  function handleNext(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return setError('이름을 입력해 주세요')
    if (!email.trim()) return setError('이메일을 입력해 주세요')
    const pwError = checkPassword(password)
    if (pwError) return setError(pwError)
    if (password !== password2) return setError('비밀번호가 일치하지 않습니다')
    setError('')
    setStep(2)
  }

  // ── 가입 완료 ──
  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (submitting) return
    if (departmentId === null || programId === null || majorId === null) {
      return setError('학교·학과·학위과정·세부전공을 모두 선택해 주세요')
    }
    if (!studentNo) return setError('학번을 입력해 주세요')
    if (admissionYear === null) return setError('입학연도를 선택해 주세요')

    setError('')
    setSubmitting(true)
    try {
      // 가입 + 자동 로그인 (AuthContext.signup). role 은 보내지 않는다 — 서버가 student 로 고정
      await signup({
        email: email.trim(),
        password,
        name: name.trim(),
        student_no: studentNo,
        department_id: departmentId,
        program_id: programId,
        major_id: majorId,
        admission_year: admissionYear,
      })
      navigate('/', { replace: true })
    } catch (err) {
      // 예: "이미 가입된 이메일입니다" → 1단계로 돌아가 이메일을 고칠 수 있다
      setError(err instanceof Error ? err.message : '회원가입에 실패했습니다')
      setSubmitting(false)
    }
  }

  function goBack() {
    setError('')
    if (step === 2) setStep(1)
    else navigate('/login')
  }

  return (
    <div className="flex flex-1 flex-col px-5 pb-6">
      <SignupHeader step={step} onBack={goBack} />

      {step === 1 ? (
        <form onSubmit={handleNext} className="flex flex-1 flex-col">
          <div className="mt-3">
            <ScreenTitle>계정 정보를 입력해요</ScreenTitle>
          </div>
          <div className="mt-6 flex flex-1 flex-col gap-4">
            <Field label="이름">
              <Input placeholder="이름 입력" autoComplete="name" value={name} onChange={setName} />
            </Field>
            <Field label="학교 이메일">
              <Input
                type="email"
                inputMode="email"
                autoComplete="email"
                placeholder="name@school.ac.kr"
                value={email}
                onChange={setEmail}
              />
            </Field>
            <Field label="비밀번호">
              <Input
                type={showPw ? 'text' : 'password'}
                autoComplete="new-password"
                placeholder="비밀번호 입력"
                value={password}
                onChange={setPassword}
                trailing={<PasswordToggle shown={showPw} onToggle={() => setShowPw((v) => !v)} />}
              />
            </Field>
            <Field label="비밀번호 확인">
              <Input
                type={showPw ? 'text' : 'password'}
                autoComplete="new-password"
                placeholder="비밀번호 재입력"
                value={password2}
                onChange={setPassword2}
              />
            </Field>
            <p className="text-[12px] font-medium text-sub">
              영문과 숫자를 포함해 8자 이상으로 설정해 주세요.
            </p>
            {error && <p className="text-[13px] font-medium text-danger">{error}</p>}
          </div>
          <PrimaryButton type="submit" className="mt-6">
            다음
          </PrimaryButton>
        </form>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-1 flex-col">
          <div className="mt-3">
            <ScreenTitle>학적 정보를 알려주세요</ScreenTitle>
          </div>

          {!options ? (
            // 선택지 로딩 중 / 실패
            <div className="mt-6 flex flex-1 flex-col gap-4">
              {optionsError ? (
                <>
                  <p className="text-[13px] font-medium text-danger">{optionsError}</p>
                  <SecondaryButton onClick={() => setReloadKey((k) => k + 1)}>다시 시도</SecondaryButton>
                </>
              ) : (
                <p className="text-[15px] text-sub">선택지를 불러오는 중...</p>
              )}
            </div>
          ) : (
            <div className="mt-6 flex flex-1 flex-col gap-4">
              <Field label="학교">
                <Select
                  options={universityOptions}
                  value={universityId}
                  onChange={(id) => pickUniversity(id)}
                  placeholder="학교 선택"
                />
              </Field>
              <Field label="학과">
                <Select
                  options={departmentOptions}
                  value={departmentId}
                  onChange={pickDepartment}
                  placeholder={universityId === null ? '학교를 먼저 선택해 주세요' : '학과 선택'}
                  disabled={universityId === null}
                />
              </Field>
              {/* label 안에 버튼(Segment)이 있으면 글자를 눌렀을 때 첫 버튼이 눌리므로 div 로 감싼다 */}
              <ChoiceField label="학위과정">
                <Choice
                  options={programOptions}
                  value={programId}
                  onChange={setProgramId}
                  placeholder="학과를 먼저 선택해 주세요"
                />
              </ChoiceField>
              <ChoiceField label="세부전공">
                <Choice
                  options={majorOptions}
                  value={majorId}
                  onChange={setMajorId}
                  placeholder="학과를 먼저 선택해 주세요"
                />
              </ChoiceField>
              <div className="flex gap-3">
                <div className="min-w-0 flex-1">
                  <Field label="학번">
                    <Input
                      inputMode="numeric"
                      placeholder="학번 입력"
                      maxLength={20}
                      value={studentNo}
                      onChange={changeStudentNo}
                    />
                  </Field>
                </div>
                <div className="min-w-0 flex-1">
                  <Field label="입학연도">
                    <Select
                      options={YEAR_OPTIONS}
                      value={admissionYear}
                      onChange={setAdmissionYear}
                      placeholder="선택"
                    />
                  </Field>
                </div>
              </div>
              <p className="text-[12px] font-medium text-sub">
                학번 앞 4자리로 입학연도가 자동 입력돼요. 다르면 직접 바꿔 주세요.
              </p>
              {error && <p className="text-[13px] font-medium text-danger">{error}</p>}
            </div>
          )}

          <PrimaryButton type="submit" disabled={submitting || !options} className="mt-6">
            {submitting ? '처리 중...' : '가입 완료'}
          </PrimaryButton>
        </form>
      )}
    </div>
  )
}

// 상단: 뒤로가기 + 단계 진행 막대 (시안의 SignupHeader 와 같은 모양)
function SignupHeader({ step, onBack }: { step: 1 | 2; onBack: () => void }) {
  return (
    <div className="flex items-center gap-3 pb-2 pt-1">
      <button
        type="button"
        onClick={onBack}
        aria-label="뒤로"
        className="-ml-2 flex h-11 w-11 items-center justify-center"
      >
        <ArrowLeft size={24} className="text-ink" />
      </button>
      <div className="flex flex-1 items-center gap-2">
        <span className="text-[15px] font-bold text-brand">{step}</span>
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-lav">
          <div className="h-full rounded-full bg-brand" style={{ width: step === 1 ? '50%' : '100%' }} />
        </div>
        <span className="text-[15px] font-bold text-[#c3bcda]">/ 2</span>
      </div>
    </div>
  )
}

// kit 의 Field 와 같은 모양이지만 <label> 대신 <div> (버튼 묶음용)
function ChoiceField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-[13px] font-semibold text-ink">{label}</span>
      {children}
    </div>
  )
}
