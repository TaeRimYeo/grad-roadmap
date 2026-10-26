import type { ButtonHTMLAttributes, ReactNode } from 'react'
import {
  Bell,
  ChevronDown,
  Home,
  GraduationCap,
  Map,
  Users,
  User,
  Signal,
  Wifi,
  BatteryFull,
} from 'lucide-react'

/* ── Phone frame ─────────────────────────────────────────────── */
// iPhone 16 Pro: 402 × 874, top safe area 59, bottom home indicator 34.

export function Phone({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className="relative flex flex-col overflow-hidden bg-bg shadow-[0_24px_60px_-20px_rgba(31,21,53,0.35)] ring-1 ring-black/5"
        style={{ width: 402, height: 874, borderRadius: 44 }}
      >
        <StatusBar />
        <div className="screen-scroll flex-1 overflow-y-auto">{children}</div>
      </div>
      <span className="text-[13px] font-semibold text-[#8b84a8]">{label}</span>
    </div>
  )
}

function StatusBar() {
  return (
    <div
      className="relative z-20 flex shrink-0 items-end justify-between px-8 pb-2"
      style={{ height: 59 }}
    >
      <span className="text-[15px] font-semibold tracking-tight text-ink">9:41</span>
      {/* Dynamic Island */}
      <div className="absolute left-1/2 top-2.5 h-8 w-[126px] -translate-x-1/2 rounded-full bg-ink" />
      <div className="flex items-center gap-1.5 text-ink">
        <Signal size={17} strokeWidth={2.4} />
        <Wifi size={17} strokeWidth={2.4} />
        <BatteryFull size={22} strokeWidth={2} />
      </div>
    </div>
  )
}

export function HomeIndicator() {
  return (
    <div className="flex justify-center pb-2 pt-1.5" style={{ height: 34 }}>
      <div className="h-[5px] w-[140px] rounded-full bg-ink/85" />
    </div>
  )
}

/* ── Bottom tab bar ──────────────────────────────────────────── */

const TABS = [
  { id: 'home', label: '홈', icon: Home },
  { id: 'credit', label: '학점', icon: GraduationCap },
  { id: 'roadmap', label: '로드맵', icon: Map },
  { id: 'community', label: '커뮤니티', icon: Users },
  { id: 'my', label: '마이', icon: User },
] as const

export function TabBar({ active }: { active: (typeof TABS)[number]['id'] }) {
  return (
    <div className="mt-auto border-t border-black/5 bg-white/90 backdrop-blur">
      <div className="flex items-stretch justify-around px-2 pt-2">
        {TABS.map((t) => {
          const on = t.id === active
          const Icon = t.icon
          return (
            <div
              key={t.id}
              className="flex min-h-11 flex-1 flex-col items-center justify-center gap-1"
            >
              <Icon
                size={24}
                strokeWidth={on ? 2.4 : 2}
                className={on ? 'text-brand' : 'text-[#9c96b3]'}
              />
              <span
                className={`text-[11px] ${on ? 'font-bold text-brand' : 'font-medium text-[#9c96b3]'}`}
              >
                {t.label}
              </span>
            </div>
          )
        })}
      </div>
      <HomeIndicator />
    </div>
  )
}

/* ── Typography helpers ──────────────────────────────────────── */

export function ScreenTitle({ children }: { children: ReactNode }) {
  return <h1 className="text-[22px] font-bold tracking-tight text-ink">{children}</h1>
}

export function SectionTitle({
  children,
  action,
}: {
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="flex items-center justify-between">
      <h2 className="text-[17px] font-semibold tracking-tight text-ink">{children}</h2>
      {action}
    </div>
  )
}

/* ── Cards ───────────────────────────────────────────────────── */

export function Card({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`rounded-2xl bg-white p-4 ring-1 ring-black/[0.04] ${className}`}>
      {children}
    </div>
  )
}

/* ── Chips ───────────────────────────────────────────────────── */

export function Chip({
  children,
  active = false,
}: {
  children: ReactNode
  active?: boolean
}) {
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-full px-3.5 py-2 text-[13px] font-semibold ${
        active ? 'bg-brand text-white' : 'bg-lav text-[#5b4b93]'
      }`}
    >
      {children}
    </span>
  )
}

/* ── Course-type badge (이수구분 4종) ────────────────────────── */

type CourseType = '전공필수' | '전공선택' | '교양필수' | '교양선택'

const COURSE_STYLE: Record<CourseType, string> = {
  전공필수: 'bg-[#ece8ff] text-[#5836e6]',
  전공선택: 'bg-[#e0f0ff] text-[#2563c9]',
  교양필수: 'bg-[#fff0e0] text-[#c26a12]',
  교양선택: 'bg-[#e8f7ee] text-[#1f8a5b]',
}

export function TypeBadge({
  type,
  short = false,
}: {
  type: CourseType
  short?: boolean
}) {
  const label = short
    ? { 전공필수: '전필', 전공선택: '전선', 교양필수: '교필', 교양선택: '교선' }[type]
    : type
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-bold ${COURSE_STYLE[type]}`}
    >
      {label}
    </span>
  )
}

/* ── Status pill ─────────────────────────────────────────────── */

export function StatusPill({
  tone,
  children,
}: {
  tone: 'ok' | 'warn' | 'danger' | 'brand' | 'muted'
  children: ReactNode
}) {
  const map = {
    ok: 'bg-[#e8f7ee] text-ok',
    warn: 'bg-[#fef3e0] text-[#c07a10]',
    danger: 'bg-[#fdecec] text-danger',
    brand: 'bg-lav text-brand',
    muted: 'bg-black/5 text-sub',
  }
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold ${map[tone]}`}
    >
      {children}
    </span>
  )
}

/* ── Progress bar ────────────────────────────────────────────── */

export function Progress({
  value,
  max,
  tone = 'brand',
}: {
  value: number
  max: number
  tone?: 'brand' | 'ok'
}) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div className="h-2.5 w-full overflow-hidden rounded-full bg-lav">
      <div
        className={`h-full rounded-full ${tone === 'ok' ? 'bg-ok' : 'bg-brand'}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

/* ── Buttons ─────────────────────────────────────────────────── */

// 버튼은 <button> 의 기본 속성(type, onClick, disabled 등)을 그대로 넘겨받는다.
// type 을 안 주면 "button" 으로 둬서, form 안에서 의도치 않게 제출되는 일을 막는다.
// disabled 일 때는 흐리게 + 눌림 효과 없음.
type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { children: ReactNode }

export function PrimaryButton({
  children,
  className = '',
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      {...rest}
      className={`min-h-[52px] w-full rounded-2xl bg-brand px-5 text-[16px] font-bold text-white shadow-[0_10px_24px_-8px_rgba(108,77,246,0.6)] transition active:scale-[0.99] disabled:opacity-50 disabled:active:scale-100 ${className}`}
    >
      {children}
    </button>
  )
}

export function SecondaryButton({
  children,
  className = '',
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      {...rest}
      className={`min-h-[52px] w-full rounded-2xl bg-lav px-5 text-[16px] font-bold text-brand transition active:scale-[0.99] disabled:opacity-50 disabled:active:scale-100 ${className}`}
    >
      {children}
    </button>
  )
}

/* ── Field ───────────────────────────────────────────────────── */

export function Field({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className="text-[13px] font-semibold text-ink">{label}</span>
      {children}
    </label>
  )
}

// Input 은 두 가지 모드로 동작한다.
//   1) onChange 가 없으면 → 시안용. 글자만 보여주는 <span> (기존 시안 화면이 이 모드)
//   2) onChange 가 있으면 → 실제 <input>. 모양(클래스)은 시안과 똑같다
export function Input({
  placeholder,
  value,
  trailing,
  onChange,
  type = 'text',
  inputMode,
  autoComplete,
  maxLength,
}: {
  placeholder?: string
  value?: string
  trailing?: ReactNode
  onChange?: (value: string) => void
  type?: 'text' | 'email' | 'password'
  inputMode?: 'text' | 'email' | 'numeric'
  autoComplete?: string
  maxLength?: number
}) {
  return (
    <div className="flex min-h-[52px] items-center gap-2 rounded-2xl bg-white px-4 ring-1 ring-black/[0.06] focus-within:ring-brand">
      {onChange ? (
        <input
          type={type}
          value={value ?? ''}
          placeholder={placeholder}
          inputMode={inputMode}
          autoComplete={autoComplete}
          maxLength={maxLength}
          onChange={(e) => onChange(e.target.value)}
          // min-w-0 : 칸이 좁아도 trailing 아이콘을 밀어내지 않게
          className="min-w-0 flex-1 bg-transparent text-[15px] text-ink outline-none placeholder:text-[#a8a2bc]"
        />
      ) : (
        <span
          className={`flex-1 text-[15px] ${value ? 'text-ink' : 'text-[#a8a2bc]'}`}
        >
          {value || placeholder}
        </span>
      )}
      {trailing}
    </div>
  )
}

/* ── 선택 입력 (Select · Segment · Choice) ──────────────────── */
// 선택지 하나의 모양. value 는 서버로 보낼 값(보통 id), label 은 화면 글자.
export type Option = { value: number; label: string }

// 드롭다운. 시안의 Dropdown 과 같은 모양이고 실제로는 브라우저 기본 <select>.
// 기본 <select> 를 쓰면 휴대폰에서 OS 의 선택 휠/목록이 떠서 터치하기 편하다.
export function Select({
  options,
  value,
  onChange,
  placeholder = '선택해 주세요',
  disabled = false,
}: {
  options: Option[]
  value: number | null
  onChange: (value: number) => void
  placeholder?: string
  disabled?: boolean
}) {
  return (
    <div className="relative flex min-h-[52px] items-center rounded-2xl bg-white ring-1 ring-black/[0.06] focus-within:ring-brand">
      <select
        value={value ?? ''}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        // appearance-none : 브라우저 기본 화살표를 숨기고 아래 ChevronDown 을 대신 보여준다
        className={`min-h-[52px] w-full appearance-none bg-transparent pl-4 pr-10 text-[15px] font-medium outline-none disabled:opacity-50 ${
          value === null ? 'text-[#a8a2bc]' : 'text-ink'
        }`}
      >
        <option value="" disabled>
          {placeholder}
        </option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown size={20} className="pointer-events-none absolute right-4 text-[#a8a2bc]" />
    </div>
  )
}

// 세그먼트 버튼. 시안 3번(회원가입 2단계)의 학위과정·세부전공 버튼과 같은 모양.
export function Segment({
  options,
  value,
  onChange,
}: {
  options: Option[]
  value: number | null
  onChange: (value: number) => void
}) {
  return (
    <div className="flex gap-1 rounded-2xl bg-lav p-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={`flex min-h-11 flex-1 items-center justify-center rounded-xl text-[14px] font-semibold ${
            o.value === value ? 'bg-white text-brand shadow-sm' : 'text-[#7d76a0]'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

// 선택지 개수에 따라 자동으로 고른다.
//   3개 이하 → Segment (한눈에 보이고 한 번에 누를 수 있음)
//   4개 이상 → Select  (375px 폭에 버튼이 너무 좁아지므로)
export function Choice(props: {
  options: Option[]
  value: number | null
  onChange: (value: number) => void
  placeholder?: string
}) {
  // 선택지가 아직 없으면(상위 항목 미선택) 비활성 드롭다운으로 자리만 잡아 둔다
  if (props.options.length === 0) {
    return <Select {...props} disabled />
  }
  return props.options.length <= 3 ? <Segment {...props} /> : <Select {...props} />
}

export { Bell }
