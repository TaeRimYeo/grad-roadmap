// 마이페이지. 지금은 내 정보(/me) 표시 + 로그아웃만

import { Card, ScreenTitle, SecondaryButton } from '../components/kit'
import { useAuth } from '../auth/AuthContext'

export default function MyPage() {
  const { user, logout } = useAuth()
  if (!user) return null

  const rows: [string, string | number | null][] = [
    ['이름', user.name],
    ['이메일', user.email],
    ['학번', user.student_no],
    ['입학연도', user.admission_year],
    ['학과', user.department],
    ['학위과정', user.program],
    ['세부전공', user.major],
  ]

  return (
    <div className="flex flex-col gap-6 px-5 pb-6 pt-4">
      <ScreenTitle>마이</ScreenTitle>
      <Card className="flex flex-col divide-y divide-black/5 py-1">
        {rows.map(([label, value]) => (
          <div key={label} className="flex min-h-11 items-center justify-between gap-4 py-2">
            <span className="text-[15px] text-sub">{label}</span>
            <span className="truncate text-[15px] font-medium text-ink">{value ?? '-'}</span>
          </div>
        ))}
      </Card>
      <SecondaryButton onClick={logout}>로그아웃</SecondaryButton>
    </div>
  )
}
