import type { ReactNode } from 'react'
import {
  Bell,
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

export function PrimaryButton({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <button
      className={`min-h-[52px] w-full rounded-2xl bg-brand px-5 text-[16px] font-bold text-white shadow-[0_10px_24px_-8px_rgba(108,77,246,0.6)] transition active:scale-[0.99] ${className}`}
    >
      {children}
    </button>
  )
}

export function SecondaryButton({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <button
      className={`min-h-[52px] w-full rounded-2xl bg-lav px-5 text-[16px] font-bold text-brand transition active:scale-[0.99] ${className}`}
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

export function Input({
  placeholder,
  value,
  trailing,
}: {
  placeholder?: string
  value?: string
  trailing?: ReactNode
}) {
  return (
    <div className="flex min-h-[52px] items-center gap-2 rounded-2xl bg-white px-4 ring-1 ring-black/[0.06]">
      <span
        className={`flex-1 text-[15px] ${value ? 'text-ink' : 'text-[#a8a2bc]'}`}
      >
        {value || placeholder}
      </span>
      {trailing}
    </div>
  )
}

export { Bell }
