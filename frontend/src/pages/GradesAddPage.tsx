// 과목 추가 화면 (/grades/add)
//
// 순서
//   1) 학년·학기 고르기
//   2) GET /api/courses 목록에서 체크박스로 여러 과목 고르기
//      - 고른 학기에 개설되는 과목(term_index 가 같은 과목)은 위 "이 학기 과목"
//      - 나머지는 아래 "다른 학기 과목" (접혀 있음)
//      - 이미 등록된 과목(completed: true)은 회색 + "등록됨", 고를 수 없음
//   3) 고른 과목마다 성적 고르기 (기본값: 성적 없음)
//   4) 목록에 없는 과목(타과·교양)은 직접 입력
//   5) POST /api/completed/bulk 로 한 번에 저장 → 성공하면 /grades 로
//
// bulk 는 "전부 저장 또는 전부 취소" 라서, 하나라도 겹치면(409) 아무것도 저장되지 않는다.

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ChevronDown, Search, X } from 'lucide-react'
import { api } from '../api/client'
import { GRADES, SEMESTERS } from '../api/types'
import type { BulkItem, BulkRequest, Category, CourseItem, Grade } from '../api/types'
import type { Option } from '../components/kit'
import {
  Card,
  Field,
  Input,
  PrimaryButton,
  ScreenTitle,
  SecondaryButton,
  SectionTitle,
  Segment,
  Select,
  StatusPill,
  TypeBadge,
} from '../components/kit'

// 성적 선택지 = 백엔드 허용 성적 10개 + 성적 없음(null)
// kit 의 Select 는 숫자 value 를 쓰므로 "목록 안의 순서(index)" 를 value 로 쓴다
const GRADE_CHOICES: (Grade | null)[] = [...GRADES, null]
const GRADE_OPTIONS: Option[] = GRADE_CHOICES.map((g, i) => ({ value: i, label: g ?? '성적 없음' }))
const NO_GRADE = GRADE_CHOICES.length - 1 // 기본값 "성적 없음" 의 index

const YEAR_OPTIONS: Option[] = [1, 2, 3, 4].map((y) => ({ value: y, label: `${y}학년` }))
// 학기도 index 로: 0 → '1', 1 → '2', 2 → '여름', 3 → '겨울'
const SEMESTER_OPTIONS: Option[] = SEMESTERS.map((s, i) => ({
  value: i,
  label: s === '1' || s === '2' ? `${s}학기` : s,
}))

const CREDIT_OPTIONS: Option[] = [1, 2, 3, 4].map((c) => ({ value: c, label: `${c}학점` }))
// 직접 입력 과목의 이수구분은 전공선택·교양선택 두 가지만
const CUSTOM_CATEGORIES: Category[] = ['전공선택', '교양선택']
const CATEGORY_OPTIONS: Option[] = CUSTOM_CATEGORIES.map((c, i) => ({ value: i, label: c }))

// 직접 입력한 과목 한 건 (화면 안에서만 쓰는 모양)
type CustomCourse = { key: number; name: string; credits: number; category: Category; grade: number }

// 이름 비교용: 공백을 모두 지운다 (서버도 "글 쓰기" = "글쓰기" 로 본다)
const squash = (s: string) => s.replace(/\s/g, '')

export default function GradesAddPage() {
  const navigate = useNavigate()

  // 1) 학년·학기
  const [year, setYear] = useState(1)
  const [semIdx, setSemIdx] = useState(0)

  // 2) 과목 목록
  const [courses, setCourses] = useState<CourseItem[]>([])
  const [loadError, setLoadError] = useState('')
  const [query, setQuery] = useState('')
  const [othersOpen, setOthersOpen] = useState(false)

  // 3) 고른 과목: { 과목코드: 성적 index }
  const [picked, setPicked] = useState<Record<string, number>>({})

  // 4) 직접 입력
  const [customOpen, setCustomOpen] = useState(false)
  const [customs, setCustoms] = useState<CustomCourse[]>([])
  const [cName, setCName] = useState('')
  const [cCredits, setCCredits] = useState(3)
  const [cCatIdx, setCCatIdx] = useState(1) // 기본 교양선택
  const [customError, setCustomError] = useState('')
  const [nextKey, setNextKey] = useState(1)

  // 5) 저장
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api<CourseItem[]>('/api/courses')
      .then(setCourses)
      .catch((err: Error) => setLoadError(err.message))
  }, [])

  // ── 목록 나누기 ──
  // 정규학기면 term_index = (학년 − 1) × 2 + 학기. 여름·겨울은 정해진 개설 과목이 없다
  const termIndex = semIdx <= 1 ? (year - 1) * 2 + (semIdx + 1) : null
  const matches = (c: CourseItem) => squash(c.name).includes(squash(query))
  const thisTerm = courses.filter((c) => c.term_index === termIndex)
  const others = courses.filter((c) => c.term_index !== termIndex)
  const shownThis = thisTerm.filter(matches)
  const shownOthers = others.filter(matches)
  // 검색 중이면 "다른 학기 과목" 도 펼쳐서 결과가 보이게 한다
  const othersVisible = othersOpen || query.trim() !== ''

  function toggle(code: string) {
    setPicked((prev) => {
      const next = { ...prev }
      if (code in next) delete next[code]
      else next[code] = NO_GRADE
      return next
    })
  }

  // 이 학기 과목 중 등록 안 된 것 전부 고르기 (이미 고른 과목의 성적은 그대로)
  function pickAllThisTerm() {
    setPicked((prev) => {
      const next = { ...prev }
      for (const c of thisTerm) {
        if (!c.completed && !(c.code in next)) next[c.code] = NO_GRADE
      }
      return next
    })
  }

  function addCustom() {
    const name = cName.trim()
    if (!name) return setCustomError('과목명을 입력해 주세요')
    if (customs.some((c) => squash(c.name) === squash(name))) {
      return setCustomError('이미 추가한 과목명이에요')
    }
    setCustoms([
      ...customs,
      { key: nextKey, name, credits: cCredits, category: CUSTOM_CATEGORIES[cCatIdx], grade: NO_GRADE },
    ])
    setNextKey(nextKey + 1)
    setCName('')
    setCustomError('')
  }

  // 고른 과목을 과목표 순서대로 (성적 고르기 카드에 쓰임)
  const pickedCourses = courses.filter((c) => c.code in picked)
  const count = pickedCourses.length + customs.length

  async function save() {
    setSaving(true)
    setError('')
    const items: BulkItem[] = [
      ...pickedCourses.map((c) => ({ code: c.code, grade: GRADE_CHOICES[picked[c.code]] })),
      ...customs.map((c) => ({
        name: c.name,
        credits: c.credits,
        category: c.category,
        grade: GRADE_CHOICES[c.grade],
      })),
    ]
    const body: BulkRequest = { taken_year: year, taken_semester: SEMESTERS[semIdx], items }
    try {
      await api('/api/completed/bulk', { method: 'POST', body })
      // /grades 화면은 새로 열리면서 목록을 다시 불러온다
      navigate('/grades')
    } catch (err) {
      // 409 등 서버 메시지를 그대로 보여준다
      setError((err as Error).message)
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-5 px-5 pb-6 pt-4">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate('/grades')}
          aria-label="뒤로"
          className="-ml-2 flex min-h-11 min-w-11 items-center justify-center text-ink"
        >
          <ArrowLeft size={24} />
        </button>
        <ScreenTitle>과목 추가</ScreenTitle>
      </div>

      {/* 1) 학년·학기 */}
      <section className="flex flex-col gap-3">
        <SectionTitle>언제 들었나요?</SectionTitle>
        <Segment options={YEAR_OPTIONS} value={year} onChange={setYear} />
        <Segment options={SEMESTER_OPTIONS} value={semIdx} onChange={setSemIdx} />
      </section>

      {/* 2) 과목 고르기 */}
      <section className="flex flex-col gap-3">
        <SectionTitle>과목 고르기</SectionTitle>
        <Input
          placeholder="과목명 검색"
          value={query}
          onChange={setQuery}
          trailing={<Search size={20} className="text-[#a8a2bc]" />}
        />
        {loadError && <p className="text-[13px] font-medium text-danger">{loadError}</p>}

        {/* 이 학기 과목 */}
        <div className="flex items-center justify-between">
          <span className="text-[13px] font-semibold text-ink">이 학기 과목</span>
          {thisTerm.length > 0 && (
            <button
              type="button"
              onClick={pickAllThisTerm}
              className="min-h-11 text-[13px] font-semibold text-brand"
            >
              이 학기 과목 전체 선택
            </button>
          )}
        </div>
        <Card className="divide-y divide-black/5 py-1">
          {shownThis.length === 0 ? (
            <p className="py-2.5 text-[13px] text-sub">
              {termIndex === null
                ? '계절학기는 정해진 개설 과목이 없어요. 아래 목록이나 직접 입력을 써 주세요.'
                : '해당하는 과목이 없어요'}
            </p>
          ) : (
            shownThis.map((c) => (
              <CourseRow key={c.code} course={c} checked={c.code in picked} onToggle={toggle} />
            ))
          )}
        </Card>

        {/* 다른 학기 과목 (접힘) */}
        <button
          type="button"
          onClick={() => setOthersOpen(!othersOpen)}
          className="flex min-h-11 items-center justify-between text-[13px] font-semibold text-ink"
        >
          <span>다른 학기 과목 ({shownOthers.length})</span>
          <ChevronDown size={20} className={`text-sub ${othersVisible ? 'rotate-180' : ''}`} />
        </button>
        {othersVisible && (
          <Card className="divide-y divide-black/5 py-1">
            {shownOthers.length === 0 ? (
              <p className="py-2.5 text-[13px] text-sub">해당하는 과목이 없어요</p>
            ) : (
              shownOthers.map((c) => (
                <CourseRow key={c.code} course={c} checked={c.code in picked} onToggle={toggle} />
              ))
            )}
          </Card>
        )}
      </section>

      {/* 4) 직접 입력 (접힘) */}
      <section className="flex flex-col gap-3">
        <button
          type="button"
          onClick={() => setCustomOpen(!customOpen)}
          className="flex min-h-11 items-center justify-between text-[13px] font-semibold text-ink"
        >
          <span>목록에 없는 과목 직접 입력</span>
          <ChevronDown size={20} className={`text-sub ${customOpen ? 'rotate-180' : ''}`} />
        </button>
        {customOpen && (
          <Card className="flex flex-col gap-4">
            <Field label="과목명">
              <Input placeholder="예) 글쓰기" value={cName} onChange={setCName} maxLength={100} />
            </Field>
            <div className="flex flex-col gap-2">
              <span className="text-[13px] font-semibold text-ink">학점</span>
              <Segment options={CREDIT_OPTIONS} value={cCredits} onChange={setCCredits} />
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-[13px] font-semibold text-ink">이수구분</span>
              <Segment options={CATEGORY_OPTIONS} value={cCatIdx} onChange={setCCatIdx} />
            </div>
            {customError && <p className="text-[13px] font-medium text-danger">{customError}</p>}
            <SecondaryButton onClick={addCustom}>추가</SecondaryButton>
          </Card>
        )}
      </section>

      {/* 3) 고른 과목의 성적 */}
      {count > 0 && (
        <section className="flex flex-col gap-3">
          <SectionTitle>성적 입력</SectionTitle>
          <Card className="flex flex-col divide-y divide-black/5 py-1">
            {pickedCourses.map((c) => (
              <GradeLine
                key={c.code}
                name={c.name}
                category={c.category}
                credits={c.credits}
                grade={picked[c.code]}
                onGrade={(g) => setPicked({ ...picked, [c.code]: g })}
                onRemove={() => toggle(c.code)}
              />
            ))}
            {customs.map((c) => (
              <GradeLine
                key={`custom-${c.key}`}
                name={c.name}
                category={c.category}
                credits={c.credits}
                grade={c.grade}
                onGrade={(g) =>
                  setCustoms(customs.map((x) => (x.key === c.key ? { ...x, grade: g } : x)))
                }
                onRemove={() => setCustoms(customs.filter((x) => x.key !== c.key))}
              />
            ))}
          </Card>
        </section>
      )}

      {/* 5) 저장 */}
      {error && <p className="text-[13px] font-medium text-danger">{error}</p>}
      <PrimaryButton disabled={count === 0 || saving} onClick={save}>
        {saving ? '저장 중...' : `${count}과목 저장`}
      </PrimaryButton>
    </div>
  )
}

// 체크박스 한 줄. 이미 등록된 과목은 회색 + "등록됨" + 선택 불가
function CourseRow({
  course,
  checked,
  onToggle,
}: {
  course: CourseItem
  checked: boolean
  onToggle: (code: string) => void
}) {
  const done = course.completed
  return (
    <label
      className={`flex min-h-11 items-center gap-3 py-2.5 ${done ? 'opacity-50' : 'cursor-pointer'}`}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={done}
        onChange={() => onToggle(course.code)}
        className="h-5 w-5 shrink-0 accent-brand"
      />
      <TypeBadge type={course.category} short />
      <span className="min-w-0 flex-1 truncate text-[15px] font-medium text-ink">{course.name}</span>
      {done ? (
        <StatusPill tone="muted">등록됨</StatusPill>
      ) : (
        <span className="text-[12px] text-sub">{course.credits}학점</span>
      )}
    </label>
  )
}

// 성적 입력 카드의 한 줄: 과목 정보 + 성적 드롭다운 + 빼기 버튼
function GradeLine({
  name,
  category,
  credits,
  grade,
  onGrade,
  onRemove,
}: {
  name: string
  category: Category
  credits: number
  grade: number
  onGrade: (g: number) => void
  onRemove: () => void
}) {
  return (
    <div className="flex flex-col gap-2 py-3">
      <div className="flex items-center gap-2">
        <TypeBadge type={category} short />
        <span className="min-w-0 flex-1 truncate text-[15px] font-medium text-ink">{name}</span>
        <span className="text-[12px] text-sub">{credits}학점</span>
        <button
          type="button"
          onClick={onRemove}
          aria-label={`${name} 빼기`}
          className="-mr-2 flex min-h-11 min-w-11 items-center justify-center text-sub"
        >
          <X size={18} />
        </button>
      </div>
      <Select options={GRADE_OPTIONS} value={grade} onChange={onGrade} />
    </div>
  )
}
