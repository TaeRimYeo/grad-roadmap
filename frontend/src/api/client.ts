// 백엔드 호출용 fetch 래퍼.
//
// 하는 일
//   1. 주소 앞에 VITE_API_URL(.env.local) 을 붙인다
//   2. 토큰이 저장돼 있으면 Authorization: Bearer <토큰> 헤더를 자동으로 붙인다
//   3. 서버가 오류를 보내면 {"detail": "한국어 메시지"} 의 메시지로 ApiError 를 던진다
//      → 화면에서는 catch 해서 err.message 를 그대로 보여주면 된다

import { getToken } from '../auth/tokenStorage'

const BASE_URL = import.meta.env.VITE_API_URL ?? ''

// 서버 오류. status 로 401(로그인 필요) 같은 경우를 구분할 수 있다.
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

type Options = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown // 객체를 넘기면 JSON 으로 바꿔서 보낸다
}

export async function api<T>(path: string, { method = 'GET', body }: Options = {}): Promise<T> {
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    // fetch 자체가 실패 = 서버가 꺼져 있거나 주소가 틀림 (status 0 으로 표시)
    throw new ApiError(0, '서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.')
  }

  // 응답 본문을 JSON 으로 읽는다. 본문이 비었거나 JSON 이 아니면 null
  const data = await res.json().catch(() => null)

  if (!res.ok) {
    // 서버 명세: 모든 오류는 {"detail": "한국어 메시지"}
    const message =
      data && typeof data.detail === 'string'
        ? data.detail
        : `요청을 처리하지 못했습니다 (${res.status})`
    throw new ApiError(res.status, message)
  }

  return data as T
}
