import type { ReactNode } from 'react'
import {
  ArrowLeft,
  AlertTriangle,
  Plus,
  Search,
  Heart,
  MoreVertical,
  Star,
  MapPin,
  MessageCircle,
  ChevronRight,
  Pencil,
  BookOpen,
  ClipboardList,
  FileText,
  Bookmark,
  Bell as BellIcon,
  Moon,
  Send,
  LogOut,
  GitCompare,
  Share2,
  Plane,
  Repeat,
} from 'lucide-react'
import {
  Card,
  Chip,
  PrimaryButton,
  ScreenTitle,
  SectionTitle,
  StatusPill,
  TabBar,
  HomeIndicator,
} from '../components/kit'

const PX = 'px-5'

/* 7 ── 로드맵 추천 — 졸업 불가 ────────────────────────────── */
export function RoadmapImpossible() {
  return (
    <div className={`flex min-h-full flex-col ${PX} pb-6`}>
      <div className="flex items-center gap-3 pt-1">
        <ArrowLeft size={24} className="text-ink" />
        <ScreenTitle>추천 로드맵</ScreenTitle>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Chip active>남은 1학기</Chip>
        <Chip>학기당 최대 22학점</Chip>
        <Chip>계절학기 사용 안 함</Chip>
      </div>

      <div className="mt-6 flex flex-col items-center gap-3 rounded-2xl bg-white p-6 text-center ring-1 ring-black/[0.04]">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#fdecec]">
          <AlertTriangle size={30} className="text-danger" />
        </div>
        <h2 className="text-[19px] font-bold text-ink">현재 조건으로는 졸업할 수 없어요</h2>
      </div>

      <div className="mt-4 rounded-2xl bg-[#fdecec] p-4 ring-1 ring-danger/20">
        <p className="text-[13px] font-bold text-danger">원인</p>
        <p className="mt-1.5 text-[14px] font-medium leading-relaxed text-[#8a2e31]">
          캡스톤디자인2는 캡스톤디자인1 이수 후 2학기에만 열려서, 남은 1학기 안에 둘 다 배치할 수 없어요
        </p>
      </div>

      <p className="mt-6 text-[15px] font-bold text-ink">이렇게 해보세요</p>
      <div className="mt-3 flex flex-col gap-3">
        {[
          { icon: <Repeat size={20} />, title: '남은 학기를 1개 늘리기', desc: '3학년 2학기까지 배치하면 모든 선수과목을 채울 수 있어요' },
          { icon: <Plane size={20} />, title: '계절학기 허용하기', desc: '여름·겨울 계절학기로 6학점을 앞당겨 들을 수 있어요' },
        ].map((s) => (
          <button
            key={s.title}
            className="flex items-center gap-3 rounded-2xl bg-white p-4 text-left ring-1 ring-black/[0.04] transition active:scale-[0.99]"
          >
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-lav text-brand">
              {s.icon}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[15px] font-bold text-ink">{s.title}</p>
              <p className="mt-0.5 text-[12px] text-sub">{s.desc}</p>
            </div>
            <ChevronRight size={18} className="text-[#c3bcda]" />
          </button>
        ))}
      </div>

      <div className="mt-auto pt-6">
        <PrimaryButton>조건 바꿔서 다시 추천</PrimaryButton>
      </div>
      <HomeIndicator />
    </div>
  )
}

/* 8 ── 로드맵 탭 — 저장한 로드맵 ─────────────────────────── */
function MiniTimeline() {
  return (
    <div className="flex items-center gap-1">
      {['2-2', '3-1', '3-2'].map((s, i) => (
        <div key={s} className="flex items-center gap-1">
          <div className="flex flex-col items-center gap-1">
            <div className={`h-2.5 w-2.5 rounded-full ${i === 2 ? 'bg-white' : 'bg-white/50'}`} />
            <span className="text-[10px] font-semibold text-white/80">{s}</span>
          </div>
          {i < 2 && <div className="h-px w-8 bg-white/40" />}
        </div>
      ))}
    </div>
  )
}

function SavedRow({ name, date, grad }: { name: string; date: string; grad: string }) {
  return (
    <div className="flex items-center gap-3 py-3.5">
      <div className="min-w-0 flex-1">
        <p className="truncate text-[15px] font-semibold text-ink">{name}</p>
        <p className="mt-0.5 text-[12px] text-sub">
          {date} 저장 · 졸업 예정 {grad}
        </p>
      </div>
      <MoreVertical size={20} className="text-[#b3adca]" />
    </div>
  )
}

export function RoadmapTab() {
  return (
    <div className="flex min-h-full flex-col">
      <div className={`flex flex-col gap-4 ${PX} pb-6 pt-2`}>
        <SectionTitle
          action={
            <span className="inline-flex items-center gap-1 rounded-full bg-lav px-3 py-1.5 text-[13px] font-bold text-brand">
              <Plus size={15} /> 새로 추천
            </span>
          }
        >
          <span className="text-[22px] font-bold">내 로드맵</span>
        </SectionTitle>

        <div className="rounded-2xl bg-brand p-5 text-white shadow-[0_16px_32px_-12px_rgba(108,77,246,0.7)]">
          <div className="flex items-center gap-2">
            <StatusPill tone="ok">대표</StatusPill>
            <h3 className="text-[18px] font-bold">기본 추천 플랜</h3>
          </div>
          <div className="mt-3 flex items-center gap-4">
            <div>
              <p className="text-[12px] text-white/75">졸업 예정</p>
              <p className="text-[16px] font-bold">3학년 2학기</p>
            </div>
            <div className="h-8 w-px bg-white/25" />
            <div>
              <p className="text-[12px] text-white/75">남은 학점</p>
              <p className="text-[16px] font-bold">38학점</p>
            </div>
          </div>
          <div className="mt-4 rounded-xl bg-white/10 p-3">
            <MiniTimeline />
          </div>
        </div>

        <Card className="divide-y divide-black/5 py-1">
          <SavedRow name="인공지능 집중 플랜" date="9월 20일" grad="3학년 2학기" />
          <SavedRow name="현장실습 포함 플랜" date="9월 18일" grad="4학년 1학기" />
        </Card>

        <div className="flex gap-3">
          {[
            { icon: <GitCompare size={18} />, label: '두 로드맵 비교' },
            { icon: <Share2 size={18} />, label: '이미지로 공유' },
          ].map((b) => (
            <button
              key={b.label}
              className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-white py-3.5 text-[14px] font-bold text-ink ring-1 ring-black/[0.05] transition active:scale-[0.99]"
            >
              <span className="text-brand">{b.icon}</span>
              {b.label}
            </button>
          ))}
        </div>
      </div>
      <TabBar active="roadmap" />
    </div>
  )
}

/* Community shared header ─────────────────────────────────────── */
function CommunityHeader({ active }: { active: 0 | 1 | 2 }) {
  const tabs = ['중고거래', '선배 네트워킹', '맛집']
  return (
    <div className={`flex flex-col gap-3 ${PX} pt-2`}>
      <ScreenTitle>커뮤니티</ScreenTitle>
      <div className="flex gap-1 rounded-2xl bg-lav p-1">
        {tabs.map((t, i) => (
          <div
            key={t}
            className={`flex min-h-10 flex-1 items-center justify-center rounded-xl text-[13px] font-bold ${
              i === active ? 'bg-white text-brand shadow-sm' : 'text-[#7d76a0]'
            }`}
          >
            {t}
          </div>
        ))}
      </div>
    </div>
  )
}

function SearchBar() {
  return (
    <div className="flex min-h-11 items-center gap-2 rounded-2xl bg-white px-4 ring-1 ring-black/[0.05]">
      <Search size={18} className="text-[#a8a2bc]" />
      <span className="text-[14px] text-[#a8a2bc]">검색어를 입력하세요</span>
    </div>
  )
}

function FAB({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <button className="absolute bottom-24 right-5 z-10 inline-flex items-center gap-2 rounded-full bg-brand px-5 py-3.5 text-[15px] font-bold text-white shadow-[0_14px_28px_-8px_rgba(108,77,246,0.7)]">
      {icon} {label}
    </button>
  )
}

/* 9 ── 커뮤니티 — 중고거래 ───────────────────────────────── */
function BookRow({
  title,
  price,
  cond,
  tag,
  seller,
  likes,
  sold = false,
}: {
  title: string
  price: string
  cond: string
  tag: string
  seller?: string
  likes: number
  sold?: boolean
}) {
  return (
    <div className={`flex gap-3 ${sold ? 'opacity-50' : ''}`}>
      <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-xl bg-lav">
        <BookOpen size={26} className="text-[#a99ce8]" />
      </div>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-start justify-between gap-2">
          <p className="min-w-0 flex-1 truncate text-[15px] font-bold text-ink">{title}</p>
          {sold && <StatusPill tone="muted">판매완료</StatusPill>}
        </div>
        <p className="mt-0.5 text-[16px] font-bold text-brand">{price}</p>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          <span className="rounded-md bg-black/5 px-1.5 py-0.5 text-[11px] font-semibold text-sub">{cond}</span>
          <span className="rounded-md bg-lav px-1.5 py-0.5 text-[11px] font-semibold text-brand">#{tag}</span>
        </div>
        <div className="mt-auto flex items-center gap-2 text-[12px] text-sub">
          {seller && <span>{seller} 판매자</span>}
          <span className="ml-auto inline-flex items-center gap-1">
            <Heart size={13} /> {likes}
          </span>
        </div>
      </div>
    </div>
  )
}

export function CommunityMarket() {
  return (
    <div className="relative flex min-h-full flex-col">
      <CommunityHeader active={0} />
      <div className={`mt-3 flex flex-col gap-3 ${PX} pb-6`}>
        <SearchBar />
        <div className="flex gap-2">
          <Chip active>전체</Chip>
          <Chip>전공서적</Chip>
          <Chip>교양</Chip>
          <Chip>기타</Chip>
        </div>
        <Card className="flex flex-col gap-4">
          <BookRow title="데이터베이스 개론 3판" price="12,000원" cond="거의 새것" tag="데이터베이스" seller="3학년" likes={4} />
          <div className="h-px bg-black/5" />
          <BookRow title="안드로이드 앱 프로그래밍" price="15,000원" cond="필기 약간" tag="안드로이드프로그래밍" likes={7} />
          <div className="h-px bg-black/5" />
          <BookRow title="C# 입문" price="8,000원" cond="새 책" tag="C#프로그래밍" likes={2} sold />
        </Card>
      </div>
      <FAB icon={<Pencil size={17} />} label="글쓰기" />
      <TabBar active="community" />
    </div>
  )
}

/* 10 ── 커뮤니티 — 선배 네트워킹 ─────────────────────────── */
function SeniorCard({ initial, name, meta, tags, intro }: { initial: string; name: string; meta: string; tags: string[]; intro: string }) {
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand text-[17px] font-bold text-white">
          {initial}
        </div>
        <div>
          <p className="text-[16px] font-bold text-ink">{name}</p>
          <p className="text-[12px] text-sub">{meta}</p>
        </div>
        <button className="ml-auto rounded-full bg-brand px-4 py-2 text-[13px] font-bold text-white">멘토링 요청</button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {tags.map((t) => (
          <span key={t} className="rounded-full bg-lav px-2.5 py-1 text-[11px] font-semibold text-brand">
            {t}
          </span>
        ))}
      </div>
      <p className="text-[13px] text-sub">{intro}</p>
    </Card>
  )
}

export function CommunitySeniors() {
  return (
    <div className="flex min-h-full flex-col">
      <CommunityHeader active={1} />
      <div className={`mt-3 flex flex-col gap-3 ${PX} pb-6`}>
        <SeniorCard
          initial="이"
          name="이도현"
          meta="3학년 · SW융합전공"
          tags={['백엔드', '인공지능', '현장실습 경험']}
          intro="스타트업 인턴 하면서 배운 것들 공유해요. 캡스톤 준비 편하게 물어보세요!"
        />
        <SeniorCard
          initial="박"
          name="박서연"
          meta="3학년 · SW융합전공"
          tags={['프론트엔드', '앱개발']}
          intro="공모전 3회 수상. 포트폴리오·이력서 첨삭 도와드릴 수 있어요."
        />

        <section className="mt-2 flex flex-col gap-2">
          <SectionTitle>질문 게시판</SectionTitle>
          <Card className="divide-y divide-black/5 py-1">
            {[
              ['캡스톤 주제 어떻게 정하셨나요?', 5],
              ['정보처리특론 난이도 어떤가요?', 3],
            ].map(([q, a]) => (
              <div key={q as string} className="flex items-center gap-3 py-3">
                <span className="min-w-0 flex-1 truncate text-[15px] font-medium text-ink">{q}</span>
                <span className="inline-flex items-center gap-1 text-[12px] font-bold text-brand">
                  <MessageCircle size={14} /> 답변 {a}
                </span>
              </div>
            ))}
          </Card>
        </section>
      </div>
      <TabBar active="community" />
    </div>
  )
}

/* 11 ── 커뮤니티 — 맛집 ──────────────────────────────────── */
function PlaceRow({ rank, name, cat, rating, reviews, walk, price, review }: { rank: number; name: string; cat: string; rating: number; reviews: number; walk: string; price: string; review?: string }) {
  return (
    <div className="flex gap-3">
      <span className="w-6 shrink-0 text-[24px] font-bold text-brand">{rank}</span>
      <div className="h-20 w-20 shrink-0 rounded-xl bg-gradient-to-br from-[#ffe1c4] to-[#f6c9a0]" />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2">
          <p className="min-w-0 truncate text-[15px] font-bold text-ink">{name}</p>
          <span className="text-[12px] text-sub">{cat}</span>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[12px] text-sub">
          <span className="inline-flex items-center gap-0.5 font-bold text-[#c07a10]">
            <Star size={12} className="fill-[#f5a524] text-[#f5a524]" /> {rating}
          </span>
          <span>리뷰 {reviews}</span>
          <span className="inline-flex items-center gap-0.5">
            <MapPin size={12} /> 도보 {walk}
          </span>
          <span>{price}</span>
        </div>
        <div className="mt-1.5">
          <StatusPill tone="brand">학생 인증 리뷰</StatusPill>
        </div>
        {review && <p className="mt-1.5 text-[12px] italic text-sub">“{review}”</p>}
      </div>
    </div>
  )
}

export function CommunityFood() {
  return (
    <div className="relative flex min-h-full flex-col">
      <CommunityHeader active={2} />
      <div className={`mt-3 flex flex-col gap-3 ${PX} pb-6`}>
        <div className="flex gap-2 overflow-x-auto">
          <Chip active>추천순</Chip>
          <Chip>평점순</Chip>
          <Chip>리뷰 많은 순</Chip>
          <Chip>가까운 순</Chip>
        </div>
        <Card className="flex flex-col gap-4">
          <PlaceRow rank={1} name="정왕 국밥집" cat="한식" rating={4.7} reviews={128} walk="5분" price="8천원대" review="공강 때 든든하게 먹기 좋아요" />
          <div className="h-px bg-black/5" />
          <PlaceRow rank={2} name="캠퍼스 앞 돈카츠" cat="일식" rating={4.6} reviews={94} walk="3분" price="9천원대" />
          <div className="h-px bg-black/5" />
          <PlaceRow rank={3} name="시흥 마라탕" cat="중식" rating={4.4} reviews={71} walk="8분" price="1만원대" />
        </Card>
      </div>
      <FAB icon={<Pencil size={17} />} label="리뷰 쓰기" />
      <TabBar active="community" />
    </div>
  )
}

/* 12 ── 마이페이지 ───────────────────────────────────────── */
function MenuGroup({ title, items }: { title: string; items: { icon: ReactNode; label: string; toggle?: boolean; on?: boolean }[] }) {
  return (
    <section className="flex flex-col gap-2">
      <p className="text-[13px] font-bold text-sub">{title}</p>
      <Card className="divide-y divide-black/5 py-1">
        {items.map((it) => (
          <div key={it.label} className="flex items-center gap-3 py-3">
            <span className="text-brand">{it.icon}</span>
            <span className="flex-1 text-[15px] font-medium text-ink">{it.label}</span>
            {it.toggle ? (
              <div className={`flex h-6 w-11 items-center rounded-full px-0.5 ${it.on ? 'justify-end bg-brand' : 'justify-start bg-black/15'}`}>
                <div className="h-5 w-5 rounded-full bg-white shadow" />
              </div>
            ) : (
              <ChevronRight size={18} className="text-[#c3bcda]" />
            )}
          </div>
        ))}
      </Card>
    </section>
  )
}

export function MyPage() {
  return (
    <div className="flex min-h-full flex-col">
      <div className={`flex flex-col gap-5 ${PX} pb-6 pt-2`}>
        <ScreenTitle>마이</ScreenTitle>

        <Card className="flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand text-[24px] font-bold text-white">
            김
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[18px] font-bold text-ink">김경기</p>
            <p className="mt-0.5 text-[12px] text-sub">2025학번 · 컴퓨터모바일융합과</p>
            <p className="text-[12px] text-sub">SW융합전공 · 전문학사</p>
          </div>
          <button className="rounded-full bg-lav px-3.5 py-2 text-[13px] font-bold text-brand">수정</button>
        </Card>

        <MenuGroup
          title="학업"
          items={[
            { icon: <FileText size={20} />, label: '학적 정보 수정' },
            { icon: <ClipboardList size={20} />, label: '이수 내역 관리' },
            { icon: <Pencil size={20} />, label: '성적 입력' },
          ]}
        />
        <MenuGroup
          title="활동"
          items={[
            { icon: <FileText size={20} />, label: '내가 쓴 글' },
            { icon: <Star size={20} />, label: '내 리뷰' },
            { icon: <Bookmark size={20} />, label: '찜한 거래' },
          ]}
        />
        <MenuGroup
          title="설정"
          items={[
            { icon: <BellIcon size={20} />, label: '과제 마감·수업 알림', toggle: true, on: true },
            { icon: <Moon size={20} />, label: '다크 모드', toggle: true, on: false },
            { icon: <Send size={20} />, label: '피드백 보내기' },
          ]}
        />

        <div className="mt-2 flex flex-col items-center gap-1">
          <button className="inline-flex items-center gap-1.5 text-[14px] font-semibold text-sub">
            <LogOut size={16} /> 로그아웃
          </button>
          <span className="text-[11px] text-[#b3adca]">앱 버전 1.0.0</span>
        </div>
      </div>
      <TabBar active="my" />
    </div>
  )
}
