// 보호 라우트 / 손님 전용 라우트.
//
// <RequireAuth>  : 로그인한 사람만 들어갈 수 있는 화면(홈·진단·로드맵·마이)을 감싼다.
//                  로그인 안 했으면 /login 으로 보낸다.
// <GuestOnly>    : 로그인·회원가입 화면을 감싼다.
//                  이미 로그인했으면 홈(/)으로 보낸다.
//
// <Outlet /> 은 "이 라우트 아래에 등록된 자식 화면이 그려질 자리" 다. (App.tsx 참고)

import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './AuthContext'

// 토큰 확인 중일 때 잠깐 보이는 화면. 이걸 안 두면 새로고침할 때마다 로그인 화면이 번쩍인다.
function Splash() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-bg">
      <span className="text-[15px] text-sub">불러오는 중...</span>
    </div>
  )
}

export function RequireAuth() {
  const { user, loading } = useAuth()
  if (loading) return <Splash />
  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}

export function GuestOnly() {
  const { user, loading } = useAuth()
  if (loading) return <Splash />
  if (user) return <Navigate to="/" replace />
  return <Outlet />
}
