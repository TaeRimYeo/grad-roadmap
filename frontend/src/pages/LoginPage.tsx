// 로그인 화면 (시안 1번 레이아웃 그대로, 입력·버튼만 실제로 동작하게)

import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import { Input, PrimaryButton } from '../components/kit'
import { useAuth } from '../auth/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  // 요청 중이면 true → 버튼 비활성화 (두 번 눌러 요청이 두 번 가는 것 방지)
  const [submitting, setSubmitting] = useState(false)

  // form 의 onSubmit 을 쓰면 버튼 클릭뿐 아니라 키보드 Enter 로도 로그인된다
  async function handleSubmit(e: FormEvent) {
    e.preventDefault() // 브라우저가 페이지를 새로고침하는 기본 동작을 막음
    if (submitting) return
    if (!email.trim() || !password) {
      setError('이메일과 비밀번호를 입력해 주세요')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      await login(email.trim(), password)
      navigate('/', { replace: true })
    } catch (err) {
      // 서버가 보낸 한국어 메시지 (예: "이메일 또는 비밀번호가 올바르지 않습니다")
      setError(err instanceof Error ? err.message : '로그인에 실패했습니다')
      setSubmitting(false)
    }
  }

  return (
    <div className="flex flex-1 flex-col px-5 pb-8">
      <div className="flex flex-1 flex-col items-center justify-center gap-8">
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-20 w-20 items-center justify-center rounded-[26px] bg-brand shadow-[0_16px_32px_-10px_rgba(108,77,246,0.7)]">
            <MapLogo />
          </div>
          <div className="text-center">
            <h1 className="text-[28px] font-bold tracking-tight text-ink">학기 로드맵</h1>
            <p className="mt-1.5 text-[15px] text-sub">졸업까지의 길을 자동으로 설계해요</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex w-full flex-col gap-3">
          <Input
            type="email"
            inputMode="email"
            autoComplete="email"
            placeholder="학교 이메일"
            value={email}
            onChange={setEmail}
          />
          <Input
            type={showPw ? 'text' : 'password'}
            autoComplete="current-password"
            placeholder="비밀번호"
            value={password}
            onChange={setPassword}
            trailing={<PasswordToggle shown={showPw} onToggle={() => setShowPw((v) => !v)} />}
          />
          {error && <p className="text-[13px] font-medium text-danger">{error}</p>}
          <PrimaryButton type="submit" disabled={submitting} className="mt-2">
            {submitting ? '처리 중...' : '로그인'}
          </PrimaryButton>
        </form>
      </div>

      <div className="flex items-center justify-center text-[14px] font-medium text-sub">
        <span>처음이신가요?</span>
        <Link to="/signup" className="ml-2 flex min-h-11 items-center font-semibold text-brand">
          회원가입
        </Link>
      </div>
    </div>
  )
}

// 비밀번호 보기/숨기기 버튼. 회원가입 화면에서도 쓴다.
export function PasswordToggle({ shown, onToggle }: { shown: boolean; onToggle: () => void }) {
  const Icon = shown ? Eye : EyeOff
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={shown ? '비밀번호 숨기기' : '비밀번호 보기'}
      className="-mr-2 flex h-11 w-11 items-center justify-center"
    >
      <Icon size={20} className="text-[#a8a2bc]" />
    </button>
  )
}

// 로고 안의 지도 아이콘 (시안 Frames1to6 의 것과 동일)
function MapLogo() {
  return (
    <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 6 3 4v14l6 2 6-2 6 2V6l-6-2-6 2Z" />
      <path d="M9 4v16M15 6v16" />
    </svg>
  )
}
