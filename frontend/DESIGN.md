# 디자인 시스템 — 시안 4 · 라벤더 퍼플 (확정)

> 모든 화면은 이 문서의 토큰과 컴포넌트만 사용한다. 새 색상·새 폰트 크기를 임의로 추가하지 않는다.

## 색상 토큰 (`src/index.css` 의 `@theme`)

| 토큰 | 값 | 용도 | Tailwind 클래스 |
|---|---|---|---|
| `bg` | `#F7F5FF` | 전체 배경 | `bg-bg` |
| `lav` | `#E4DEFF` | 카드 강조, 선택 칩, 진행률 트랙 | `bg-lav` |
| `brand` | `#6C4DF6` | 주 강조 (버튼, 활성 탭, 진행률) | `bg-brand` `text-brand` |
| `ink` | `#1F1535` | 제목·본문 텍스트 | `text-ink` |
| `sub` | `#6B6580` | 보조 텍스트 | `text-sub` |
| `ok` | `#2BA471` | 완료 | `text-ok` |
| `warn` | `#F5A524` | 주의 (마감 임박) | `text-warn` |
| `danger` | `#E5484D` | 경고 (지연 위험, 졸업 불가) | `text-danger` |

카드 배경은 흰색(`bg-white`), 버튼 글자는 흰색.

## 타이포그래피 — Pretendard

| 용도 | 크기 / 굵기 | 컴포넌트 |
|---|---|---|
| 화면 제목 | 22 / Bold | `ScreenTitle` |
| 섹션 제목 | 17 / SemiBold | `SectionTitle` |
| 본문 | 15 / Regular | — |
| 캡션 | 12 / Medium | — |

## 간격·형태

- 8pt 그리드, 좌우 여백 20 (`px-5`)
- 카드 모서리 16, 칩 모서리 완전 둥글게
- 터치 영역 최소 44 (`min-h-11`)

## 공통 컴포넌트 (`src/components/kit.tsx`)

| 컴포넌트 | 용도 |
|---|---|
| `TabBar` | 하단 5탭 (홈 · 학점 · 로드맵 · 커뮤니티 · 마이) |
| `ScreenTitle` / `SectionTitle` | 제목 |
| `Card` | 흰 카드 |
| `Chip` | 필터·조건 칩 |
| `TypeBadge` | 이수구분 뱃지 (전필·전선·교필·교선, `short` 옵션) |
| `StatusPill` | 상태 라벨 (ok · warn · danger · brand · muted) |
| `Progress` | 진행률 바 |
| `PrimaryButton` / `SecondaryButton` | 버튼 |
| `Field` / `Input` | 입력 |
| `CourseTile` | 로드맵 학기 카드 안의 과목 타일. `dashed` 이면 가상 과목(교양 자리) |

## 화면 목록 (현재는 시안 쇼케이스 형태)

| # | 화면 | 컴포넌트 | 우선순위 |
|---|---|---|---|
| 1 | 로그인 | `Login` | P0 |
| 2 | 회원가입 1단계 | `SignupAccount` | P0 |
| 3 | 회원가입 2단계 | `SignupSchool` | P0 |
| 4 | 홈 | `HomeScreen` | P1 |
| 5 | 학점관리 | `CreditScreen` | P0 |
| 6 | 로드맵 추천 결과 | `RoadmapResult` | P0 |
| 7 | 졸업 불가 | `RoadmapImpossible` | P0 |
| 8 | 로드맵 탭 | `RoadmapTab` | P0 |
| 9 | 커뮤니티 — 중고거래 | `CommunityMarket` | P2 |
| 10 | 커뮤니티 — 선배 | `CommunitySeniors` | P2 |
| 11 | 커뮤니티 — 맛집 | `CommunityFood` | P2 |
| 12 | 마이페이지 | `MyPage` | P1 |

## 실제 앱으로 전환할 때 지킬 것

1. `Phone`, `StatusBar`, `HomeIndicator` 는 **시안 전용**이다. 실제 앱에서는 기기 자체의 상태바를 쓰므로 제거하고, 대신 CSS 안전영역을 쓴다.
   ```css
   padding-top: env(safe-area-inset-top);
   padding-bottom: env(safe-area-inset-bottom);
   ```
2. 화면 컴포넌트 안의 **하드코딩된 샘플 데이터**(김경기, 과목명, 학점 등)는 props 또는 API 응답으로 교체한다. 레이아웃·클래스는 바꾸지 않는다.
3. 402px 고정폭은 `Phone` 에만 있다. 화면 내부는 이미 유동폭이므로 그대로 쓰면 기기별로 늘어난다. 태블릿·PC에서는 앱 전체를 `max-w-[480px] mx-auto` 로 감싼다.
