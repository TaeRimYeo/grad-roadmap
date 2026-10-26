// 디자인 시안 모음 (/design). 원래 App.tsx 에 있던 쇼케이스를 그대로 옮겼다.
// 실제 앱 화면을 만들 때 참고용으로 계속 유지한다. 로그인 없이 볼 수 있다.

import { Phone } from '../components/kit'
import {
  Login,
  SignupAccount,
  SignupSchool,
  HomeScreen,
  CreditScreen,
  RoadmapResult,
} from '../screens/Frames1to6'
import {
  RoadmapImpossible,
  RoadmapTab,
  CommunityMarket,
  CommunitySeniors,
  CommunityFood,
  MyPage,
} from '../screens/Frames7to12'

const FRAMES = [
  { n: 1, label: '1 · 로그인', el: <Login /> },
  { n: 2, label: '2 · 회원가입 1단계', el: <SignupAccount /> },
  { n: 3, label: '3 · 회원가입 2단계', el: <SignupSchool /> },
  { n: 4, label: '4 · 홈', el: <HomeScreen /> },
  { n: 5, label: '5 · 학점관리', el: <CreditScreen /> },
  { n: 6, label: '6 · 로드맵 추천 결과', el: <RoadmapResult /> },
  { n: 7, label: '7 · 로드맵 — 졸업 불가', el: <RoadmapImpossible /> },
  { n: 8, label: '8 · 로드맵 탭', el: <RoadmapTab /> },
  { n: 9, label: '9 · 커뮤니티 — 중고거래', el: <CommunityMarket /> },
  { n: 10, label: '10 · 커뮤니티 — 선배', el: <CommunitySeniors /> },
  { n: 11, label: '11 · 커뮤니티 — 맛집', el: <CommunityFood /> },
  { n: 12, label: '12 · 마이페이지', el: <MyPage /> },
]

export default function DesignPage() {
  return (
    <div className="min-h-screen bg-[#efeafd] px-8 py-12">
      <header className="mx-auto mb-10 max-w-[1400px]">
        <p className="text-[13px] font-bold uppercase tracking-widest text-brand">Semester Roadmap · UI Kit</p>
        <h1 className="mt-2 text-[34px] font-bold tracking-tight text-ink">학기 로드맵 — 모바일 앱 시안</h1>
        <p className="mt-2 text-[15px] font-medium text-sub">
          iPhone 16 Pro · 12 프레임 · 라벤더 퍼플 · Pretendard
        </p>
      </header>

      <main className="mx-auto grid max-w-[1400px] grid-cols-1 justify-items-center gap-x-8 gap-y-14 md:grid-cols-2 xl:grid-cols-3">
        {FRAMES.map((f) => (
          <Phone key={f.n} label={f.label}>
            {f.el}
          </Phone>
        ))}
      </main>
    </div>
  )
}
