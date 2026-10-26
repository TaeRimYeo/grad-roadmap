// 주소(URL) → 화면 연결표.
//
//   /design                  디자인 시안 모음 (누구나)
//   /login, /signup          로그인·회원가입 (로그인 안 한 사람만, 탭바 없음)
//   /, /diagnose, /roadmap, /grades, /grades/add, /my   로그인한 사람만, 하단 탭바 있음
//
// 중첩 Route 읽는 법: 바깥 Route 의 element(예: <RequireAuth/>)가 먼저 그려지고,
// 그 안의 <Outlet/> 자리에 안쪽 Route 의 화면이 들어간다.
//   RequireAuth(로그인 확인) → AppShell(탭바 틀) → HomePage

import { Navigate, Route, Routes } from 'react-router-dom'
import { GuestOnly, RequireAuth } from './auth/RequireAuth'
import { AppShell, AuthLayout } from './layouts/AppShell'
import DesignPage from './pages/DesignPage'
import DiagnosePage from './pages/DiagnosePage'
import GradesAddPage from './pages/GradesAddPage'
import GradesPage from './pages/GradesPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import MyPage from './pages/MyPage'
import RoadmapPage from './pages/RoadmapPage'
import SignupPage from './pages/SignupPage'

export default function App() {
  return (
    <Routes>
      <Route path="/design" element={<DesignPage />} />

      <Route element={<GuestOnly />}>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
        </Route>
      </Route>

      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          {/* 탭을 추가할 때는 layouts/AppShell.tsx 의 TABS 와 여기에 한 줄씩 */}
          <Route path="/" element={<HomePage />} />
          <Route path="/diagnose" element={<DiagnosePage />} />
          <Route path="/roadmap" element={<RoadmapPage />} />
          <Route path="/grades" element={<GradesPage />} />
          <Route path="/grades/add" element={<GradesAddPage />} />
          <Route path="/my" element={<MyPage />} />
        </Route>
      </Route>

      {/* 없는 주소는 홈으로 (로그인 안 했으면 다시 /login 으로) */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
