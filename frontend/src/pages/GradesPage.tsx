// 학점관리 화면 (/grades)
//
// 불러오는 API (세 개를 동시에)
//   GET /api/completed      → 학기별 과목 목록
//   GET /api/grades/summary → 평점·취득학점·이수구분별 학점·학기별 평점
//   GET /api/diagnose/me    → 졸업학점(total.required), 전공·전공필수 필요 학점
//     진단은 실패할 수 있다(예: 전공심화 과정은 400). 그때도 나머지 화면은 보여주고 기준값만 "-"
//
// 과목을 누르면 아래에서 바텀시트가 올라와 성적 변경(PATCH)·삭제(DELETE)를 할 수 있다.

import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plus, X } from 'lucide-react'
import { api } from '../api/client'
import { GRADES } from '../api/types'
import type {
  CompletedItem,
  DiagnoseResult,
  Grade,
  GradesSummary,
  Semester,
} from '../api/types'
import {
  Card,
  PrimaryButton,
  Progress,
  ScreenTitle,
  SecondaryButton,
  SectionTitle,
  TypeBadge,
} from '../components/kit'

// '1' → '1학기', '여름' → '여름학기'
function semesterLabel(s: Semester) {
  return `${s}학기`
}

// 평점 표시: null 이면 "-", 아니면 소수 둘째 자리까지
function gpaText(gpa: number | null) {
  return gpa === null ? '-' : gpa.toFixed(2)
}

// 성적 글자 색: F 는 빨강, 성적 없음은 회색, 나머지는 brand
function gradeClass(grade: Grade | null) {
  if (grade === 'F') return 'text-danger'
  if (grade === null) return 'text-sub'
  return 'text-brand'
}

// 같은 학년·학기 과목끼리 묶는다. 서버가 이미 학기 순으로 정렬해서 주므로 순서는 그대로 둔다
type TermGroup = { year: number; semester: Semester; items: CompletedItem[] }
function groupByTerm(list: CompletedItem[]): TermGroup[] {
  const groups: TermGroup[] = []
  for (const item of list) {
    const last = groups[groups.length - 1]
    if (last && last.year === item.taken_year && last.semester === item.taken_semester) {
      last.items.push(item)
    } else {
      groups.push({ year: item.taken_year, semester: item.taken_semester, items: [item] })
    }
  }
  return groups
}

export default function GradesPage() {
  const navigate = useNavigate()
  const [completed, setCompleted] = useState<CompletedItem[]>([])
  const [summary, setSummary] = useState<GradesSummary | null>(null)
  const [diagnose, setDiagnose] = useState<DiagnoseResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  // 바텀시트에 띄운 과목 (null 이면 시트 닫힘)
  const [selected, setSelected] = useState<CompletedItem | null>(null)

  // 세 API 를 다시 불러온다. 성적 변경·삭제 후에도 이 함수를 부른다
  const load = useCallback(async () => {
    setError('')
    try {
      const [c, s] = await Promise.all([
        api<CompletedItem[]>('/api/completed'),
        api<GradesSummary>('/api/grades/summary'),
      ])
      setCompleted(c)
      setSummary(s)
    } catch (err) {
      setError((err as Error).message)
    }
    // 진단은 따로: 실패해도 위 내용은 보여준다
    try {
      setDiagnose(await api<DiagnoseResult>('/api/diagnose/me'))
    } catch {
      setDiagnose(null)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (loading) {
    return (
      <div className="flex flex-col gap-6 px-5 pb-6 pt-4">
        <ScreenTitle>학점관리</ScreenTitle>
        <p className="text-[15px] text-sub">불러오는 중...</p>
      </div>
    )
  }

  const groups = groupByTerm(completed)
  // 전공선택 기준 = 전공 필요 학점 − 전공필수 필요 학점 (예: 64 − 9 = 55)
  const majorElectiveRequired = diagnose
    ? diagnose.major.required - diagnose.required.required
    : null

  return (
    <div className="flex flex-col gap-5 px-5 pb-6 pt-4">
      <div className="flex items-center justify-between">
        <ScreenTitle>학점관리</ScreenTitle>
        <Link
          to="/grades/add"
          className="inline-flex min-h-11 items-center gap-1 rounded-full bg-lav px-3.5 text-[13px] font-semibold text-brand"
        >
          <Plus size={16} /> 과목 추가
        </Link>
      </div>

      {error && <p className="text-[13px] font-medium text-danger">{error}</p>}

      {summary && (
        <>
          {/* 요약 카드: 전체 평점 · 전공 평점 · 취득학점 / 졸업학점 */}
          <Card className="flex flex-col gap-3">
            <div className="flex items-baseline justify-between">
              <span className="text-[14px] font-semibold text-ink">전체 평점</span>
              <span className="text-[20px] font-bold text-brand">
                {gpaText(summary.gpa)}{' '}
                <span className="text-[13px] font-semibold text-sub">/ 4.5</span>
              </span>
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-[14px] font-semibold text-ink">전공 평점</span>
              <span className="text-[20px] font-bold text-brand">
                {gpaText(summary.major_gpa)}{' '}
                <span className="text-[13px] font-semibold text-sub">/ 4.5</span>
              </span>
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-[14px] font-semibold text-ink">취득학점</span>
              <span className="text-[20px] font-bold text-brand">
                {summary.earned_credits}{' '}
                <span className="text-[13px] font-semibold text-sub">
                  / {diagnose ? diagnose.total.required : '-'}학점
                </span>
              </span>
            </div>
          </Card>

          {/* 이수구분별 학점 */}
          <Card className="flex flex-col gap-4">
            <CategoryRow
              label="전공필수"
              value={summary.by_category.전공필수}
              max={diagnose ? diagnose.required.required : null}
            />
            <CategoryRow
              label="전공선택"
              value={summary.by_category.전공선택}
              max={majorElectiveRequired}
            />
            {/* 교양은 최소요건이 없어서 막대 없이 학점만 */}
            <div className="flex items-baseline justify-between">
              <span className="text-[14px] font-semibold text-ink">교양</span>
              <span className="text-[13px] font-bold text-sub">
                <span className="text-ink">{summary.by_category.교양}</span>학점 · 최소요건 없음
              </span>
            </div>
          </Card>
        </>
      )}

      {/* 학기별 목록 */}
      {groups.length === 0 ? (
        !error && (
          <Card className="flex flex-col items-center gap-4 py-8">
            <p className="text-[15px] text-sub">아직 등록된 과목이 없어요</p>
            <PrimaryButton onClick={() => navigate('/grades/add')}>과목 추가</PrimaryButton>
          </Card>
        )
      ) : (
        groups.map((g) => {
          // 그 학기 평점은 summary.terms 에서 찾는다
          const term = summary?.terms.find((t) => t.year === g.year && t.semester === g.semester)
          return (
            <section key={`${g.year}-${g.semester}`} className="flex flex-col gap-2">
              <SectionTitle
                action={
                  <span className="text-[13px] font-bold text-brand">
                    평점 {gpaText(term?.gpa ?? null)}
                  </span>
                }
              >
                {g.year}학년 {semesterLabel(g.semester)}
              </SectionTitle>
              <Card className="divide-y divide-black/5 py-1">
                {g.items.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setSelected(item)}
                    className="flex min-h-11 w-full items-center gap-3 py-2.5 text-left"
                  >
                    <TypeBadge type={item.category} short />
                    <span className="min-w-0 flex-1 truncate text-[15px] font-medium text-ink">
                      {item.name}
                    </span>
                    <span className="text-[12px] text-sub">{item.credits}학점</span>
                    <span className={`w-9 text-right text-[15px] font-bold ${gradeClass(item.grade)}`}>
                      {item.grade ?? '-'}
                    </span>
                  </button>
                ))}
              </Card>
            </section>
          )
        })
      )}

      {selected && (
        <CourseSheet
          item={selected}
          onClose={() => setSelected(null)}
          onChanged={() => {
            setSelected(null)
            load()
          }}
        />
      )}
    </div>
  )
}

// 이수구분 한 줄 (시안의 SummaryRow 모양). max 를 모르면 "-" + 빈 막대
function CategoryRow({ label, value, max }: { label: string; value: number; max: number | null }) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-[14px] font-semibold text-ink">{label}</span>
        <span className="text-[13px] font-bold text-sub">
          <span className="text-ink">{value}</span> / {max ?? '-'}학점
        </span>
      </div>
      <div className="mt-2">
        <Progress value={max ? value : 0} max={max || 1} />
      </div>
    </div>
  )
}

// ── 바텀시트 ────────────────────────────────────────────────────
// 화면 아래에서 올라오는 흰 판. 뒤쪽 어두운 부분을 누르면 닫힌다.
// fixed 라서 화면 전체 기준으로 붙고, 안쪽은 앱 폭(480px)에 맞춘다.
// 삭제는 브라우저 confirm() 대신 시트 안에서 "삭제할까요?" 로 한 번 더 묻는다.
function CourseSheet({
  item,
  onClose,
  onChanged,
}: {
  item: CompletedItem
  onClose: () => void
  onChanged: () => void
}) {
  const [confirming, setConfirming] = useState(false) // 삭제 확인 단계인지
  const [busy, setBusy] = useState(false) // 서버 요청 중이면 버튼 잠금
  const [error, setError] = useState('')

  // 성적 버튼 목록 = 백엔드 허용 성적 10개 + 성적 없음(null)
  const choices: (Grade | null)[] = [...GRADES, null]

  async function changeGrade(grade: Grade | null) {
    if (grade === item.grade) return onClose() // 같은 성적이면 요청 없이 닫기
    setBusy(true)
    setError('')
    try {
      // grade: null 을 보내면 "성적 모름" 으로 바뀐다
      await api(`/api/completed/${item.id}`, { method: 'PATCH', body: { grade } })
      onChanged()
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }

  async function remove() {
    setBusy(true)
    setError('')
    try {
      await api(`/api/completed/${item.id}`, { method: 'DELETE' })
      onChanged()
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex items-end justify-center bg-ink/40" onClick={onClose}>
      <div
        className="w-full max-w-[480px] rounded-t-2xl bg-white px-5 pt-4"
        style={{ paddingBottom: 'max(env(safe-area-inset-bottom), 20px)' }}
        // 시트 안을 누른 건 바깥(닫기)으로 전달하지 않는다
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <SectionTitle>{item.name}</SectionTitle>
            <div className="mt-1 flex items-center gap-1.5">
              <TypeBadge type={item.category} short />
              <span className="text-[12px] font-medium text-sub">
                {item.credits}학점 · {item.taken_year}학년 {semesterLabel(item.taken_semester)}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            className="flex min-h-11 min-w-11 items-center justify-center text-sub"
          >
            <X size={22} />
          </button>
        </div>

        {confirming ? (
          <div className="mt-5 flex flex-col gap-4">
            <p className="text-[15px] text-ink">삭제할까요?</p>
            <div className="flex gap-3">
              <SecondaryButton disabled={busy} onClick={() => setConfirming(false)}>
                취소
              </SecondaryButton>
              <button
                type="button"
                disabled={busy}
                onClick={remove}
                className="min-h-[52px] w-full rounded-2xl bg-danger px-5 text-[16px] font-bold text-white disabled:opacity-50"
              >
                {busy ? '삭제 중...' : '삭제'}
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-5 flex flex-col gap-4">
            <p className="text-[13px] font-semibold text-ink">성적</p>
            <div className="grid grid-cols-4 gap-2">
              {choices.map((g) => {
                const on = g === item.grade
                return (
                  <button
                    key={g ?? 'none'}
                    type="button"
                    disabled={busy}
                    onClick={() => changeGrade(g)}
                    className={`min-h-11 rounded-xl text-[14px] font-semibold disabled:opacity-50 ${
                      on ? 'bg-brand text-white' : 'bg-lav text-[#5b4b93]'
                    }`}
                  >
                    {g ?? '성적 없음'}
                  </button>
                )
              })}
            </div>
            <button
              type="button"
              disabled={busy}
              onClick={() => setConfirming(true)}
              className="min-h-11 text-[15px] font-semibold text-danger disabled:opacity-50"
            >
              이 과목 삭제
            </button>
          </div>
        )}

        {error && <p className="mt-3 text-[13px] font-medium text-danger">{error}</p>}
      </div>
    </div>
  )
}
