/// <reference types="vite/client" />

// .env 파일에 적는 환경변수의 타입. 여기 적어두면 import.meta.env.VITE_API_URL 에 자동완성이 된다.
interface ImportMetaEnv {
  readonly VITE_API_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
