// 홈 화면. 지금은 인사 + 소속 표시 + 로그아웃만 (시안 4번의 나머지는 진단·로드맵 API 연결 후)

import { Chip, ScreenTitle, SecondaryButton } from '../components/kit'
import { useAuth } from '../auth/AuthContext'

export default function HomePage() {
  const { user, logout } = useAuth()
  // RequireAuth 안에서만 그려지므로 user 는 항상 있지만, 타입상 null 일 수 있어 한 번 막아 둔다
  if (!user) return null

  // 관리자 계정처럼 소속이 비어 있으면 그 칸은 건너뛴다
  const tags = [user.department, user.program, user.major].filter((t): t is string => !!t)

  return (
    <div className="flex flex-col gap-6 px-5 pb-6 pt-4">
      <div className="flex flex-col gap-3">
        <ScreenTitle>{user.name}님, 안녕하세요</ScreenTitle>
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {tags.map((t) => (
              <Chip key={t}>{t}</Chip>
            ))}
          </div>
        )}
      </div>
      {/* 로그아웃하면 user 가 null 이 되어 RequireAuth 가 자동으로 /login 으로 보낸다 */}
      <SecondaryButton onClick={logout}>로그아웃</SecondaryButton>
    </div>
  )
}
