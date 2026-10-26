import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './auth/AuthContext'
import './index.css'

// BrowserRouter : 주소창의 URL 에 따라 화면을 바꿔 주는 라우터
// AuthProvider  : 로그인 상태를 앱 전체에 공유 (auth/AuthContext.tsx)
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
