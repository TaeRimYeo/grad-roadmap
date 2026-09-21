import type { ReactNode } from 'react'
import {
  ArrowLeft,
  Eye,
  EyeOff,
  Check,
  ChevronDown,
  ChevronRight,
  Clock,
  MapPin,
  AlertTriangle,
  GraduationCap,
} from 'lucide-react'
import {
  Bell,
  Card,
  Chip,
  Field,
  Input,
  PrimaryButton,
  Progress,
  ScreenTitle,
  SecondaryButton,
  SectionTitle,
  StatusPill,
  TabBar,
  TypeBadge,
  HomeIndicator,
} from '../components/kit'

const PX = 'px-5' // 좌우 여백 20

/* 1 ── 로그인 ──────────────────────────────────────────────── */
export function Login() {
  return (
    <div className={`flex min-h-full flex-col ${PX} pb-8`}>
      <div className="flex flex-1 flex-col items-center justify-center gap-8">
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-20 w-20 items-center justify-center rounded-[26px] bg-brand shadow-[0_16px_32px_-10px_rgba(108,77,246,0.7)]">
            <Map />
          </div>
          <div className="text-center">
            <h1 className="text-[28px] font-bold tracking-tight text-ink">학기 로드맵</h1>
            <p className="mt-1.5 text-[15px] text-sub">졸업까지의 길을 자동으로 설계해요</p>
          </div>
        </div>

        <div className="flex w-full flex-col gap-3">
          <Input placeholder="학교 이메일" />
          <Input placeholder="비밀번호" trailing={<EyeOff size={20} className="text-[#a8a2bc]" />} />
          <PrimaryButton className="mt-2">로그인</PrimaryButton>
        </div>
      </div>

      <div className="flex items-center justify-center gap-4 text-[14px] font-medium text-sub">
        <span>비밀번호 찾기</span>
        <span className="h-3 w-px bg-black/10" />
        <span className="font-semibold text-brand">회원가입</span>
      </div>
    </div>
  )
}

// tiny map glyph for the logo
function Map() {
  return (
    <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 6 3 4v14l6 2 6-2 6 2V6l-6-2-6 2Z" />
      <path d="M9 4v16M15 6v16" />
    </svg>
  )
}

/* Signup shared ──────────────────────────────────────────────── */
function SignupHeader({ step }: { step: 1 | 2 }) {
  return (
    <div className="flex items-center gap-3 pb-2 pt-1">
      <ArrowLeft size={24} className="text-ink" />
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

/* 2 ── 회원가입 1단계 ─────────────────────────────────────── */
export function SignupAccount() {
  return (
    <div className={`flex min-h-full flex-col ${PX} pb-6`}>
      <SignupHeader step={1} />
      <div className="mt-3">
        <ScreenTitle>계정 정보를 입력해요</ScreenTitle>
      </div>
      <div className="mt-6 flex flex-1 flex-col gap-4">
        <Field label="이름">
          <Input placeholder="이름 입력" />
        </Field>
        <Field label="학교 이메일">
          <Input
            placeholder="name@school.ac.kr"
            trailing={<span className="rounded-lg bg-lav px-3 py-1.5 text-[12px] font-bold text-brand">인증</span>}
          />
        </Field>
        <Field label="비밀번호">
          <Input placeholder="비밀번호 입력" trailing={<Eye size={20} className="text-[#a8a2bc]" />} />
        </Field>
        <Field label="비밀번호 확인">
          <Input placeholder="비밀번호 재입력" trailing={<Eye size={20} className="text-[#a8a2bc]" />} />
        </Field>
        <p className="text-[12px] font-medium text-sub">
          영문·숫자·특수문자를 포함해 8자 이상으로 설정해 주세요.
        </p>
      </div>
      <PrimaryButton>다음</PrimaryButton>
    </div>
  )
}

/* Segmented control */
function Segment({ options, active }: { options: string[]; active: number }) {
  return (
    <div className="flex gap-1 rounded-2xl bg-lav p-1">
      {options.map((o, i) => (
        <div
          key={o}
          className={`flex min-h-11 flex-1 items-center justify-center rounded-xl text-[14px] font-semibold ${
            i === active ? 'bg-white text-brand shadow-sm' : 'text-[#7d76a0]'
          }`}
        >
          {o}
        </div>
      ))}
    </div>
  )
}

function Dropdown({ value }: { value: string }) {
  return (
    <div className="flex min-h-[52px] items-center justify-between rounded-2xl bg-white px-4 ring-1 ring-black/[0.06]">
      <span className="text-[15px] font-medium text-ink">{value}</span>
      <ChevronDown size={20} className="text-[#a8a2bc]" />
    </div>
  )
}

/* 3 ── 회원가입 2단계 ─────────────────────────────────────── */
export function SignupSchool() {
  return (
    <div className={`flex min-h-full flex-col ${PX} pb-6`}>
      <SignupHeader step={2} />
      <div className="mt-3">
        <ScreenTitle>학적 정보를 알려주세요</ScreenTitle>
      </div>
      <div className="mt-6 flex flex-1 flex-col gap-4">
        <Field label="학교">
          <Dropdown value="경기과학기술대학교" />
        </Field>
        <Field label="학과">
          <Dropdown value="컴퓨터모바일융합과" />
        </Field>
        <Field label="학위과정">
          <Segment options={['전문학사', '전공심화']} active={0} />
        </Field>
        <Field label="세부전공">
          <Segment options={['SW융합전공', '게임개발전공']} active={0} />
        </Field>
        <div className="flex gap-3">
          <div className="flex-1">
            <Field label="입학연도">
              <Dropdown value="2025" />
            </Field>
          </div>
          <div className="flex-1">
            <Field label="학번">
              <Input placeholder="학번 입력" />
            </Field>
          </div>
        </div>
        <p className="text-[12px] font-medium text-sub">
          타 전공 과목도 잔여석이 있으면 수강할 수 있어요.
        </p>
      </div>
      <PrimaryButton>가입 완료</PrimaryButton>
    </div>
  )
}

/* 4 ── 홈 ─────────────────────────────────────────────────── */
function ClassCard({
  time,
  name,
  prof,
  room,
  status,
}: {
  time: string
  name: string
  prof: string
  room: string
  status: 'now' | 'soon'
}) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-1.5 text-[13px] font-bold text-brand">
          <Clock size={15} strokeWidth={2.4} />
          {time}
        </div>
        {status === 'now' ? (
          <StatusPill tone="ok">진행 중</StatusPill>
        ) : (
          <StatusPill tone="muted">예정</StatusPill>
        )}
      </div>
      <h3 className="mt-2 text-[17px] font-bold text-ink">{name}</h3>
      <div className="mt-1 flex items-center gap-2 text-[13px] text-sub">
        <span>{prof} 교수</span>
        <span className="h-3 w-px bg-black/10" />
        <span className="inline-flex items-center gap-1">
          <MapPin size={13} /> {room}
        </span>
      </div>
      <div className="mt-3">
        <TypeBadge type="전공선택" />
      </div>
    </Card>
  )
}

function AssignmentRow({
  course,
  task,
  dday,
  warn = false,
}: {
  course: string
  task: string
  dday: string
  warn?: boolean
}) {
  return (
    <div className="flex items-center gap-3 py-3">
      <div className="min-w-0 flex-1">
        <p className="truncate text-[15px] font-semibold text-ink">{task}</p>
        <p className="mt-0.5 text-[12px] text-sub">{course}</p>
      </div>
      <StatusPill tone={warn ? 'warn' : 'brand'}>{dday}</StatusPill>
    </div>
  )
}

export function HomeScreen() {
  return (
    <div className="flex min-h-full flex-col">
      <div className={`flex flex-col gap-5 ${PX} pb-6 pt-2`}>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-[22px] font-bold tracking-tight text-ink">김경기님, 오늘도 화이팅</h1>
            <p className="mt-1 text-[14px] font-medium text-sub">9월 23일 수요일</p>
          </div>
          <div className="relative">
            <Bell size={24} className="text-ink" />
            <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-danger ring-2 ring-bg" />
          </div>
        </div>

        <section className="flex flex-col gap-3">
          <SectionTitle>오늘 수업</SectionTitle>
          <ClassCard time="10:30–13:20" name="IoT네트워크실습" prof="전선도" room="C320" status="now" />
          <ClassCard time="14:30–17:20" name="안드로이드프로그래밍" prof="윤창표" room="C405" status="soon" />
        </section>

        <section className="flex flex-col gap-1">
          <SectionTitle>다가오는 과제</SectionTitle>
          <Card className="divide-y divide-black/5 py-1">
            <AssignmentRow course="안드로이드프로그래밍" task="액티비티 생명주기 실습 보고서" dday="D-2" warn />
            <AssignmentRow course="IoT네트워크실습" task="센서 데이터 수집 과제" dday="D-5" />
            <AssignmentRow course="데이터베이스프로그래밍" task="조별 ERD 설계" dday="D-9" />
          </Card>
        </section>

        <Card className="bg-lav ring-0">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[13px] font-semibold text-[#5b4b93]">졸업까지</p>
              <p className="mt-1 text-[20px] font-bold text-ink">
                55 <span className="text-[15px] font-semibold text-sub">/ 110학점</span>
              </p>
            </div>
            <div className="flex items-center gap-1 text-[13px] font-bold text-brand">
              로드맵 보기 <ChevronRight size={16} />
            </div>
          </div>
          <div className="mt-3">
            <Progress value={55} max={110} />
          </div>
        </Card>
      </div>
      <TabBar active="home" />
    </div>
  )
}

/* 5 ── 학점관리 ───────────────────────────────────────────── */
function SummaryRow({ label, value, max, tone }: { label: string; value: number; max: number; tone?: 'brand' | 'ok' }) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-[14px] font-semibold text-ink">{label}</span>
        <span className="text-[13px] font-bold text-sub">
          <span className="text-ink">{value}</span> / {max}학점
        </span>
      </div>
      <div className="mt-2">
        <Progress value={value} max={max} tone={tone} />
      </div>
    </div>
  )
}

function GradeRow({ name, grade, type }: { name: string; grade: string; type: '전공필수' | '전공선택' | '교양필수' | '교양선택' }) {
  return (
    <div className="flex items-center gap-3 py-2.5">
      <TypeBadge type={type} short />
      <span className="min-w-0 flex-1 truncate text-[15px] font-medium text-ink">{name}</span>
      <span className="text-[12px] text-sub">3학점</span>
      <span className="w-9 text-right text-[15px] font-bold text-brand">{grade}</span>
    </div>
  )
}

export function CreditScreen() {
  const gpaBars = [
    { s: '1-1', v: 3.9 },
    { s: '1-2', v: 3.7 },
    { s: '2-1', v: 3.85 },
  ]
  return (
    <div className="flex min-h-full flex-col">
      <div className={`flex flex-col gap-5 ${PX} pb-6 pt-2`}>
        <ScreenTitle>학점관리</ScreenTitle>

        <Card className="flex flex-col gap-4">
          <SummaryRow label="총 이수" value={55} max={110} />
          <SummaryRow label="전공" value={40} max={64} />
          <SummaryRow label="전공필수" value={0} max={9} />
        </Card>

        <Card>
          <div className="flex items-baseline justify-between">
            <span className="text-[14px] font-semibold text-ink">전체 평점</span>
            <span className="text-[20px] font-bold text-brand">
              3.82 <span className="text-[13px] font-semibold text-sub">/ 4.5</span>
            </span>
          </div>
          <div className="mt-4 flex items-end justify-around gap-3" style={{ height: 96 }}>
            {gpaBars.map((b) => (
              <div key={b.s} className="flex flex-1 flex-col items-center gap-1.5">
                <span className="text-[12px] font-bold text-ink">{b.v.toFixed(2)}</span>
                <div className="w-full overflow-hidden rounded-t-lg bg-lav" style={{ height: '100%' }}>
                  <div className="w-full rounded-t-lg bg-brand" style={{ height: `${(b.v / 4.5) * 100}%`, marginTop: `${100 - (b.v / 4.5) * 100}%` }} />
                </div>
                <span className="text-[12px] font-medium text-sub">{b.s}</span>
              </div>
            ))}
          </div>
        </Card>

        <section className="flex flex-col gap-2">
          <SectionTitle>지난 학기 성적</SectionTitle>
          <p className="-mt-1 text-[12px] font-medium text-sub">2학년 1학기</p>
          <Card className="divide-y divide-black/5 py-1">
            <GradeRow name="데이터베이스" grade="A+" type="전공선택" />
            <GradeRow name="C#프로그래밍" grade="A0" type="전공선택" />
            <GradeRow name="컴퓨터네트워크" grade="B+" type="전공필수" />
            <GradeRow name="자료구조실습" grade="A0" type="전공선택" />
            <GradeRow name="웹서버프로그래밍" grade="B+" type="전공선택" />
            <GradeRow name="임베디드프로그래밍" grade="A0" type="전공선택" />
          </Card>
        </section>

        <section className="flex flex-col gap-2">
          <SectionTitle>앞으로 들어야 할 과목</SectionTitle>
          <Card className="flex flex-col gap-2.5">
            <p className="text-[12px] font-bold text-sub">전공필수</p>
            {[
              ['정보처리특론', '3학년 1학기 개설'],
              ['캡스톤디자인1', '3학년 1학기 개설'],
              ['캡스톤디자인2', '3학년 2학기 · 선수: 캡스톤디자인1'],
            ].map(([n, d]) => (
              <div key={n} className="flex items-center gap-2.5">
                <TypeBadge type="전공필수" short />
                <span className="flex-1 text-[15px] font-semibold text-ink">{n}</span>
                <span className="text-[11px] text-sub">{d}</span>
              </div>
            ))}
          </Card>
          <div className="rounded-2xl bg-[#fef3e0] p-4 ring-1 ring-[#f5a524]/25">
            <div className="flex items-center gap-2 text-[14px] font-bold text-[#c07a10]">
              <AlertTriangle size={16} /> 선수과목 주의
            </div>
            <p className="mt-1.5 text-[13px] font-medium text-[#8a6410]">
              파이썬프로그래밍응용 — 파이썬프로그래밍기초를 먼저 이수해야 해요
            </p>
          </div>
          <div className="rounded-2xl border-2 border-dashed border-[#b8aef0] bg-white/60 p-4">
            <div className="flex items-center gap-2">
              <TypeBadge type="교양선택" />
              <span className="text-[15px] font-bold text-ink">교양 자리 12학점</span>
            </div>
            <p className="mt-1 text-[12px] font-medium text-sub">과목 자유 선택</p>
          </div>
        </section>

        <PrimaryButton>로드맵 추천받기</PrimaryButton>
      </div>
      <TabBar active="credit" />
    </div>
  )
}

/* 6 ── 로드맵 추천 결과 ───────────────────────────────────── */
export function CourseTile({
  name,
  type,
  credit,
  dashed = false,
}: {
  name: string
  type: '전공필수' | '전공선택' | '교양필수' | '교양선택'
  credit: number
  dashed?: boolean
}) {
  return (
    <div
      className={`flex flex-col gap-1.5 rounded-xl p-2.5 ${
        dashed ? 'border-2 border-dashed border-[#b8aef0] bg-white/50' : 'bg-lav/60'
      }`}
    >
      <span className="text-[13px] font-bold leading-tight text-ink">{name}</span>
      <div className="flex items-center gap-1.5">
        <TypeBadge type={type} short />
        <span className="text-[11px] font-semibold text-sub">{credit}학점</span>
      </div>
      {dashed && <span className="text-[10px] font-medium text-[#8b7fc9]">과목 자유 선택</span>}
    </div>
  )
}

function SemesterCard({
  title,
  credits,
  last,
  children,
}: {
  title: string
  credits: number
  last?: boolean
  children: ReactNode
}) {
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-[16px] font-bold text-ink">{title}</h3>
          {last && <StatusPill tone="brand">마지막 학기</StatusPill>}
        </div>
        <span className="text-[13px] font-bold text-brand">{credits}학점</span>
      </div>
      <div className="grid grid-cols-2 gap-2">{children}</div>
    </Card>
  )
}

export function RoadmapResult() {
  return (
    <div className={`flex min-h-full flex-col ${PX} pb-6`}>
      <div className="flex items-center gap-3 pt-1">
        <ArrowLeft size={24} className="text-ink" />
        <ScreenTitle>추천 로드맵</ScreenTitle>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Chip active>남은 2학기</Chip>
        <Chip>학기당 최대 22학점</Chip>
        <Chip>계절학기 사용 안 함</Chip>
        <span className="ml-auto inline-flex items-center rounded-full bg-white px-3 py-2 text-[13px] font-bold text-brand ring-1 ring-brand/20">
          수정
        </span>
      </div>

      <div className="mt-4 flex items-center gap-3 rounded-2xl bg-brand p-4 text-white shadow-[0_12px_28px_-10px_rgba(108,77,246,0.7)]">
        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white/20">
          <GraduationCap size={24} />
        </div>
        <div>
          <p className="text-[15px] font-bold">3학년 2학기에 졸업할 수 있어요</p>
          <p className="text-[13px] text-white/85">총 110학점 충족</p>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-3">
        <SemesterCard title="3학년 1학기" credits={18}>
          <CourseTile name="정보처리특론" type="전공필수" credit={3} />
          <CourseTile name="캡스톤디자인1" type="전공필수" credit={3} />
          <CourseTile name="인공지능기초" type="전공선택" credit={3} />
          <CourseTile name="웹서버설계" type="전공선택" credit={3} />
          <CourseTile name="앱프로그래밍" type="전공선택" credit={3} />
          <CourseTile name="교양선택 A" type="교양선택" credit={3} dashed />
        </SemesterCard>

        <SemesterCard title="3학년 2학기" credits={20} last>
          <CourseTile name="캡스톤디자인2" type="전공필수" credit={3} />
          <CourseTile name="인공지능설계" type="전공선택" credit={3} />
          <CourseTile name="빅데이터" type="전공선택" credit={3} />
          <CourseTile name="모바일네트워크시스템" type="전공선택" credit={3} />
          <CourseTile name="클라우드네트워킹설계" type="전공선택" credit={3} />
          <CourseTile name="교양선택 B" type="교양선택" credit={3} dashed />
          <CourseTile name="교양선택 C" type="교양선택" credit={2} dashed />
        </SemesterCard>
      </div>

      <div className="mt-4 flex items-start gap-2.5 rounded-2xl bg-[#fdecec] p-4 ring-1 ring-danger/20">
        <AlertTriangle size={18} className="mt-0.5 shrink-0 text-danger" />
        <p className="text-[13px] font-semibold text-[#a52a2e]">
          캡스톤디자인1을 3학년 1학기에 듣지 않으면 졸업이 1학기 늦어져요
        </p>
      </div>

      <div className="mt-5 flex gap-3">
        <SecondaryButton>조건 바꾸기</SecondaryButton>
        <PrimaryButton>이 로드맵 저장</PrimaryButton>
      </div>
      <div className="mt-auto" />
      <HomeIndicator />
    </div>
  )
}
