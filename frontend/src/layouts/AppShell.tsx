// 실제 앱의 바깥 틀.
//
// AppShell   : 로그인 후 화면용. 위쪽 안전영역 + 화면 내용 + 하단 탭바
// AuthLayout : 로그인·회원가입용. 안전영역만 있고 탭바는 없음
//
// 안전영역(safe area)이란?
//   아이폰의 노치·다이내믹 아일랜드, 하단 홈 막대처럼 "화면은 있지만 가려지는 부분" 이다.
//   env(safe-area-inset-top) 등은 기기가 알려주는 그 높이(일반 PC 브라우저에서는 0)이고,
//   index.html 의 viewport-fit=cover 와 함께 써야 값이 들어온다.
//   시안의 StatusBar / HomeIndicator 는 이 역할을 흉내 낸 것이라 실제 앱에서는 쓰지 않는다.

import { NavLink, Outlet } from 'react-router-dom'
import { Home, GraduationCap, Map, User } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

// ── 하단 탭 목록 ─────────────────────────────────────────────
// 탭을 추가하려면 여기에 한 줄 넣고, App.tsx 에 같은 경로의 Route 를 추가하면 된다.
//   예) { to: '/community', label: '커뮤니티', icon: Users },
// end: true → 정확히 그 주소일 때만 활성 (홈 '/' 은 모든 주소의 앞부분이라 꼭 필요)
type Tab = { to: string; label: string; icon: LucideIcon; end?: boolean }

export const TABS: Tab[] = [
  { to: '/', label: '홈', icon: Home, end: true },
  { to: '/diagnose', label: '진단', icon: GraduationCap },
  { to: '/roadmap', label: '로드맵', icon: Map },
  { to: '/my', label: '마이', icon: User },
]

// 태블릿·PC 에서는 가운데 480px 폭으로 (DESIGN.md "실제 앱으로 전환할 때 지킬 것" 3번)
const FRAME = 'mx-auto flex min-h-dvh w-full max-w-[480px] flex-col bg-bg'

export function AppShell() {
  return (
    <div className={FRAME}>
      <main className="flex-1" style={{ paddingTop: 'env(safe-area-inset-top)' }}>
        <Outlet />
      </main>
      <TabNav />
    </div>
  )
}

export function AuthLayout() {
  return (
    <div
      className={FRAME}
      style={{
        paddingTop: 'env(safe-area-inset-top)',
        paddingBottom: 'env(safe-area-inset-bottom)',
      }}
    >
      <Outlet />
    </div>
  )
}

// 하단 탭바. 모양은 kit.tsx 의 TabBar(시안)와 같고, 진짜로 눌러서 이동할 수 있다.
// sticky bottom-0 : 내용이 길어 스크롤해도 화면 아래에 붙어 있음
function TabNav() {
  return (
    <nav
      className="sticky bottom-0 z-10 border-t border-black/5 bg-white/90 backdrop-blur"
      // 시안의 HomeIndicator(34px) 대신 기기의 실제 하단 안전영역만큼 띄운다. PC 에선 8px
      style={{ paddingBottom: 'max(env(safe-area-inset-bottom), 8px)' }}
    >
      <div className="flex items-stretch justify-around px-2 pt-2">
        {TABS.map((t) => {
          const Icon = t.icon
          return (
            <NavLink
              key={t.to}
              to={t.to}
              end={t.end}
              className="flex min-h-11 flex-1 flex-col items-center justify-center gap-1"
            >
              {/* NavLink 는 현재 주소와 맞으면 isActive=true 를 알려준다 */}
              {({ isActive }) => (
                <>
                  <Icon
                    size={24}
                    strokeWidth={isActive ? 2.4 : 2}
                    className={isActive ? 'text-brand' : 'text-[#9c96b3]'}
                  />
                  <span
                    className={`text-[11px] ${isActive ? 'font-bold text-brand' : 'font-medium text-[#9c96b3]'}`}
                  >
                    {t.label}
                  </span>
                </>
              )}
            </NavLink>
          )
        })}
      </div>
    </nav>
  )
}
