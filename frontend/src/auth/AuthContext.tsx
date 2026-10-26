// 로그인 상태를 앱 전체에서 함께 쓰기 위한 Context.
//
// Context 란?
//   보통 React 에서는 데이터를 부모 → 자식으로 props 로 하나씩 넘겨야 한다.
//   "지금 로그인한 사람" 처럼 거의 모든 화면이 필요한 값은 그렇게 넘기기 번거로우므로,
//   맨 위(<AuthProvider>)에 한 번 넣어 두고 어느 화면에서든 useAuth() 로 꺼내 쓴다.
//
// 제공하는 것
//   user    : 로그인한 사용자 정보(/me 응답). 로그인 안 했으면 null
//   loading : 앱 시작 시 저장된 토큰을 확인하는 중이면 true
//   login / signup / logout

import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api, ApiError } from '../api/client'
import type { LoginResponse, Me, SignupRequest } from '../api/types'
import { clearToken, getToken, setToken } from './tokenStorage'

type AuthValue = {
  user: Me | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (req: SignupRequest) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null)
  // 토큰이 있을 때만 "확인 중" 으로 시작한다. 없으면 바로 로그아웃 상태 확정
  const [loading, setLoading] = useState(() => getToken() !== null)

  // 앱 시작 시 1번: 저장된 토큰이 아직 유효한지 /me 로 확인
  useEffect(() => {
    if (!getToken()) return
    api<Me>('/api/auth/me')
      .then(setUser)
      .catch((err) => {
        // 401 = 토큰 만료·위조 → 토큰을 지워서 로그인 화면으로 가게 한다
        // 403 = 비활성화 계정 → 마찬가지로 로그인 상태를 풀어 준다
        // 그 밖의 오류(서버 꺼짐 등)는 토큰을 남겨 두고, 다음에 다시 확인한다
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          clearToken()
        }
      })
      .finally(() => setLoading(false))
  }, [])

  // 로그인: 토큰을 받아 저장 → 로그인 응답에는 학과·전공이 없으므로 /me 로 전체 정보를 받는다
  const login = useCallback(async (email: string, password: string) => {
    const res = await api<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    setToken(res.access_token)
    try {
      setUser(await api<Me>('/api/auth/me'))
    } catch (err) {
      // /me 가 실패하면 반쯤 로그인된 상태가 남지 않게 토큰도 지운다
      clearToken()
      throw err
    }
  }, [])

  // 회원가입: 가입 API 는 토큰을 주지 않으므로, 가입 직후 같은 이메일·비밀번호로 로그인까지 한다
  const signup = useCallback(
    async (req: SignupRequest) => {
      await api('/api/auth/signup', { method: 'POST', body: req })
      await login(req.email, req.password)
    },
    [login],
  )

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// 화면에서 쓰는 방법: const { user, logout } = useAuth()
export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth 는 <AuthProvider> 안에서만 쓸 수 있습니다')
  return ctx
}
