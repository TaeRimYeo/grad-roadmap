// 로드맵 화면 (빈 화면). 솔버 API 가 생기면 연결한다.

import { Card, ScreenTitle } from '../components/kit'

export default function RoadmapPage() {
  return (
    <div className="flex flex-col gap-6 px-5 pb-6 pt-4">
      <ScreenTitle>로드맵</ScreenTitle>
      <Card>
        <p className="text-[15px] text-sub">준비 중인 화면이에요.</p>
      </Card>
    </div>
  )
}
