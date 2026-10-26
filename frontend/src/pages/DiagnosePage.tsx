// 졸업 진단 화면 (빈 화면). 다음 단계에서 POST /api/diagnose 를 연결한다.

import { Card, ScreenTitle } from '../components/kit'

export default function DiagnosePage() {
  return (
    <div className="flex flex-col gap-6 px-5 pb-6 pt-4">
      <ScreenTitle>졸업 진단</ScreenTitle>
      <Card>
        <p className="text-[15px] text-sub">준비 중인 화면이에요.</p>
      </Card>
    </div>
  )
}
