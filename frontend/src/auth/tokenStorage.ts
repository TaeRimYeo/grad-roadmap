// 로그인 토큰(JWT) 보관함.
//
// 지금은 브라우저의 localStorage 에 저장한다.
// 나중에 Capacitor 로 앱을 만들면 @capacitor/preferences 로 바꿀 예정인데,
// 앱 전체가 이 파일의 함수 3개만 쓰도록 해 두었으므로 이 파일 하나만 고치면 된다.
// (Preferences 는 비동기라서 그때는 함수들이 Promise 를 돌려주게 바뀔 수 있다)

const KEY = 'grad-roadmap.token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(KEY)
  } catch {
    // 사생활 보호 모드 등에서 localStorage 접근이 막히면 "토큰 없음" 으로 취급
    return null
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(KEY, token)
  } catch {
    // 저장 실패 시 새로고침하면 로그아웃될 뿐, 앱이 멈추지는 않게 무시
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // 무시
  }
}
